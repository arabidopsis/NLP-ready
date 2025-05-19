from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from typing import Self

from bs4 import BeautifulSoup
from bs4 import Tag
from html_to_markdown import convert_to_markdown
from requests import Session

from .._selenium import MD_STYLE
from .utils import PMCEvents

PE = re.compile(b"<[?][^?]+[?]>")

# see https://europepmc.org/RestfulWebService#!/Europe32PMC32Articles32RESTful32API/fullTextXML
XML = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"  # noqa: E221
)


@dataclass
class Outline:
    title: Tag
    abstract: Tag
    body: Tag


def epmc(
    pmcid: str,
    session: Session | None = None,
    *,
    strip_pi: bool = True,
) -> bytes | None:
    """Given a PUBMED id return the Europmc XML as bytes."""
    url = XML.format(pmcid=pmcid)
    if session is None:
        session = Session()
    resp = session.get(url)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    # get rid of <?ConverterInfo.XSLTName jp2nlmx2.xml?> it breaks iterparse!
    return PE.sub(b"", resp.content) if strip_pi else resp.content


class EPMC:
    REMOVE_META = (
        "contrib-group",
        "author-notes",
        "history",
        "kwd-group",
        "article-id",
        "article-categories",
        "aff",
        "pub-date",
        "elocation-id",
        "permissions",
        "issue",
        "volume",
    )

    REMOVE = (
        "ref-list",
        "floats-group",
        "front > journal-meta",
        "back",
        "supplementary-material",
        "named-content",
        "funding-source",
        "fn",
        "fpage",
        "lpage",
        "funding-group",
        "award-id",
        "self-uri",
        "counts",
        "custom-meta-group",
        "issue-id",
        "alt-title",
    )

    PARSER = "lxml-xml"

    def __init__(self, content: bytes, **kwargs: Any):
        self.soup = BeautifulSoup(BytesIO(content), self.PARSER)
        self.missing: set[str] = set()
        self.md_style = {**MD_STYLE, **kwargs}

    @classmethod
    def from_pmcid(
        cls,
        pmcid: str,
        session: Session | None = None,
        strip_pi: bool = True,
        **kwargs: Any,
    ) -> Self:
        content = epmc(pmcid, session, strip_pi=strip_pi)
        if not content:
            raise ValueError(f"no content for {pmcid}")

        return cls(content, **kwargs)

    @classmethod
    def from_file(
        cls,
        filename: str | Path,
        *,
        strip_pi: bool = True,
        **kwargs: Any,
    ) -> Self:
        with open(filename, "rb") as fp:
            content = fp.read()
        if strip_pi:
            content = PE.sub(b"", content)
        return cls(content, **kwargs)

    def get_article(self) -> Tag | None:
        article = self.soup.select("article")
        if not article:
            return None
        return article[0]

    def save_content(self, save: str | Path, pretty: bool = False) -> None:
        a = self.soup.prettify() if pretty else str(self.soup)
        with open(save, "w", encoding="utf-8") as fp:
            fp.write(a)

    def cull(self, article: Tag) -> Tag:
        remove = list(self.REMOVE)
        remove.extend(f"front > article-meta > {m}" for m in self.REMOVE_META)
        css = ",".join(remove)

        for s in article.select(css):
            s.decompose()
        return article

    def extract(self, article: Tag) -> Outline:
        title = article.select("> front > article-meta > title-group > article-title")[
            0
        ]
        abstract = article.select("> front > article-meta > abstract")[0]
        body = article.select("> body")[0]
        return Outline(title, abstract, body)

    def html(self) -> str | None:
        article = self.get_article()
        if article is None:
            return None
        article = self.cull(article)
        pmc = PMCEvents()
        html = "".join(pmc.parse(BytesIO(str(article).encode("utf-8"))))
        self.missing = pmc.missing
        return html

    def html_to_markdown(self, html: str) -> str:
        return convert_to_markdown(html, **self.md_style)

    def markdown(self):
        return self.html_to_markdown(self.html())
