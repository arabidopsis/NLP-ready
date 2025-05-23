from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup
    from ._mlabc import Response, Paper


# BMC Plant Biology

ISSN = {
    "1471-2229": "BMC Plant Biol.",
    # added
    "1472-6750": "BMC Biotechnol.",
    "1471-2164": "BMC Genomics",
    "1756-0500": "BMC Res Notes",
    "1474-760X": "Genome Biol.",
    "1746-4811": "Plant Methods",
    "1471-2121": "BMC Cell Biol.",
    "1471-2148": "BMC Evol. Biol.",
    "1477-5956": "Proteome Sci",
    "1759-8753": "Mob DNA",
}


class PMCPB(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select(".FulltextWrapper section.Abstract")
        assert a, a
        self.article = a[0].parent

    def results(self) -> list[Tag]:
        if self.article is None:
            return []
        secs = self.article.select("section.Section1")
        for sec in secs:
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion", "result"}:
                    return [sec]

        return []

    def methods(self) -> list[Tag]:
        if self.article is None:
            return []
        secs = self.article.select("section.Section1")
        for sec in secs:
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
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
        if self.article is None:
            return []
        secs = self.article.select("section.Abstract")
        return [secs[0]] if secs else []

    def title(self) -> str | None:
        t = self.root.select(".FulltextWrapper .MainTitleSection h1")
        return t[0].text.strip()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("p figure,div.Para figure"):

                if "FigureTable" in a["class"]:
                    a.replace_with(self.newtable(a, node="span"))
                else:
                    a.replace_with(self.newfig(a, node="span"))

            for a in sec.select("span.CitationRef"):
                a.replace_with("CITATION")

        def paraordiv(tag):
            return tag.name == "p" or (
                tag.name == "div" and tag.has_attr("class") and "Para" in tag["class"]
            )

        txt = [
            self.SPACE.sub(" ", p.text)
            for sec in seclist
            for p in sec.find_all(paraordiv)
        ]
        return txt


class GeneratePMCPB(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return PMCPB(soup)


def gen_bmcpb(issn: str) -> None:

    g = GeneratePMCPB(issn)
    g.run()


def download_bmcpb(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "https://bmcplantbiol.biomedcentral.com"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select(".FulltextWrapper section.Abstract")
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_bmcpb(issn: str) -> None:

    g = GeneratePMCPB(issn)
    print(g.tohtml())


if __name__ == "__main__":
    download_bmcpb(issn="1471-2229", sleep=120.0, mx=0)
