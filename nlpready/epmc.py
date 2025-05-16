from __future__ import annotations

import csv
import gzip
import os
from typing import TYPE_CHECKING

import click
from requests import Session

from ._mlabc import Clean
from ._mlabc import Generate
from ._mlabc import read_suba_papers_csv


if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup

ISSN = {"epmc": "epmc"}


XML = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"  # noqa: E221
)


def epmc(pmcid: str, session: Session | None = None) -> bytes | None:
    """Given a PUBMED id return the Europmc XML as bytes."""
    url = XML.format(pmcid=pmcid)
    if session is None:
        session = Session()
    resp = session.get(url)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.content


class EPMC(Clean):

    def title(self) -> str | None:

        titles = self.root.select(
            "article > front > article-meta > title-group > article-title",
        )
        if not titles:
            return None
        return " ".join([t.get_text(" ", strip=True) for t in titles])

    def abstract(self) -> list[Tag]:
        abstracts = self.root.select("article > front > article-meta > abstract")
        return list(abstracts)

    def methods(self) -> list[Tag]:
        for sec in self.root.select("article > body > sec > title"):
            if sec.string and "method" in sec.string.lower():
                return [sec]
        return []

    def results(self) -> list[Tag]:
        for sec in self.root.select("article > body > sec > title"):
            if sec.string and "result" in sec.string.lower():
                return [sec]
        return []

    def tostr(self, seclist: list[Tag]) -> list[str]:
        return [sec.get_text(" ", strip=True) for sec in seclist]


# PMC ids at ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/ see https://www.ncbi.nlm.nih.gov/pmc/pmctopmid/


def pmc_subset(fname: str) -> None:
    """Create a PMCID subset from PMC-ids.csv.gz."""
    pmids = {p.pmid for p in read_suba_papers_csv()}
    with open(fname, "w", encoding="utf-8") as out:
        W = csv.writer(out)
        W.writerow(["pmid", "pmcid"])
        with gzip.open("PMC-ids.csv.gz", "rt") as fp:
            R = csv.reader(fp)
            next(R)  # skip header
            for row in R:
                pmcid, pmid = row[8:10]
                if pmcid and pmid in pmids:
                    W.writerow([pmid, pmcid])


def getpmcids(
    pmids: set[str],
    fname: str = "PMC-ids-partial.csv",
) -> dict[str, str]:
    """Map pubmed ids to the "open access" fulltext PMC ids."""
    ret: dict[str, str] = {}
    pmids = set(pmids)
    if os.path.exists(fname):
        with open(fname) as fp:
            R = csv.reader(fp)
            next(R)
            for pmid, pmcid in R:
                ret[pmid] = pmcid

        return ret

    if not os.path.exists("PMC-ids.csv.gz"):
        raise RuntimeError(
            "please download PMC-ids.csv.gz (~85MB) file with:"
            ' "wget ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz"',
        )
    with gzip.open("PMC-ids.csv.gz", "rt") as fp:
        R = csv.reader(fp)
        next(R)  # skip header
        for row in R:
            pmcid, pmid = row[8:10]
            if pmcid and pmid in pmids:
                assert pmid not in ret, pmid
                ret[pmid] = pmcid

    return ret


class GenerateEPMC(Generate):
    parser = "lxml-xml"

    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        return EPMC(soup)


def gen_epmc(issn: str = "epmc") -> None:
    o = GenerateEPMC(issn)
    o.run()


def html_epmc(issn: str = "epmc") -> None:

    e = GenerateEPMC(issn)
    print(e.tohtml())


@click.group()
def cli():
    pass


@cli.command()
@click.option("--fname", help="output filename", default="PMC-ids-partial.csv")
def subset(fname: str):
    """Generate subset of PMC-ids.csv.gz."""
    if not os.path.exists("PMC-ids.csv.gz"):
        raise RuntimeError(
            "please download PMC-ids.csv.gz (~85MB) file with:"
            ' "wget ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz"',
        )
    pmc_subset(fname)


if __name__ == "__main__":
    cli()
