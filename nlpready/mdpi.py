from __future__ import annotations

from typing import TYPE_CHECKING

import requests
from bs4 import Tag

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

# http://genesdev.cshlp.org

if TYPE_CHECKING:

    from ._mlabc import Response
    from bs4 import BeautifulSoup
    from ._mlabc import Paper

ISSN = {
    "1422-0067": "Int J Mol Sci",
    "1420-3049": "Molecules",
}


class MDPI(Clean):
    def __init__(self, root: BeautifulSoup):
        super().__init__(root)
        a = root.select("article")
        assert a, a
        self.article = a[0]
        self.figures: dict[str, Tag] = {}

    def results(self) -> list[Tag]:
        for sec in self.article.select(".html-body section"):
            if sec.attrs.get("type") == "results":
                return [sec]
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                for t in ["results", "results and discussion"]:
                    if txt.endswith(t):
                        return [sec]

        return []

    def methods(self) -> list[Tag]:
        for sec in self.article.select(".html-body section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                for t in [
                    "methods",
                    "experimental procedures",
                    "materials and methods",
                    "material and methods",
                    "experimental section",
                ]:  # spelling!
                    if txt.endswith(t):
                        return [sec]

        return []

    def abstract(self) -> list[Tag]:
        secs = self.root.select("article div.html-front #html-abstract")
        return [secs[0]] if secs else []

    def title(self) -> str | None:
        secs = self.root.select("article div.html-front #html-article-title")
        return secs[0].text.strip()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        figs = []
        for sec in seclist:
            for a in sec.select("div.html-p a.html-bibr"):
                a.replace_with(" CITATION ")

            for a in sec.select("div.html-p a.html-fig"):
                href = str(a["href"])
                if href not in self.figures:
                    n = self.root.select(href)[0]
                    self.figures[href] = n.select(".html-fig_description")[0]
                    figs.append(href)

                a.replace_with(" FIG-REF ")

        # for a in sec.select('.html-fig-wrap'):
        #     # figures are placed by some javascript I think... so this doesn't work
        #     p = self.root.new_tag('div', **{'class': 'html-p'})
        #     p.string = '[[FIGURE]]'
        #     a.replace_with(p)

        figs = [
            self.FIGURE % self.SPACE.sub(" ", self.figures[href].text) for href in figs
        ]

        txt = [
            self.SPACE.sub(" ", p.text)
            for sec in seclist
            for p in sec.select("div.html-p")
        ]
        if not txt:
            txt = [
                self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.select("p")
            ]
        if not txt:
            txt = [
                " ".join(
                    [
                        self.SPACE.sub(" ", p.string)
                        for sec in seclist
                        for p in sec.contents
                        if isinstance(p, Tag)
                    ],
                ),
            ]

        return txt + figs


class GenerateMDPI(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return MDPI(soup)


def gen_mdpi(issn: str) -> None:

    mdpi = GenerateMDPI(issn)
    mdpi.run()


def download_mdpi(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://www.mdpi.com"

        def get_response(self, paper, header):
            resp = requests.get(f"http://doi.org/{paper.doi}", headers=header)
            if not resp.url.endswith("/htm"):
                resp = requests.get(resp.url + "/htm", headers=header)
            return resp

    def check_soup(
        self,
        paper: Paper,
        soup: BeautifulSoup,
        resp: Response,
    ) -> bytes | None:
        a = soup.select("article div.html-body")
        # if not a and year <= 2001:  # probably only a (scanned?) PDF version
        #    xml = b'failed-only-pdf'
        #     d = fdir
        #    failed.add(pmid)
        # else:
        assert a and len(a) == 1, (paper.pmid, resp.url)
        return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_mdpi(issn: str) -> None:

    mdpi = GenerateMDPI(issn)
    print(mdpi.tohtml())


if __name__ == "__main__":

    download_mdpi(issn="1422-0067", sleep=10.0, mx=1)
