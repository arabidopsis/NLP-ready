from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import dump
from ._mlabc import Generate

if TYPE_CHECKING:

    from bs4 import BeautifulSoup, Tag
    from ._mlabc import Response, Paper


ISSN = {
    "1573-5028": "Plant Mol. Biol.",
    "0167-4412": "Plant Mol. Biol.",
    "1432-2048": "Planta",
    "0032-0935": "Planta",
    "1615-6102": "Protoplasma",
    "0033-183X": "Protoplasma",
    "1617-4623": "Mol. Genet. Genomics",
    "1617-4615": "Mol. Genet. Genomics",
    "0918-9440": "J. Plant Res.",
    "1618-0860": "J. Plant Res.",
    "1432-203X": "Plant Cell Rep.",
    "0721-7714": "Plant Cell Rep",
    "0009-5915": "Chromosoma",
    "1432-0886": "Chromosoma",
    "1573-4978": "Mol. Biol. Rep.",
    # added
    "0040-5752": "Theor. Appl. Genet.",
    "1432-2242": "Theor. Appl. Genet.",
    "0172-8083": "Curr. Genet.",
    "0175-7598": "Appl. Microbiol. Biotechnol.",
    "0219-1032": "Mol. Cells",
    "0949-944X": "Dev. Genes Evol.",
    "1420-682X": "Cell. Mol. Life Sci.",
    "1438-793X": "Funct. Integr. Genomics",
    "1438-7948": "Funct. Integr. Genomics",
    "1466-1268": "Cell Stress Chaperones",
    "2194-7961": "Plant Reprod",
    "2193-1801": "Springerplus",
    "1438-2199": "Amino Acids",
    "1939-8425": "Rice (N Y)",
    "0166-8595": "Photosyn. Res.",
    "1573-5079": "Photosyn. Res.",
    "1573-6776": "Biotechnol. Lett.",
    "0962-8819": "Transgenic Res.",
    "1559-0305": "Mol. Biotechnol.",
    "0098-0331": "J. Chem. Ecol.",
    "1940-6029": "Methods Mol. Biol.",
    "1869-1889": "Sci China Life Sci",
    "1573-9368": "Transgenic Res.",
}


class Springer(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("main#main-content article.main-body__content")
        assert a
        self.article = a[0]

    def results(self) -> list[Tag]:
        secs = self.article.select("#body section.SectionTypeResults")
        if secs:
            return [secs[0]]
        for sec in self.article.select("#body section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return [sec]
        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select("#body section.SectionTypeMaterialsAndMethods")
        if secs:
            return [secs[0]]
        for sec in self.article.select("#body section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {
                    "materials and methods",
                    "methods and materials",
                    "experimental procedures",
                    "methods",
                }:
                    return [sec]
        return []

    def abstract(self) -> list[Tag]:

        secs = self.article.select("section.Abstract")
        if secs:
            return [secs[0]]
        secs = self.article.select("div.section.abstract")
        return [secs[0]] if secs else []

    def title(self):
        s = self.root.select("h1.ArticleTitle")
        if s:
            return s[0].text.strip()
        return super().title()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("figure"):
                a.replace_with(self.newfig(a, node="span"))
                # a.replace_with('[[FIGURE]]')

            for a in sec.select("div.Table"):
                a.replace_with(self.newtable(a, ".Caption p", node="span"))
                # a.replace_with('[[TABLE]]')

            for a in sec.select("span.CitationRef"):
                a.replace_with("CITATION")

        def para(tag):
            return tag.name == "p" or (
                tag.name == "div" and tag.has_attr("class") and "Para" in tag["class"]
            )

        # txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p, div.Para')]
        txt = [
            self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.find_all(para)
        ]
        return txt


class SpringerRice(Springer):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("body.journal-fulltext .FulltextWrapper > section")
        assert a
        article = a[0].parent
        assert article
        self.article = article

    def results(self) -> list[Tag]:

        for sec in self.article.select("section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return [sec]
        return []

    def methods(self) -> list[Tag]:
        for sec in self.article.select("section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()

                if txt in {
                    "materials and methods",
                    "methods and materials",
                    "experimental procedures",
                    "methods",
                }:
                    return [sec]
        return []


def download_springer(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "https://link.springer.com"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("main#main-content article.main-body__content")
            if not a and paper.issn == "1939-8425":
                a = soup.select("body.journal-fulltext .FulltextWrapper > section")
            if not a and paper.year < 2005:
                dump(paper, resp.content)
                return b"failed-only-pdf"
            assert a, (paper.pmid, resp.url, paper.doi)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateSpringer(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        if self.pmid2doi[pmid].issn == "1939-8425":
            return SpringerRice(soup)
        return Springer(soup)


def gen_springer(issn: str) -> None:
    e = GenerateSpringer(issn)
    e.run()


def html_springer(issn: str) -> None:
    e = GenerateSpringer(issn)
    print(e.tohtml())


def run() -> None:
    for issn in ISSN:
        download_springer(issn=issn, sleep=60.0 * 2, mx=0)


if __name__ == "__main__":
    run()
