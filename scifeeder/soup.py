from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path
from typing import Any
from typing import Literal
from typing import TYPE_CHECKING
from typing import TypeAlias
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from bs4 import Tag
from html_to_markdown import convert_to_markdown


if TYPE_CHECKING:
    from .issn import Location

logger = logging.getLogger("scifeeder")

MD: TypeAlias = Literal["markdown", "pmarkdown", "html", "phtml", "text"]


def custom_div_converter(
    *,
    tag: Tag,
    text: str,
    convert_as_inline: bool,
    **kwargs,
) -> str:
    # if tag.attrs.get('role') == 'paragraph':
    return "\n" + text + "\n"


def sanitize(title: str) -> str:
    return " ".join(
        t
        for t in title.replace("[", "(").replace("]", ")").replace("\n", " ").split()
        if t
    )


MD_STYLE = dict(
    heading_style="atx",
    escape_misc=False,
    custom_converters={"div": custom_div_converter},
)


class Soup:
    PARSER = "lxml"

    def __init__(self, format: MD = "markdown", **kwargs: dict[str, Any]):
        self.format = format
        self.md_style = {**MD_STYLE, **kwargs}

    def soupify(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(StringIO(html), self.PARSER)

    def tofrag(
        self,
        soup: BeautifulSoup,
        css: Location,
        *,
        fmt: MD | None = None,
    ) -> str:
        if fmt is None:
            fmt = self.format
        return "\n".join(
            self.get_text(a, css, fmt=fmt) for a in soup.select(css.article_css)
        )

    def get_text(self, article: Tag, css: Location, *, fmt: MD | None = None) -> str:
        if css.remove_css:
            for ref in article.select(css.remove_css):
                ref.decompose()
        fmt = fmt or self.format
        if fmt == "markdown":
            return convert_to_markdown(str(article), **self.md_style)
        if fmt == "pmarkdown":
            return convert_to_markdown(
                article.prettify(),
                **self.md_style,
            )
        if fmt == "html":
            return str(article)
        if fmt == "phtml":
            return article.prettify()
        return article.get_text(" ")

    @classmethod
    def save_html(self, html: str, path: Path) -> None:
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        with path.open("wt", encoding="utf8") as fp:
            fp.write(html)

    def update_links(self, soup: BeautifulSoup, url: str | None) -> BeautifulSoup:
        if url is None:
            return soup
        if not url.endswith("/"):
            url += "/"
        purl = urlparse(url)
        baseurl = f"{purl.scheme}://{purl.netloc}"

        def add(ref: str) -> str:
            ref = ref.replace(" ", "%20").replace("|", "%7C").replace(",", "%2C")
            if ref.startswith("//"):
                return purl.scheme + ":" + ref
            if ref.startswith("/"):
                return baseurl + ref
            return url + ref

        URLS = ("https://", "http://")

        for a in soup.select("a"):
            href = a.get("href")

            if href:
                if not href.startswith(URLS):
                    a.attrs["href"] = add(href)
            title = a.get("title")
            if title:
                a.attrs["title"] = sanitize(title)
        for a in soup.select("img,script"):
            src = a.get("src")
            if src:
                if not src.startswith(URLS):
                    a.attrs["src"] = add(src)
        return soup
