# import csv
from __future__ import annotations

import os
import time
from io import StringIO
from os.path import join
from typing import TYPE_CHECKING

import click
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from .mlabc import Clean
from .mlabc import Config
from .mlabc import DownloadSelenium
from .mlabc import dump
from .mlabc import Generate
from .mlabc import read_suba_papers_csv
from .mlabc import readxml

if TYPE_CHECKING:
    from bs4 import Tag
    from .mlabc import Paper
    from .mlabc import Response

ISSN = {
    "1097-4172": "Cell",
    "0092-8674": "Cell",
    "1090-2104": "Biochem. Biophys. Res. Commun.",
    "0006-291X": "Biochem. Biophys. Res. Commun.",
    "1873-2690": "Plant Physiol. Biochem.",
    "0981-9428": "Plant Physiol. Biochem.",
    "0960-9822": "Curr. Biol.",
    "1879-0445": "Curr. Biol.",
    "1752-9867": "Mol Plant",
    "1674-2052": "Mol Plant",
    "0378-1119": "Gene",
    "1879-0038": "Gene",
    "1873-3700": "Phytochemistry",
    "0031-9422": "Phytochemistry",
    "1876-7737": "J Proteomics",
    "1873-2259": "Plant Sci.",
    "1089-8638": "J. Mol. Biol.",
    "0022-2836": "J. Mol. Biol.",
    # added
    "0006-3002": "Biochim. Biophys. Acta",
    "0171-9335": "Eur. J. Cell Biol.",
    "1047-8477": "J. Struct. Biol.",
    "1095-8657": "J. Struct. Biol.",
    "1095-9998": "Food Microbiol.",
    "1097-4164": "Mol. Cell",
    "1360-1385": "Trends Plant Sci.",
    "1522-4724": "Mol. Cell Biol. Res. Commun.",
    "1618-1328": "J. Plant Physiol.",
    "0176-1617": "J. Plant Physiol.",
    "1872-8278": "Mitochondrion",
    "1873-3778": "J Chromatogr A",
    # added
    "1096-0309": "Anal. Biochem.",
    "0003-9861": "Arch. Biochem. Biophys.",
    "0006-3495": "Biophys. J.",
    "1934-6069": "Cell Host Microbe",
    "1095-564X": "Dev. Biol.",
    "1534-5807": "Dev. Cell",
    "1090-2422": "Exp. Cell Res.",
    "1097-2765": "Mol. Cell",
    "1046-5928": "Protein Expr. Purif.",
    "0042-6822": "Virology",
    "1096-0341": "Virology",
    "1673-8527": "J Genet Genomics",
    "0308-8146": "Food Chem",
    "0300-9084": "Biochimie",
    "0891-5849": "Free Radic. Biol. Med.",
}


class DownloadCell(DownloadSelenium):
    def wait(self):

        w = super().wait()
        w.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "article div.Body section,div.fullText section"),
            ),
        )
        return w

    def check_soup(
        self,
        paper: Paper,
        soup: BeautifulSoup,
        resp: Response,
    ) -> bytes | None:
        secs = soup.select("article div.Body section")
        if not secs:
            secs = soup.select("div.fullText section")
        if not secs:
            s = soup.select("h1.Head .title-text")
            if s:
                txt = s[0].text
                if "WITHDRAWN" in txt:
                    return b"withdrawn"
        if len(secs) <= 3:
            dump(paper, resp.content)
        assert len(secs) > 3, (paper.pmid, paper.doi, secs)
        return None


def download_cell(
    issn: str,
    sleep: float = 5.0,
    mx: int = 0,
    headless: bool = True,
    close: bool = True,
    driver=None,
) -> None:
    downloader = DownloadCell(
        issn,
        sleep=sleep,
        mx=mx,
        headless=headless,
        close=close,
        driver=driver,
    )

    downloader.run()


