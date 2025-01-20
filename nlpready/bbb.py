from __future__ import annotations

from typing import TYPE_CHECKING

import click
import requests

from .mlabc import Clean
from .mlabc import Download
from .mlabc import Generate

if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup
    from .mlabc import Response
    from .mlabc import Paper

ISSN = {
    "0916-8451": "Biosci. Biotechnol. Biochem.",
    "1347-6947": "Biosci. Biotechnol. Biochem.",
    "1559-2324": "Plant Signal Behav",
    "1555-8584": "RNA Biol",
    "0968-7688": "Mol. Membr. Biol.",
}


class BBB(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("article.article")
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
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
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
        secs = self.article.select(".hlFld-Abstract .abstractInFull")
        if not secs:
            secs = self.article.select(".hlFld-Abstract #abstractBox")
        return [secs[0]] if secs else []

    def title(self) -> str | None:
        t = self.root.select(".NLM_article-title.hlFld-title")
        if not t:
            t = self.article.select(".hlFld-title")
        if t:
            return t[0].text.strip()
        print("no title")
        return super().title()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("p span.ref-lnk"):
                a.replace_with(" (CITATION)")

            for a in sec.select("div.figure"):
                a.replace_with(self.newfig(a, caption=".figureInfo p"))

            for a in sec.select("div.tableView"):
                a.replace_with(self.newtable(a, caption=".tableCaption p"))

            for a in sec.select("div.hidden"):
                a.decompose()

        return super().tostr(seclist)


class GenerateBBB(Generate):
    def create_clean(self, soup, pmid: str) -> Clean:
        return BBB(soup)


def gen_bbb(issn):

    g = GenerateBBB(issn)
    g.run()


def download_bbb(issn: str, sleep: float = 5.0, mx: int = 0):
    class D(Download):
        Referer = "https://www.tandfonline.com"

        def get_response(self, paper, header):
            resp = requests.get(f"http://doi.org/{paper.doi}", headers=header)
            if resp.url.find("/doi/full/") < 0:
                url = resp.url.replace("/doi/abs/", "/doi/full/")
                print("redirect", url)
                header["Referer"] = resp.url
                resp = requests.get(url, headers=header)
            return resp

        def check_soup(
            self,
            paper: Paper,
            soup: BeautifulSoup,
            resp: Response,
        ) -> None | bytes:
            a = soup.select("article.article div.hlFld-Fulltext")
            if resp.url.find("/doi/full/") < 0:
                click.secho(f"no full text {paper.pmid} {resp.url}", fg="red")
                return b"no full text"
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_bbb(issn: str) -> None:

    g = GenerateBBB(issn)
    print(g.tohtml())


if __name__ == "__main__":
    # download_bbb(issn='0916-8451', sleep=120., mx=0)
    # download_bbb(issn='1347-6947', sleep=120., mx=0)
    # download_bbb(issn='1559-2324', sleep=10., mx=2)
    pass
