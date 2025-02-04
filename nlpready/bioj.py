from __future__ import annotations

from typing import TYPE_CHECKING

import click
import requests

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup
    from ._mlabc import Response, Paper


ISSN = {"1470-8728": "Biochem. J.", "0264-6021": "Biochem. J."}


class BIOJ(Clean):
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
            for a in sec.select("p a.xref-bibr"):
                a.replace_with("CITATION")
            for a in sec.select("div.fig.pos-float"):
                a.replace_with(self.newfig(a, caption=".fig-caption p"))
            for a in sec.select("div.table.pos-float"):
                a.replace_with(self.newtable(a, caption=".table-caption p"))

        return super().tostr(seclist)


class GenerateBIOJ(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return BIOJ(soup)


def gen_bioj(issn: str) -> None:

    gad = GenerateBIOJ(issn)
    gad.run()


def download_bioj(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://www.biochemj.org"

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
            if not a:
                click.secho(
                    f"no full text {paper.pmid} http://doi.org/{paper.doi}",
                    fg="red",
                )
                return b"no full-text"
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_bioj(issn: str) -> None:

    b = GenerateBIOJ(issn)
    print(b.tohtml())


if __name__ == "__main__":
    download_bioj(issn="1470-8728", sleep=120.0, mx=0)
    download_bioj(issn="0264-6021", sleep=120.0, mx=0)
    # gen_bioj(issn='0264-6021')
