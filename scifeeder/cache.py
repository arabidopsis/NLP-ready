from __future__ import annotations

import gzip
from pathlib import Path
from typing import cast
from typing import Iterator
from typing import Literal
from typing import Sequence
from typing import TYPE_CHECKING
from typing import TypeAlias


if TYPE_CHECKING:
    from .types import Paper

FileFormat: TypeAlias = Literal["xml", "html", "ncbi"]


class Cache:

    def __init__(self, cache_dir: str | Path, compressed: bool = False):
        self.cache_dir = Path(cache_dir)
        self.compressed = compressed
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.gz = ".gz" if self.compressed else ""

    def locate(self, paper: Paper) -> tuple[Path | None, FileFormat]:

        for typ in ["html", "xml", "ncbi"]:
            ext = "xml" if typ == "xml" else "html"
            outdir = self.cache_dir / typ / f"{paper.pmid}.{ext}{self.gz}"
            if outdir.exists():
                return outdir, cast(FileFormat, typ)

        return None, "html"

    def save_ncbi(self, paper: Paper, html: str) -> None:
        return self.save_(paper, html, "ncbi")

    def save_html(self, paper: Paper, html: str) -> None:
        return self.save_(paper, html, "html")

    def save_xml(self, paper: Paper, xml: str) -> None:
        return self.save_(paper, xml, "xml")

    def fetch_html(self, paper: Paper) -> str | None:
        return self.fetch_(paper, "html")

    def fetch_ncbi(self, paper: Paper) -> str | None:
        return self.fetch_(paper, "ncbi")

    def fetch_xml(self, paper: Paper) -> str | None:
        return self.fetch_(paper, "xml")

    def fetch(self, paper: Paper) -> tuple[str | None, FileFormat]:
        path, typ = self.locate(paper)
        if path is None:
            return None, "html"
        if self.compressed:
            with gzip.open(path, "rt", encoding="utf8") as fp:
                return fp.read(), typ
        with path.open("rt", encoding="utf-8") as fp:
            return fp.read(), typ

    def save_(self, paper: Paper, html, ff: FileFormat) -> None:
        outdir = self.cache_dir / ff
        if not outdir.exists():
            outdir.mkdir(parents=True, exist_ok=True)
        ext = "xml" if ff == "xml" else "html"
        path = outdir / f"{paper.pmid}.{ext}{self.gz}"
        if self.compressed:
            with gzip.open(path, "wt", encoding="utf8") as fp:
                fp.write(html)
        with path.open("wt", encoding="utf8") as fp:
            fp.write(html)

    def fetch_(self, paper: Paper, ff: FileFormat) -> str | None:

        outdir = self.cache_dir / ff
        ext = "xml" if ff == "xml" else "html"
        path = outdir / f"{paper.pmid}.{ext}{self.gz}"
        if not path.exists():
            return None
        if self.compressed:
            with gzip.open(path, "rt", encoding="utf8") as fp:
                return fp.read()
        with path.open("rt", encoding="utf8") as fp:
            return fp.read()

    def fetchall(self, papers: Sequence[Paper]) -> Iterator[tuple[str, FileFormat]]:
        for paper in papers:
            s, ff = self.fetch(paper)
            if s is not None:
                yield s, ff
