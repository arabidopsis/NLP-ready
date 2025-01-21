from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

if TYPE_CHECKING:
    from bs4 import BeautifulSoup, Tag
    from ._mlabc import Response, Paper


# http://genesdev.cshlp.org


ISSN = {
    "2050-084X": "Elife",
}


class Elife(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("main")
        assert a, a
        self.article = a[0]

    def results(self) -> list[Tag]:
        for sec in self.article.select("section.article-section"):
            h2 = sec.find("h2")
            if h2 and h2.text:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return [sec]

        return []

    def methods(self) -> list[Tag]:
        for sec in self.article.select("section.article-section"):
            h2 = sec.find("h2")
            if h2 and h2.text:
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
        secs = self.article.select("#abstract")
        return [secs[0]] if secs else []

    def title(self) -> str | None:
        return self.article.select("h1.content-header__title")[0].text.strip()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("div.asset-viewer-inline"):
                idattr = a.attrs.get("id")
                if not idattr:
                    continue

                if idattr.startswith("fig"):
                    a.replace_with(self.newfig(a))
                elif idattr.startswith("tbl"):
                    a.replace_with(self.newtable(a))
        for sec in seclist:
            for a in sec.select("p a"):
                href = a.attrs.get("href")
                if not href or not href.startswith("#bib"):
                    continue
                a.replace_with("CITATION")
        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.select("p")]
        return txt


class GenerateElife(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return Elife(soup)


def gen_elife(issn: str) -> None:

    elife = GenerateElife(issn)
    elife.run()


def download_elife(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "https://elifesciences.org"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("main section.article-section")
            assert a, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_elife(issn: str) -> None:

    elife = GenerateElife(issn)
    print(elife.tohtml())


def run() -> None:
    for issn in ISSN:
        download_elife(issn=issn, sleep=10.0, mx=1)


if __name__ == "__main__":
    run()
