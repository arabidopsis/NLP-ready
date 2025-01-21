from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup
    from ._mlabc import Response, Paper


ISSN = {
    "1460-2075": "EMBO J.",
    "0261-4189": "EMBO J.",
    "1469-221X": "EMBO Rep.",
    "1469-3178": "EMBO Rep.",
    "1744-4292": "Mol. Syst. Biol.",
}


class EMBOJ(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("div.article.fulltext-view")
        assert a, a
        self.article = a[0]

    def title(self) -> str | None:
        s = self.root.select("#embo-page-title")
        if s:
            return s[0].text.strip()
        return super().title()

    def results(self) -> list[Tag]:
        secs = self.article.select("div.section.results-discussion")
        if secs:
            return [secs[0]]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results and discussion", "results"}:
                    return [sec]

        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select("div.section.methods")
        if not secs:
            secs = self.article.select("div.section.materials-methods")
        if secs:
            return [secs[0]]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"materials and methods", "methods"}:
                    return [sec]
        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select("div.section.abstract")
        # print(secs)
        return [secs[0]] if secs else []

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("div.fig.pos-float"):
                a.replace_with(self.newfig(a, caption=".fig-caption p"))
            for a in sec.select("div.table.pos-float"):
                a.replace_with(self.newtable(a, caption=".table-caption"))
            for a in sec.select("p a.xref-ref"):
                a.replace_with("CITATION")
            for a in sec.select("p a.xref-fig"):
                a.replace_with("FIG-REF")

        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.select("p")]
        return txt


def download_emboj(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://emboj.embopress.org"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("div.article.fulltext-view")
            assert a and len(a) == 1, (paper, resp.url)
            return None

    e = D(issn, sleep=sleep, mx=mx)
    e.run()


class GenerateEMBJ(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return EMBOJ(soup)


def gen_emboj(issn: str) -> None:

    e = GenerateEMBJ(issn)
    e.run()


def html_emboj(issn: str) -> None:

    e = GenerateEMBJ(issn)
    print(e.tohtml())


if __name__ == "__main__":
    # this is also a Wiley thing
    download_emboj(issn="1460-2075", sleep=60.0 * 2, mx=0)
    download_emboj(issn="0261-4189", sleep=60.0 * 2, mx=0)
    # html_emboj(issn='1460-2075')
