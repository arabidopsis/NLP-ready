from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


@dataclass(kw_only=True)
class Paper:
    pmid: str
    year: int
    title: str | None
    doi: str
    issn: str | None
    journal: str | None
    pmcid: str | None

    @property
    def key(self):
        return (
            self.journal.replace(" ", "")
            .replace(".", "")
            .replace("(", "_")
            .replace(")", "_")
        )


@dataclass(kw_only=True)
class NCBIPaper(Paper):
    abstract: str | None
    authors: list[tuple[str | None, str | None, str | None]]
    volume: str | None
    issue: str | None
    pages: str | None


@dataclass
class Location:
    article_css: str
    remove_css: str = ""
    wait_css: str = ""
    pdf_accessible: bool = False

    def full(self, url: str) -> str:
        return url

    def pdf(self, soup: BeautifulSoup, url: str) -> bytes | None:
        return None


@dataclass
class RNALocation(Location):
    def full(self, url: str) -> str:
        return url + ".full"
