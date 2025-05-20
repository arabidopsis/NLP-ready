from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.exceptions import MaxRetryError
from urllib3.exceptions import NewConnectionError

from .cache import Cache
from .issn import ISSN_MAP
from .runner import Runner
from .soup import logger
from .soup import MD
from .soup import Soup
from .utils import getconfig


if TYPE_CHECKING:
    from .issn import Location
    from selenium.webdriver.remote.webdriver import WebDriver
    from tqdm import tqdm


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


class SeleniumRunner(Runner):
    web: Selenium
    cache: Cache

    def start(self):
        self.web = self.create_driver()
        self.cache = (
            Cache(self.cache_dir) if self.cache_dir else Cache(getconfig().data_dir)
        )

    def create_driver(self):
        return StealthSelenium(headless=True)

    def work(self, paper, tqdm: tqdm) -> str:
        tqdm.write(f"working... {paper.pmid}")
        if not paper.doi:
            return "nodoi"
        if paper.issn not in ISSN_MAP:
            return "noissn"

        try:
            html = self.web.fetch_html(paper.doi, ISSN_MAP[paper.issn])
            if html is None:
                self.web = self.create_driver()
                tqdm.write("retry....")
                html = self.web.fetch_html(paper.doi, ISSN_MAP[paper.issn])
            if html is None:
                retval = "cc"
            elif not html:
                retval = "timeout"
            else:
                self.cache.save_html(paper, html)
                retval = "ok"
        except Exception as e:
            tqdm.write(f"failed: {paper.pmid} {e}")
            retval = "failed"
        tqdm.write(retval)
        return retval

    def end(self):
        self.web.close()
