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

# http://genesdev.cshlp.org


ISSN = {"0890-9369": "Genes Dev."}


class GAD(Clean):
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
            for a in sec.select("div.fig.pos-float"):
                a.replace_with(self.newfig(a, caption=".fig-caption p"))
            for a in sec.select("p a.xref-bibr"):
                a.replace_with("CITATION")
        return super().tostr(seclist)


class GenerateGAD(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return GAD(soup)


def gen_gad(issn: str) -> None:

    gad = GenerateGAD(issn)
    gad.run()


def download_gad(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://genesdev.cshlp.org"

        def get_response(self, paper, header):
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
            # if not a and year <= 2001:  # probably only a (scanned?) PDF version
            #    xml = b'failed-only-pdf'
            #     d = fdir
            #    failed.add(pmid)
            # else:
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_gad(issn: str) -> None:

    gad = GenerateGAD(issn)
    print(gad.tohtml())


if __name__ == "__main__":

    download_gad(issn="0890-9369", sleep=120.0, mx=0)
    # gen_gad(issn='0890-9369')
