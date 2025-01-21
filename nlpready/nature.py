from __future__ import annotations

from typing import TYPE_CHECKING

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate


if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup
    from ._mlabc import Response, Paper

ISSN = {
    "1476-4687": "Nature",
    "0028-0836": "Nature",
    "1748-7838": "Cell Res.",
    "1001-0602": "Cell Res.",
    "1465-7392": "Nat. Cell Biol.",
    "1476-4679": "Nat. Cell Biol.",
    "1087-0156": "Nat. Biotechnol.",
    "1350-9047": "Cell Death Differ.",
    "2041-1723": "Nat Commun",
    "2045-2322": "Sci Rep",
}


class Nature(Clean):

    def results(self) -> list[Tag]:
        for sec in self.root.select(
            "article div.c-article-body > div > section[data-title]",
        ):
            if (
                "data-title" in sec.attrs
                and sec.attrs["data-title"].lower() == "discussion"
            ):
                return [sec]
        return []

    def methods(self) -> list[Tag]:
        for sec in self.root.select(
            "article div.c-article-body > div > section[data-title]",
        ):
            if (
                "data-title" in sec.attrs
                and sec.attrs["data-title"].lower() == "methods"
            ):
                return [sec]
        return []

    def abstract(self):
        return list(self.root.select('article section[data-title="Abstract"] p'))

    def title(self) -> str | None:
        title = self.root.select("article [data-article-title]")
        if not title:
            return None
        return title[0].get_text(" ", strip=True)


class GenerateNature(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return Nature(soup)


def gen_nature(issn: str) -> None:

    nature = GenerateNature(issn)
    nature.run()


def download_nature(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "https://www.nature.com"

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> bytes | None:
            x = list(soup.select('article section[data-title="Abstract"] p'))
            if not x:
                return b"can't find abstract!"
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_nature(issn: str) -> None:

    nature = GenerateNature(issn)
    print(nature.tohtml())


if __name__ == "__main__":
    download_nature(issn="1476-4687", sleep=10.0, mx=1)
    download_nature(issn="0028-0836", sleep=10.0, mx=1)
