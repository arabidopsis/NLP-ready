from __future__ import annotations

from pathlib import Path
from typing import cast
from typing import Literal
from typing import TypeAlias

from .types import Paper

FileFormat: TypeAlias = Literal["xml", "html", "ncbi"]


class Cache:

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def locate(self, paper) -> tuple[Path | None, FileFormat]:

        for typ in ["html", "xml", "ncbi"]:
            ext = "xml" if typ == "xml" else "html"
            outdir = self.cache_dir / typ / f"{paper.pmid}.{ext}"
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
        with path.open("rt", encoding="utf-8") as fp:
            return fp.read(), typ

    def save_(self, paper: Paper, html, ff: FileFormat) -> None:
        outdir = self.cache_dir / ff
        if not outdir.exists():
            outdir.mkdir(parents=True, exist_ok=True)
        ext = "xml" if ff == "xml" else "html"
        fname = outdir / f"{paper.pmid}.{ext}"
        with fname.open("wt", encoding="utf8") as fp:
            fp.write(html)

    def fetch_(self, paper: Paper, ff: FileFormat) -> str | None:

        outdir = self.cache_dir / ff
        ext = "xml" if ff == "xml" else "html"
        fname = outdir / f"{paper.pmid}.{ext}"
        if not fname.exists():
            return None
        with fname.open("rt", encoding="utf8") as fp:
            return fp.read()