def getpage(doi: str, driver: WebDriver) -> str:

    driver.get(f"http://doi.org/{doi}")

    h = driver.find_element(by=By.TAG_NAME, value="html")
    txt = h.get_attribute("outerHTML")
    soup = BeautifulSoup(StringIO(txt), "lxml")
    secs = soup.select("article div.Body section")
    if not secs:
        secs = soup.select("div.fullText section")
    assert len(secs) > 3, (doi, secs)

    return txt or ""


def old_download_cell(
    issn: str,
    sleep: float = 5.0,
    mx: int = 0,
    headless: bool = True,
    close: bool = True,
):
    # pylint: disable=import-outside-toplevel
    from selenium import webdriver

    # header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    #           ' (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
    #           'Referer': 'http://www.sciencedirect.com'
    #           }
    fdir = f"failed_{issn}"
    gdir = f"xml_{issn}"
    target = join(Config.DATADIR, fdir)
    if not os.path.isdir(target):
        os.mkdir(target)
    target = join(Config.DATADIR, gdir)
    if not os.path.isdir(target):
        os.mkdir(target)
    failed = set(readxml(fdir))
    done = set(readxml(gdir))

    ISSNS = {issn}
    allpmid = failed | done
    todo = {
        p.pmid: p
        for p in read_suba_papers_csv()
        if p.doi and p.issn in ISSNS and p.pmid not in allpmid
    }

    print("%s: %d failed, %d done, %d todo" % (issn, len(failed), len(done), len(todo)))
    lst = sorted(todo.items(), key=lambda t: t[0])
    if mx > 0:
        lst = lst[:mx]
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("headless")
    # https://blog.miguelgrinberg.com/post/using-headless-chrome-with-selenium
    driver = webdriver.Chrome(options=options)
    for idx, (pmid, p) in enumerate(lst):
        print(pmid, p.doi)
        xml = getpage(p.doi, driver)
        d = gdir
        done.add(pmid)

        with open(join(Config.DATADIR, d, f"{pmid}.html"), "w") as fp:
            fp.write(xml)

        del todo[pmid]
        print(
            "%d failed, %d done, %d todo: %s"
            % (len(failed), len(done), len(todo), pmid),
        )
        if sleep > 0 and idx < len(lst) - 1:
            time.sleep(sleep)
    if close:
        driver.close()
        return None
    return driver


class CELL(Clean):
    def __init__(self, root: BeautifulSoup):
        super().__init__(root)
        a = root.select("article")
        assert a, a
        self.article = a[0]

    def results(self) -> list[Tag]:

        secs = self.article.select("div.Body section")
        for sec in secs:
            if self.find_title(
                sec,
                op=lambda h2, b: h2.endswith(b),
                txt=["results", "results and discussion", "results and discussions"],
            ):
                return [sec]
            if self.find_title(sec, txt=["experimental"]):
                return [sec]
        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select("div.Body section")
        for sec in secs:
            if self.find_title(
                sec,
                op=lambda h2, b: h2.endswith(b),
                txt=[
                    "experimental procedures",
                    "materials and methods",
                    "material and methods",
                    "methods",
                ],
            ):
                return [sec]

        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select(".Abstracts")
        return [secs[0]] if secs else []

    def title(self) -> str | None:
        t = self.article.select(".Head .title-text")
        if t:
            return t[0].text.strip()
        return super().title()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("p a.workspace-trigger"):
                if a.attrs["name"].startswith("bbib"):
                    a.replace_with("CITATION")

            for a in sec.select("figure"):
                a.replace_with(self.newfig(a, caption=".captions p"))
            for a in sec.select(".tables"):
                a.replace_with(self.newtable(a, caption=".captions p"))
        txt = [self.SPACE.sub(" ", p.text) for sec in seclist for p in sec.select("p")]
        return txt


