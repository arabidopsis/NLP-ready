from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import requests

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate
from ._mlabc import Response

if TYPE_CHECKING:
    from bs4 import BeautifulSoup, Tag
    from ._mlabc import Paper

ISSN = {
    "1059-1524": "Mol. Biol. Cell",
    "1939-4586": "Mol. Biol. Cell",
    "1557-7430": "DNA Cell Biol.",
}


class ASCB(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("div.article__body")[0]
        assert a
        self.article = a

        sections = {"results", "materials and methods"}
        res = {k.lower(): v for k, v in self._full_text()}

        assert set(res) & sections
        self.resultsd = res

    def _full_text(self) -> list[tuple[str, list[Tag]]]:
        target = None
        targets = []
        objs = defaultdict(list)
        a = self.article.select("div.hlFld-Fulltext")[0]

        def has_class(d, cls):
            return d.has_attr("class") and cls in d["class"]

        for d in a.contents:
            if not isinstance(d, Tag):
                continue
            if d.name == "h2":
                target = d.text.strip()
                targets.append(target)
            elif (
                d.name == "p"
                or d.name == "figure"
                or has_class(d, "article-table-content")
            ):
                if target:
                    objs[target].append(d)
        return [(t, objs[t]) for t in targets]

    def results(self) -> list[Tag]:
        return self.resultsd.get("results") or []

    def methods(self) -> list[Tag]:
        return self.resultsd.get("materials and methods") or []

    def abstract(self) -> list[Tag]:
        s = self.article.select("div.abstractSection.abstractInFull")
        if s:
            v = s[0]
            return v.select("p") or [v]
        return []

    def full_text(self) -> list[Tag]:
        return [tag for _, lt in self._full_text() for tag in lt]

    def title(self) -> str | None:
        s = self.root.select("h1.citation__title")
        if s:
            return s[0].text.strip()
        return super().title()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        def has_class(d, cls):
            return d.has_attr("class") and cls in d["class"]

        ss = []
        for sec in seclist:
            for section in sec:
                if not isinstance(section, Tag):
                    continue
                for a in section.select("a.tab-link"):
                    a.replace_with("CITATION")

                if section.name == "figure":
                    ss.append(self.newfig(section))
                elif has_class(section, "article-table-content"):
                    ss.append(self.newtable(section, caption="caption"))
                else:
                    for s in section.select("figure"):
                        s.replace_with(self.newfig(s))
                    ss.append(section)

        txt = [self.SPACE.sub(" ", p.text) for p in ss]
        return txt


def download_ascb(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "https://www.molbiolcell.org"

        def get_response(self, paper: Paper, header: dict[str, str]) -> Response:
            if paper.issn == "1557-7430":
                return requests.get(
                    f"https://www.liebertpub.com/doi/full/{paper.doi}",
                    headers=header,
                )
            return super().get_response(paper, header)

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            a = soup.select("div.article__body div.abstractSection.abstractInFull")
            assert a, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateASCB(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return ASCB(soup)


def gen_ascb(issn: str) -> None:

    e = GenerateASCB(issn)
    e.run()


def html_ascb(issn: str) -> None:

    e = GenerateASCB(issn)
    print(e.tohtml())


if __name__ == "__main__":
    download_ascb(issn="1059-1524", sleep=120.0, mx=0)
    download_ascb(issn="1939-4586", sleep=120.0, mx=0)
    # html_ascb(issn='1059-1524')
