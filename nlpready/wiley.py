from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import dump
from ._mlabc import Generate


if TYPE_CHECKING:

    from bs4 import BeautifulSoup, Tag

# generated from downloads.py:wiley_issn()
# only gives online version for Plant J. !!!!
ISSN = {
    # '1460-2075': 'EMBO J.',  # see emboj!
    "1399-3054": "Physiol Plant",
    "1365-313X": "Plant J.",
    "1600-0854": "Traffic",
    "0960-7412": "Plant J.",  # added by hand
    "1467-7652": "Plant Biotechnol. J.",
    "1469-8137": "New Phytol.",
    # '1469-3178': 'EMBO Rep.',
    "1873-3468": "FEBS Lett.",
    "0014-5793": "FEBS Lett.",
    # '1567-1364': 'FEMS Yeast Res.',
    "1522-2683": "Electrophoresis",
    "1744-7909": "J Integr Plant Biol",
    "1742-4658": "FEBS J.",
    "1742-464X": "FEBS J.",
    # '1744-4292': 'Mol. Syst. Biol.',
    # '1364-3703': 'Mol. Plant Pathol.',
    # '1365-2591': 'Int Endod J',
    "1615-9861": "Proteomics",
    "1615-9853": "Proteomics",
    "1365-3040": "Plant Cell Environ.",
    "0140-7791": "Plant Cell Environ.",
    # added
    "0028-646X": "New Phytol.",
    "0173-0835": "Electrophoresis",
    "0730-2312": "J. Cell. Biochem.",
    "0886-1544": "Cell Motil. Cytoskeleton",
    "1065-6995": "Cell Biol. Int.",
    "1356-9597": "Genes Cells",
    "1364-3703": "Mol. Plant Pathol.",
    "1365-2591": "Int Endod J",
    "1526-954X": "Genesis",
    "1438-8677": "Plant Biol (Stuttg)",
    "1435-8603": "Plant Biol (Stuttg)",
    "1462-5822": "Cell. Microbiol.",
}


# pylint: disable=abstract-method
class BaseWiley(Clean):
    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("figure"):
                # figure inside a div.Para so can't really replace
                # with a "p"
                a.replace_with(self.newfig(a))

            for a in sec.select(".article-table-content"):
                a.replace_with(self.newtable(a, caption=".article-table-caption"))
            # for a in sec.select('figure'):
            #    p = self.root.new_tag('p')
            #    p.string = '[[FIGURE]]'
            #     a.replace_with(p)
            for a in sec.select('p a[title="Link to bibliographic citation"]'):
                a.replace_with("CITATION")
            for a in sec.select("p a.bibLink"):
                a.replace_with("CITATION")

        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.select("p")]
        return txt


class Wiley(BaseWiley):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("article.journal article.issue article.article")[0]
        assert a, a
        self.article = a

    def title(self) -> str | None:
        for s in self.article.select("h1.article-header__title"):
            return s.text.strip()
        return super().title()

    def results(self) -> list[Tag]:
        for sec in self.article.select("section.article-body-section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt.endswith(
                    ("results", "results and discussion", "significance of the study"),
                ):
                    return [sec]

        return []

    def methods(self) -> list[Tag]:
        for sec in self.article.select("section.article-body-section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt.endswith(
                    (
                        "experimental procedures",
                        "materials and methods",
                        "methods",
                        "material and methods",
                    ),
                ):  # spelling!
                    return [sec]

        return []

    def abstract(self) -> list[Tag]:
        for s in self.article.select("section.article-section--abstract"):
            if s.attrs["id"] == "abstract":
                return [s]
        return []


class Wiley2(BaseWiley):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("article div.article__body article")
        assert a, a
        self.article = a[0]

    def results(self) -> list[Tag]:
        for sec in self.article.select(
            ".article-section.article-section__full div.article-section__content",
        ):
            h2 = sec.find("h2")
            if h2 and h2.text.lower().strip().endswith("results and discussion"):
                return [sec]
        for sec in self.article.select("div.article-section__content"):
            h2 = sec.find("h2")
            if h2 and h2.text.lower().strip().endswith("results"):
                return [sec]
        return []

    def methods(self) -> list[Tag]:
        for sec in self.article.select("section.article-body-section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt.endswith(
                    (
                        "experimental procedures",
                        "materials and methods",
                        "methods",
                        "material and methods",
                    ),
                ):  # spelling!
                    return [sec]

        for sec in self.article.select("div.article-section__content"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt.endswith(
                    (
                        "experimental procedures",
                        "materials and methods",
                        "methods",
                        "material and methods",
                    ),
                ):  # spelling!
                    return [sec]

        return []

    def abstract(self) -> list[Tag]:
        for s in self.article.select("section.article-section__abstract"):
            return [s]
        return []

    def title(self) -> str | None:
        s = self.root.select(".article-citation .citation__title")
        if s:
            return s[0].text.strip()
        return super().title()


class GenerateWiley(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        # p = self.pmid2doi[pmid]
        # if p.issn in {'1873-3468'}:
        #     return Wiley(soup)
        e: Clean
        try:
            e = Wiley(soup)
        except Exception:  # pylint: disable=broad-except
            e = Wiley2(soup)
        return e


def gen_wiley(issn: str) -> None:
    e = GenerateWiley(issn)
    e.run()


def download_wiley(issn: str, sleep: float = 5.0, mx: int = 0) -> None:
    class D(Download):
        Referer = "http://onlinelibrary.wiley.com"

        def get_response(self, paper, header):
            url = f"http://onlinelibrary.wiley.com/doi/{paper.doi}/full"
            resp = requests.get(url, headers=header)
            return resp

        def check_soup(self, paper, soup, resp):
            a = soup.select("article.journal article.issue article.article")
            if not a:
                a = soup.select("article div.article__body article")
            # print(soup.select('article'))
            if not a:
                dump(paper, resp.content)
                return b"failed! no article body"

            assert a and len(a) == 1, (paper.pmid, resp.url, paper.doi, len(a))
            return None

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


def html_wiley(issn: str) -> None:

    e = GenerateWiley(issn)
    print(e.tohtml())


def download_all(sleep: float = 10.0, mx: int = 5) -> None:
    for issn in ISSN:
        download_wiley(issn=issn, sleep=sleep, mx=mx)


if __name__ == "__main__":
    # download_wiley(issn='0960-7412', sleep=20., mx=50)
    # download_wiley(issn='1467-7652', sleep=10., mx=5)
    # download_wiley(issn='1365-313X', sleep=10., mx=20)
    # download_wiley(issn='1873-3468', sleep=10., mx=20)
    # download_wiley(issn='1469-8137', sleep=60. * 2, mx=0)
    # download_wiley(issn='1742-4658', sleep=60. * 2, mx=0)
    # download_wiley(issn='1615-9861', sleep=60. * 2, mx=0)
    download_wiley(issn="1744-7909", sleep=60.0 * 2, mx=0)
    # download_all(sleep=60. * 2, mx = 0)

    # gen_wiley(issn='0960-7412')
    # gen_wiley(issn='1467-7652')
    # gen_wiley(issn='1365-313X')
    # gen_wiley(issn='1873-3468')
    # html_wiley(issn='1615-9861')
