from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup

ISSN = {
    "0021-9533": "J. Cell. Sci.",
    "1477-9137": "J. Cell. Sci.",
    # added
    "0021-9525": "J. Cell Biol.",
    "1540-8140": "J. Cell Biol.",
}


class JCS(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("div.article.fulltext-view")
        assert a, a
        self.article = a[0]

    def results(self) -> list[Tag]:
        secs = self.article.select("div.section.results")
        if secs:
            return [secs[0]]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return [sec]

        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select("div.section.materials-methods")
        if secs:
            return [secs[0]]
        secs = self.article.select("div.section.methods")
        if secs:
            return [secs[0]]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {
                    "methods",
                    "experimental procedures",
                    "materials and methods",
                    "material and methods",
                }:  # spelling!
                    return [sec]

        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select("div.section.abstract")
        return [secs[0]] if secs else []

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("div.table.pos-float"):
                a.replace_with(self.newtable(a, caption=".table-caption p"))
            for a in sec.select("div.fig.pos-float"):
                a.replace_with(self.newfig(a, caption=".fig-caption p"))
            for a in sec.select("p a.xref-bibr"):
                a.replace_with("CITATION")
        return super().tostr(seclist)


class GenerateJCS(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return JCS(soup)


def gen_jcs(issn: str) -> None:

    jcs = GenerateJCS(issn)
    jcs.run()


def download_jcs(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://jcs.biologists.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article.fulltext-view")
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_jcs(issn: str) -> None:

    jcs = GenerateJCS(issn)
    print(jcs.tohtml())


if __name__ == "__main__":
    download_jcs(issn="0021-9533", sleep=120.0, mx=0)
    download_jcs(issn="1477-9137", sleep=120.0, mx=0)
    # gen_gad(issn='0890-9369')
