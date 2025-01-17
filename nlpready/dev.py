from __future__ import annotations

from typing import TYPE_CHECKING

from .mlabc import Clean
from .mlabc import Download
from .mlabc import Generate

if TYPE_CHECKING:
    from bs4 import BeautifulSoup, Tag
    from .mlabc import Paper
    from requests import Response

ISSN = {"0950-1991": "Development", "1477-9129": "Development"}


class Dev(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("div.article.fulltext-view")[0]
        assert a, a
        self.article = a

    def title(self) -> str | None:
        t = self.root.select("#page-title")
        if t:
            return t[0].text.strip()
        return super().title()

    def results(self) -> list[Tag]:
        # secs = self.article.select('div.section.results-discussion')
        # if secs:
        #     return secs[0]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2 and hasattr(h2, "string") and h2.string:
                txt = h2.string.lower()
                if txt == "results":
                    return [sec]
                if txt == "results and discussion":
                    return [sec]

        return []

    def methods(self) -> list[Tag]:
        # secs = self.article.select('div.section.methods')
        # if not secs:
        #     secs = self.article.select('div.section.materials-methods')
        # if secs:
        #     return secs[0]
        for sec in self.article.select("div.section"):
            f = sec.find("h2")
            if not f or not f.text:
                continue
            if f.text.lower() == "materials and methods":
                return [sec]
        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select("div.section.abstract")
        return [secs[0]] if secs else []

    def tostr(self, seclist) -> list[str]:
        for sec in seclist:
            for a in sec.select("p a.xref-ref"):
                a.replace_with("CITATION")

            for a in sec.select("div.fig"):
                a.replace_with(self.newfig(a, caption=".fig-caption p"))

        def p(tag):
            return tag.name == "p" or (tag.name == "div" and "fig" in tag["class"])

        # txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.find_all(p)]
        return txt


def download_dev(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://dev.biologists.org"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("div.article.fulltext-view")
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateDev(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return Dev(soup)


def gen_dev(issn: str) -> None:
    e = GenerateDev(issn)
    e.run()


def html_dev(issn: str) -> None:
    e = GenerateDev(issn)
    print(e.tohtml())


if __name__ == "__main__":
    download_dev(issn="0950-1991", sleep=120.0, mx=0)
    download_dev(issn="1477-9129", sleep=120.0, mx=0)
    # gen_dev(issn='0950-1991')
    # html_dev(issn='0950-1991')
