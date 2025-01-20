from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from bs4 import Tag

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

if TYPE_CHECKING:
    from ._mlabc import Paper
    from ._mlabc import Response

ISSN = {
    "1664-462X": "Front Plant Sci",
    "2296-634X": "Front Cell Dev Biol",
}


class FPLS(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = self.root.select("div.article-section div.JournalFullText")
        assert a, a
        self.article = a[0]
        self.search()

    def search(self) -> None:

        objs = defaultdict(list)
        target = None
        for d in self.article.contents:
            if not isinstance(d, Tag):
                continue
            if d.name == "h2":
                target = d.text.lower().strip()
            elif d.name == "p":
                if target:
                    objs[target].append(d)
            elif d.name == "div" and "FigureDesc" in d["class"]:
                if target:
                    p = self.newfig(d, caption="p")
                    d.replace_with(p)
                    objs[target].append(p)

        res: dict[str, list[Tag]] = {}
        sections = {
            "results",
            "materials and methods",
            "results and discussion",
            "material and methods",
        }  # spelling!
        for k in objs:
            if k in sections:
                res[k] = objs[k]
        # assert set(res) == sections, (set(res))
        self.resultsd: dict[str, list[Tag]] = res

    def results(self) -> list[Tag]:
        return (
            self.resultsd.get("results")
            or self.resultsd.get(
                "results and discussion",
            )
            or []
        )

    def methods(self) -> list[Tag]:
        return (
            self.resultsd.get("materials and methods")
            or self.resultsd.get(
                "material and methods",
            )
            or []
        )

    def abstract(self) -> list[Tag]:
        secs = self.root.select("div.article-section div.JournalAbstract p")
        return list(secs) if secs else []

    def title(self) -> str | None:
        return self.root.select("div.article-section div.JournalAbstract h1")[
            0
        ].text.strip()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for p in sec:
                if not isinstance(p, Tag):
                    continue
                for a in p.select("a"):
                    href = a.attrs.get("href")
                    if href and href.startswith("#B"):
                        a.replace_with("CITATION")
        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec]
        return txt


class GenerateFPLS(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return FPLS(soup)


def gen_fpls(issn: str) -> None:

    g = GenerateFPLS(issn)
    g.run()


def download_fpls(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "https://www.frontiersin.org"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("div.article-section div.JournalFullText")

            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_fpls(issn: str) -> None:

    g = GenerateFPLS(issn)
    print(g.tohtml())


if __name__ == "__main__":
    download_fpls(issn="1664-462X", sleep=10.0, mx=3)
