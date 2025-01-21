from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

if TYPE_CHECKING:

    from bs4 import BeautifulSoup, Tag
    from ._mlabc import Response, Paper


ISSN = {
    "0894-0282": "Mol. Plant Microbe Interact.",
}


class MPMI(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("table .pubContent")
        assert a, a
        self.article = a[0]

    def results(self) -> list[Tag]:
        secs = self.article.select(
            ".hlFld-Fulltext .NLM_sec-type_results.NLM_sec_level_1",
        )
        if secs:
            return [secs[0]]
        secs = self.article.select(".hlFld-Fulltext .NLM_sec_level_1")
        for sec in secs:
            h2 = sec.select("table tr th")
            if h2:
                txt = h2[0].text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return [sec]

        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select(
            ".hlFld-Fulltext .NLM_sec-type_materials|methods.NLM_sec_level_1",
        )
        if secs:
            return [secs[0]]
        secs = self.article.select(
            ".hlFld-Fulltext .MaterialsAndMethods.NLM_sec_level_1",
        )
        if secs:
            return [secs[0]]
        secs = self.article.select(".hlFld-Fulltext .NLM_sec_level_1")
        for sec in secs:
            h2 = sec.select("table tr th")
            if h2:
                txt = h2[0].text.lower().strip()
                if txt in {
                    "experimental section",
                    "methods",
                    "experimental procedures",
                    "materials and methods",
                    "material and methods",
                }:  # spelling!
                    return [sec]

        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select(".hlFld-Abstract .abstractInFull")
        return [secs[0]] if secs else []

    def title(self) -> str | None:
        return self.article.select(".hlFld-Abstract .hlFld-Title")[0].text.strip()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("div.figure"):
                p = self.root.new_tag("p")  # , **{'class': 'NLM_p'})

                p.string = "[[FIGURE]]"
                a.replace_with(p)
            for a in sec.select("p span.ref-lnk"):
                a.replace_with("CITATION")
            for a in sec.select("p a.ref.bibr"):
                a.replace_with("CITATION")

        return super().tostr(seclist)


class GenerateMPMI(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return MPMI(soup)


def gen_mpmi(issn: str) -> None:

    g = GenerateMPMI(issn)
    g.run()


def download_mpmi(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "https://apsjournals.apsnet.org"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("table .pubContent div.hlFld-Fulltext")
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_mpmi(issn: str) -> None:

    g = GenerateMPMI(issn)
    print(g.tohtml())


if __name__ == "__main__":
    download_mpmi(issn="0894-0282", sleep=10.0, mx=2)