class CELL2(Clean):
    def __init__(self, root: BeautifulSoup) -> None:
        super().__init__(root)
        a = root.select("div.fullText")

        a0 = a[0]
        assert a0, a0
        self.article = a0

    def results(self) -> list[Tag]:
        secs = self.article.select("section")
        for sec in secs:
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return [sec]
        return []

    def methods(self) -> list[Tag]:
        secs = self.article.select("section")
        for sec in secs:
            if sec.has_attr("class"):
                if "materials-methods" in sec["class"]:
                    return [sec]
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower()
                if txt in {"experimental procedures", "materials and methods"}:
                    return [sec]
        return []

    def abstract(self) -> list[Tag]:
        secs = self.article.select("section.abstract")
        for sec in secs:
            return [sec]
        return []

    def title(self) -> str | None:
        for t in self.root.select("h1.articleTitle"):
            txt = t.text.strip()
            if txt:
                return txt
        return super().title()

    def tostr(self, seclist: list[Tag]) -> list[str]:
        for sec in seclist:
            for a in sec.select("p span.bibRef"):
                a.replace_with("CITATION")
            for a in sec.select("div.floatDisplay"):
                a.replace_with(self.newfig(a, caption=".caption p"))

        return super().tostr(seclist)


class GenerateCell(Generate):
    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        e: Clean
        try:
            e = CELL(soup)
        except Exception:  # pylint: disable=broad-except
            e = CELL2(soup)
        return e


def gen_cell(issn: str) -> None:
    e = GenerateCell(issn)
    e.run()


def html_cell(issn: str) -> None:
    e = GenerateCell(issn)
    print(e.tohtml())


def cmds():
    # pylint: disable=unused-variable
    @click.group()
    def cli():
        pass

    DEFAULT = ",".join(ISSN)

    @cli.command()
    @click.option(
        "--sleep",
        default=10.0,
        help="wait sleep seconds between requests",
        show_default=True,
    )
    @click.option("--mx", default=1, help="max documents to download 0=all")
    @click.option(
        "--head",
        default=False,
        is_flag=True,
        help="don't run browser headless",
    )
    @click.option(
        "--noclose",
        default=False,
        is_flag=True,
        help="don't close browser at end",
    )
    @click.option(
        "--issn",
        default=DEFAULT,
        show_default=True,
        help="only download these journals",
    )
    def download(sleep, mx, issn, head, noclose):
        """Download XML for CELL Journals."""
        # pylint: disable=import-outside-toplevel
        from selenium import webdriver

        options = webdriver.ChromeOptions()
        if not head:
            options.add_argument("headless")
        driver = webdriver.Chrome(chrome_options=options)
        for i in issn.split(","):
            download_cell(
                issn=i,
                sleep=sleep,
                mx=mx,
                headless=not head,
                close=False,
                driver=driver,
            )
        if noclose:
            # pylint: disable=import-outside-toplevel
            import code

            code.interact(local=locals())
        else:
            driver.close()

    # @cli.command()
    # @click.option("--issn", default=DEFAULT, show_default=True)
    # def clean(issn):
    #     for i in issn.split(","):
    #         gen_cell(issn=i)

    # @cli.command()
    # @click.option("--issn", default=DEFAULT, show_default=True)
    # def html(issn):
    #     for i in issn.split(","):
    #         html_cell(issn=i)

    # @cli.command()
    # def issn():
    #     print(" ".join(ISSN))

    # @cli.command()
    # @click.option("--issn", default=DEFAULT, show_default=True)
    # def failed(issn):
    #     for iissn in issn.split(","):
    #         gdir = f"failed_{iissn}"
    #         for pmid in readxml(gdir):
    #             fname = Config.DATADIR + gdir + f"/{pmid}.html"
    #             with open(fname, "rb") as fp:
    #                 err = fp.read().decode("utf-8")
    #                 print(f'{iissn},{pmid},"{err}",{fname}')

    return cli


if __name__ == "__main__":
    cmds()()

    # download_cell(issn='1097-4172', sleep=120., mx=0, headless=False)
    # download_cell(issn='0092-8674', sleep=120., mx=0, headless=False)
    # download_cell(issn='1873-2690', sleep=120., mx=0, headless=False)
    # download_cell(issn='0981-9428', sleep=120., mx=0, headless=False)
    # gen_cell(issn='1097-4172')
