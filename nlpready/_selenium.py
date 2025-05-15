from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

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

logger = logging.getLogger("nlpready")


class Soup:

    def __init__(self, as_markdown: bool = True):
        self.as_markdown = as_markdown

    def soupify(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(StringIO(html))

    def soup(self, html: str, css: Location) -> str:
        t = self.soupify(html)
        return "\n".join(self.get_text(a, css) for a in t.select(css.article_css))

    def get_text(self, article: Tag, css: Location) -> str:
        if css.remove_css:
            for ref in article.select(css.remove_css):
                ref.decompose()
        if self.as_markdown:
            return convert_to_markdown(article.prettify())
        return article.get_text(" ")

    @classmethod
    def save_html(self, html, path: Path) -> None:
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        with path.open("wt", encoding="utf8") as fp:
            fp.write(html)


class Selenium(Soup):

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 10,
        as_markdown: bool = True,
        path: str | Path | None = None,
    ):
        super().__init__(as_markdown)
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("headless")
        self.timeout = timeout
        self.driver = webdriver.Chrome(options=options)
        self.as_markdown = as_markdown
        self.path = path
        self.wait_ = None

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
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css)))

    def doi(self, doi: str, css: Location | None = None) -> str:

        url = f"https://doi.org/{doi}"
        self.driver.get(url)
        try:
            if css is not None:
                wait = css.wait_css if css.wait_css else css.article_css
            else:
                wait = "html"
            self.wait_for_css(wait)

            html = self.find_html()
        except TimeoutException:
            logger.warning("timeout for: %s", url)
            html = ""
        return html

    def run(self, doi: str, css: Location) -> str | None:
        html = self.doi(doi, css)
        if not html:
            if self.is_cloudflare_challenge():
                return None
            return html
        if self.path is not None:
            self.save_html(html, Path(self.path))
        return self.soup(html, css)

    def rerun(self, css: Location) -> str:
        return self.soup(self.find_html(), css)

    def close(self):
        self.driver.close()
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
