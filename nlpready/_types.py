from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True)
class Paper:
    pmid: str
    year: int
    title: str | None
    doi: str
    issn: str | None
    journal: str | None
    pmcid: str | None


@dataclass(kw_only=True)
class NCBIPaper(Paper):
    abstract: str | None
    authors: list[tuple[str | None, str | None, str | None]]
    volume: str | None
    issue: str | None
    pages: str | None
