from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate


if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup
    from ._mlabc import Paper
    from ._mlabc import Response

ISSN = {"0021-9258": "J. Biol. Chem.", "1083-351X": "J. Biol. Chem."}


class JBC(Clean):
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
                }:
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


def download_jbc(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://www.jbc.org"

        def get_response(self, paper: Paper, header: dict[str, str]) -> Response:
            resp = requests.get(f"http://doi.org/{paper.doi}", headers=header)
            if not resp.url.endswith(".full"):
                resp = requests.get(resp.url + ".full", headers=header)
            return resp

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("div.article.fulltext-view")
            if not a:
                if paper.year <= 2001:  # probably only a (scanned?) PDF version
                    return b"failed-only-pdf"
                assert a, (a, resp.url, paper.doi)
            return None

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


class GenerateJBC(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return JBC(soup)


def gen_jbc(issn: str) -> None:

    e = GenerateJBC(issn)
    e.run()


def html_jbc(issn: str) -> None:

    e = GenerateJBC(issn)
    print(e.tohtml())


if __name__ == "__main__":
    # download_jbc(issn='0021-9258', sleep=60. * 2, mx=0)
    # download_jbc(issn='1083-351X', sleep=60. * 2, mx=0)
    # gen_jbc(issn='0021-9258')
    # gen_jbc(issn='1083-351X')
    html_jbc(issn="0021-9258")
