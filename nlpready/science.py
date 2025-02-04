from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate
from ._mlabc import Paper
from ._mlabc import XRef

if TYPE_CHECKING:
    from typing import Iterator
    from bs4 import BeautifulSoup, Tag
    from ._mlabc import Response


ISSN = {"1095-9203": "Science", "0036-8075": "Science"}


class Science(Clean):
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
            if h2 and h2.text and h2.text.lower() == "results":
                return [sec]

        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select("div.section.methods")
        if secs:
            return [secs[0]]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2 and h2.text and h2.text.lower() == "methods":
                return [sec]

        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select("div.section.abstract")
        return [secs[0]] if secs else []

    def full_text(self) -> list[Tag]:

        paper = [
            t
            for t in self.article.contents
            if isinstance(t, Tag) and t.name in {"p", "figure"}
        ]
        if not paper:
            for sec in self.article.select(".section"):
                if "abstract" not in sec["class"]:
                    return [sec]
        node = self.root.new_tag("div")
        for n in paper:
            node.append(n)
        return [node]

    def title(self) -> str | None:
        s = self.root.select("h1.article__headline")
        if s:
            return s[0].text.strip()
        return super().title()

    def xrefs(self) -> list[XRef]:
        def xref(s: Tag) -> Iterator[XRef]:
            for c in s.select("li div[data-doi]"):
                cite = c.find("cite")
                if not isinstance(cite, Tag):
                    continue
                title = cite.select(".cit-article-title")
                stitle = title[0].text if title else None
                yield XRef(doi=c.attrs["data-doi"], title=stitle)

        for s in self.article.select("div.section"):
            if "ref-list" in s.attrs["class"]:
                return list(xref(s))

        for s in self.article.select("div.section"):

            ss = s.find("h2")
            if not ss or not hasattr(ss, "string") or not ss.string:
                continue

            txt = str(ss.string.lower())
            if txt.find("references") >= 0:
                return list(xref(s))
        return []

    def old_tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("div.fig.pos-float"):
                a.replace_with(self.newfig(a, caption=".fig-caption p"))

            for a in sec.select("div.table.pos-float"):
                a.replace_with(
                    self.newtable(a, caption=".table-caption p"),
                )  # XXXX check me!!!!
            for a in sec.select("p a.xref-bibr"):
                a.replace_with(" CITATION ")
            for a in sec.select("p a.xref-fig"):
                a.replace_with(" FIG-REF ")
        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.select("p")]
        return txt

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("figure"):
                a.replace_with(self.newfig(a))

            for a in sec.select("p a.xref-bibr"):
                a.replace_with(" CITATION ")
            for a in sec.select("p a.xref-fig"):
                a.replace_with(" FIG-REF ")
        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.select("p")]
        return txt


def download_science(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://science.sciencemag.org"

        def get_response(self, paper: Paper, header: dict[str, str]) -> Response:
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
            assert a, (a, resp.url, paper.doi)
            return None

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


class GenerateScience(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return Science(soup)


def gen_science(issn):

    e = GenerateScience(issn)
    e.run()


def html_science(issn):

    e = GenerateScience(issn)
    print(e.tohtml())


if __name__ == "__main__":
    download_science(issn="1095-9203", sleep=60.0 * 2, mx=0)
    # gen_science(issn='1095-9203')
    # html_science(issn='1095-9203')
