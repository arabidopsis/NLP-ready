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
from urllib3.exceptions import MaxRetryError
from urllib3.exceptions import NewConnectionError


if TYPE_CHECKING:
    from .issn import Location
    from selenium.webdriver.remote.webdriver import WebDriver

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


# from https://stackoverflow.com/questions/68289474
# /selenium-headless-how-to-bypass-cloudflare-detection-using-selenium
def get_service():
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    return Service(ChromeDriverManager().install())


def stealth_driver(headless: bool = True) -> WebDriver:
    from .config import USER_AGENT
    import undetected_chromedriver as uc
    from selenium_stealth import stealth

    chrome_options = uc.ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    driver = uc.Chrome(options=chrome_options)
    # driver = uc.Chrome(service=get_service(), options=chrome_options)
    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver


class Selenium(Soup):

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 10,
        format: MD = "markdown",
        page_load_timeout: int = 20,
    ):
        super().__init__(format)
        self.wait_ = None
        self.timeout = timeout
        self.driver = self.mkdriver(headless)
        if page_load_timeout:
            self.driver.set_page_load_timeout(page_load_timeout)

    def mkdriver(self, headless: bool = True) -> WebDriver:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("headless")
        return webdriver.Chrome(options=options)

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
            logger.info("timeout[%s] for: %s", self.timeout, doi_or_url)
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
    ) -> tuple[str | None, BeautifulSoup | None]:
        html = self.fetch_html(doi_or_url, css)
        if not html:
            return None, None
        soup = self.soupify(html)
        soup = self.update_links(soup, self.current_url)
        return self.tofrag(soup, css, fmt=fmt), soup

    def rerun(
        self,
        css: Location,
        *,
        fmt: MD | None = None,
    ) -> tuple[str | None, BeautifulSoup | None]:
        soup = self.resoupify()
        soup = self.update_links(soup, self.current_url)
        return self.tofrag(soup, css, fmt=fmt), soup

    def close(self):
        self.driver.close()  # or quit()?
        self.driver = None

    def __del__(self):
        if self and self.driver is not None:
            try:
                self.close()
            except (InvalidSessionIdException, MaxRetryError, NewConnectionError):
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

    def stealth(self) -> str:
        self.driver.get("https://bot.sannysoft.com/")
        return self.driver.find_element(By.XPATH, "/html/body").text


class StealthSelenium(Selenium):

    def mkdriver(self, headless: bool = True) -> WebDriver:
        return stealth_driver(headless)
