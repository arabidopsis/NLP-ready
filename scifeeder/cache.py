from __future__ import annotations

from pathlib import Path
from typing import Literal
from typing import TypeAlias

from .types import Paper

FileFormat: TypeAlias = Literal["xml", "html"]


class Cache:

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def locate(self, paper) -> Path | None:
        outdir = self.cache_dir / "html" / f"{paper.pmid}.html"
        if outdir.exists():
            return outdir
        outdir = self.cache_dir / "xml" / f"{paper.pmid}.xml"
        if outdir.exists():
            return outdir
        return None

    def save_html(self, paper: Paper, html: str) -> None:
        return self.save_(paper, html, "html")

    def save_xml(self, paper: Paper, xml: str) -> None:
        return self.save_(paper, xml, "xml")

    def fetch_html(self, paper: Paper) -> str | None:
        return self.fetch_(paper, "html")

    def fetch_xml(self, paper: Paper) -> str | None:
        return self.fetch_(paper, "xml")

    def fetch(self, paper: Paper) -> tuple[str | None, FileFormat]:
        ret = self.fetch_html(paper)
        if ret is not None:
            return ret, "html"
        return self.fetch_xml(paper), "xml"

    def save_(self, paper: Paper, html, ff: FileFormat) -> None:
        outdir = self.cache_dir / ff
        if not outdir.exists():
            outdir.mkdir(parents=True, exist_ok=True)
        fname = outdir / f"{paper.pmid}.{ff}"
        with fname.open("wt", encoding="utf8") as fp:
            fp.write(html)

    def fetch_(self, paper: Paper, ff: FileFormat) -> str | None:
        outdir = self.cache_dir / ff
        fname = outdir / f"{paper.pmid}.{ff}"
        if not fname.exists():
            return None
        with fname.open("rt", encoding="utf8") as fp:
            return fp.read()
