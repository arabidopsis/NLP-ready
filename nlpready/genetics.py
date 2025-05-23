from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import DownloadSelenium
from ._mlabc import Generate


if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup
    from ._mlabc import Paper
    from ._mlabc import Response

ISSN = {
    "0016-6731": "Genetics",
    "1943-2631": "Genetics",
}
ARTICLE = ".widget.widget-ArticleFulltext.widget-instance-OUP_Article_FullText_Widget"
# ARTICLE = "div.widget-items[data-widgetname=ArticleFulltext]"


class Genetics(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        # a = root.select("div.article.fulltext-view")
        a = root.select(ARTICLE)
        assert a, a
        self.article = a[0]

    def results(self) -> list[Tag]:
        secs = self.article.select("div.section.results")
        if secs:
            return [secs[0]]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2 and h2.text:
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
        secs = self.article.select("section.abstract")
        return [secs[0]] if secs else []

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("div.table.pos-float"):
                a.replace_with(self.newtable(a, caption=".table-caption p"))
            for a in sec.select("div.fig.pos-float"):
                # print(a, file=sys.stderr)
                a.replace_with(self.newfig(a))
            for a in sec.select("p a.xref-bibr"):
                a.replace_with("CITATION")
        return super().tostr(seclist)


def download_genetics(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(DownloadSelenium):
        Referer = "http://www.genetics.org"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            # a = soup.select("div.article.fulltext-view")
            a = soup.select(ARTICLE)

            if not a:
                if paper.year <= 2001:  # probably only a (scanned?) PDF version
                    return b"failed-only-pdf"
                assert a, (a, resp.url, paper.doi)
            return None

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


class GenerateGenetics(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return Genetics(soup)


def gen_genetics(issn: str) -> None:

    e = GenerateGenetics(issn)
    e.run()


def html_genetics(issn: str) -> None:

    e = GenerateGenetics(issn)
    print(e.tohtml())


def run() -> None:
    for issn in ISSN:
        download_genetics(issn, sleep=10.0, mx=1)


if __name__ == "__main__":
    run()
