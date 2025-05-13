from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class ISSN:
    article_css: str
    remove_css: str


DATA = {
    "1532-2548": ISSN(".widget-instance-OUP_Article_FullText_Widget", ".ref-list"),
    "1365-313X": ISSN(
        ".article__body",
        "section.article-section__references,section.article-section__citedBy",
    ),
    "1873-3468": ISSN(
        ".article__body",
        "section.article-section__references,section.article-section__citedBy",
    ),
    "1664-462X": ISSN(".JournalFullText .JournalFullText", ".References"),
    "2045-2322": ISSN(".main-content", ""),
}


class Selenium:

    def __init__(self, headless: bool = True, timeout: int = 10):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("headless")
        self.timeout = timeout
        self.driver = webdriver.Chrome(options=options)
        self.wait_ = None

    @property
    def wait(self) -> WebDriverWait:
        if self.wait_ is not None:
            return self.wait_
        self.wait_ = WebDriverWait(self.driver, self.timeout)
        return self.wait_

    def wait_for_css(self, css: str) -> None:
        self.wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, css)))

    def doi(self, doi: str, css: ISSN | None = None) -> str:

        url = f"https://doi.org/{doi}"
        self.driver.get(url)
        try:
            self.wait_for_css(css.article_css if css else "html")
            h = self.driver.find_element(by=By.TAG_NAME, value="html")

            txt = h.get_attribute("outerHTML") or ""
        except TimeoutException:
            print("timeout", url)
            txt = ""
        return txt

    def soup(self, text: str, css: ISSN) -> str:
        t = BeautifulSoup(StringIO(text))
        return " ".join(self.get_text(a, css) for a in t.select(css.article_css))

    def get_text(self, article: WebElement, css: ISSN) -> str:
        if css.remove_css:
            for ref in article.select(css.remove_css):
                ref.decompose()
        return article.get_text(" ")

    def run(self, doi: str, css: ISSN) -> str:
        txt = self.doi(doi, css)
        if not txt:
            return txt
        return self.soup(txt, css)

    def close(self):
        self.driver.close()
        self.driver = None
