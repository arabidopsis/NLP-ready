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
from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from ._issn import Location
    from ._types import Paper

logger = logging.getLogger("nlpready")

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
        html: str,
        css: Location,
        url: str | None = None,
        *,
        fmt: MD | None = None,
    ) -> str:
        t = self.soupify(html)
        if url:
            t = self.udpate_links(t, url)
        return "\n".join(
            self.get_text(a, css, fmt=fmt) for a in t.select(css.article_css)
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
    def save_html(self, html, path: Path) -> None:
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        with path.open("wt", encoding="utf8") as fp:
            fp.write(html)

    def udpate_links(self, soup: BeautifulSoup, url: str) -> BeautifulSoup:
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
            if "href" in a.attrs:
                href = a.attrs["href"]
                if href:
                    if not href.startswith(URLS):
                        a.attrs["href"] = add(href)
                if "title" in a.attrs:
                    a.attrs["title"] = sanitize(a.attrs["title"])
        for a in soup.select("img"):
            if "src" in a.attrs:
                src = a.attrs["src"]
                if src:
                    if not src.startswith(URLS):
                        a.attrs["src"] = add(src)
        return soup


class Selenium(Soup):

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 10,
        format: MD = "markdown",
        cache: str | Path | None = None,
        page_load_timeout: int = 20,
    ):
        super().__init__(format)
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("headless")
        self.timeout = timeout
        self.driver = webdriver.Chrome(options=options)
        self.cache = Path(cache) if cache else None
        self.wait_ = None
        if page_load_timeout:
            self.driver.set_page_load_timeout(page_load_timeout)

    # @classmethod
    # def has_driver(self) -> bool:
    #     return which('chromedriver') is not None

    @property
    def wait(self) -> WebDriverWait:
        if self.wait_ is not None:
            return self.wait_
        self.wait_ = WebDriverWait(self.driver, self.timeout)
        return self.wait_

    def wait_for_css(self, css: str) -> None:
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))

    def doi(self, doi_or_url: str, css: Location | None = None) -> str:
        if not doi_or_url.startswith(("https://", "http://")):
            doi_or_url = f"https://doi.org/{doi_or_url}"
        self.driver.get(doi_or_url)
        url = self.current_url
        if css and url:
            new_url = css.full(url)
            if new_url != url:
                self.driver.get(new_url)
        try:
            if css is not None:
                wait = css.wait_css if css.wait_css else css.article_css
            else:
                wait = "html"
            self.wait_for_css(wait)

            html = self.find_html()
        except TimeoutException:
            logger.warning("timeout[%s] for: %s", self.timeout, doi_or_url)
            html = ""
        return html

    @property
    def current_url(self) -> str | None:
        try:
            return self.driver.current_url
        except InvalidSessionIdException:
            return None

    def fetch_html(self, doi_or_url: str, css: Location | None = None) -> str | None:
        html = self.doi(doi_or_url, css)
        if not html:
            if self.is_cloudflare_challenge():
                return None
        return html

    def run(
        self,
        doi_or_url: str,
        css: Location,
        *,
        fmt: MD | None = None,
    ) -> str | None:
        html = self.fetch_html(doi_or_url, css)
        if not html:
            return html
        return self.tofrag(html, css, self.current_url, fmt=fmt)

    def check_run(
        self,
        paper: Paper,
        css: Location,
        *,
        fmt: MD | None = None,
    ) -> str | None:
        html = None
        if self.cache:
            path = self.cache / f"{paper.pmid}.html"
            if path.exists():
                with path.open("rt", encoding="utf8") as fp:
                    html = fp.read()
        if not html:
            html = self.fetch_html(paper.doi, css)
            if html and self.cache:
                path = self.cache / f"{paper.pmid}.html"
                with path.open("wt", encoding="utf8") as fp:
                    fp.write(html)
        if not html:
            return html
        return self.tofrag(html, css, self.current_url, fmt=fmt)

    def rerun(self, css: Location, *, fmt: MD | None = None) -> str:
        return self.tofrag(self.find_html(), css, fmt=fmt)

    def close(self):
        self.driver.close()  # or quit()?
        self.driver = None

    def __del__(self):
        if self and self.driver is not None:
            try:
                self.close()
            except InvalidSessionIdException:
                pass

    def is_cloudflare_challenge(self) -> bool:
        scripts = [
            a.get_attribute("src")
            for a in self.driver.find_elements(by=By.TAG_NAME, value="script")
        ]
        return any(
            [
                "https://challenges.cloudflare.com" in src
                for src in scripts
                if src is not None
            ],
        )

    def find_html(self) -> str:
        h = self.driver.find_element(by=By.TAG_NAME, value="html")
        return h.get_attribute("outerHTML") or ""

    def resoupify(self) -> BeautifulSoup:
        return self.soupify(self.find_html())

    def pdf(self, css: Location) -> bytes | None:
        if not css.pdf_accessible:
            return None
        url = self.current_url
        if not url:
            return None
        soup = self.resoupify()
        return css.pdf(soup, url)
