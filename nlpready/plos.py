from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate


if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup

ISSN = {
    "1932-6203": "PLoS ONE",
    "1553-7404": "PLoS Genet.",
    "1545-7885": "PLoS Biol.",
    "1553-7374": "PLoS Pathog.",
}


class PLOS(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("div.article-text")
        assert a, a
        self.article = a[0]

    def results(self) -> list[Tag]:
        secs = self.article.select("div.section.toc-section")
        for sec in secs:
            if self.find_title(
                sec,
                txt=["results and discussion", "results", "result"],
            ):
                return [sec]

        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select("div.section.toc-section")
        for sec in secs:
            if self.find_title(
                sec,
                txt=[
                    "materials & methods",
                    "materials and methods",
                    "material and methods",
                    "methods",
                ],
            ):  # spelling!
                return [sec]

        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select("div.toc-section.abstract")
        return [secs[0]] if secs else []

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("div.figure"):
                a.replace_with(self.newfig(a, caption=".figcaption"))
            for a in sec.select("span.equation"):  # e.g. math equations
                a.replace_with("[[EQUATION]]")
            for a in sec.select("span.inline-formula"):  # e.g. math equations
                a.replace_with("[[EQUATION]]")
            for a in sec.select("p a.ref-tip"):
                a.replace_with("CITATION")

        return super().tostr(seclist)


def download_plos(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://www.plosone.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article-text")
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GeneratePLOS(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return PLOS(soup)


def gen_plos(issn: str) -> None:
    e = GeneratePLOS(issn)
    e.run()


def html_plos(issn: str) -> None:
    e = GeneratePLOS(issn)
    print(e.tohtml())


if __name__ == "__main__":
    download_plos(issn="1932-6203", sleep=60 * 2.0, mx=0)
    # html_plos(issn='1932-6203')
