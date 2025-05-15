from __future__ import annotations

import csv
import gzip
import os
import time
from os.path import join
from typing import TYPE_CHECKING

import click
import requests
from requests import Session

from .._mlabc import Clean
from .._mlabc import Config
from .._mlabc import Generate
from .._mlabc import read_suba_papers_csv
from .._mlabc import readxml


if TYPE_CHECKING:
    from bs4 import Tag, BeautifulSoup

ISSN = {"epmc": "epmc"}


XML = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"  # noqa: E221
)


def epmc(pmcid: str, session: Session | None = None) -> str | None:
    """Given a PUBMED id return the Europmc XML as text."""
    url = XML.format(pmcid=pmcid)
    if session is None:
        session = Session()
    resp = session.get(url)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    txt = resp.text

    # ipt = BytesIO(resp.content)
    # t = etree.parse(ipt)
    # txt = etree.tostring(t, pretty_print=True, encoding='unicode')
    return txt


def ensure_dir(d: str) -> None:
    td = join(Config.DATADIR, d)
    if not os.path.isdir(td):
        os.makedirs(td, exist_ok=True)


def download_epmc(issn: str = "epmc", sleep: float = 0.5, mx: int = 0) -> None:
    """Download any EuroPMC XML files using pubmed IDs."""
    failed = set(readxml("failed_epmc"))
    done = set(readxml("xml_epmc"))
    session = requests.Session()

    # pmids = set()
    pm2pmc = {}
    for p in read_suba_papers_csv():
        pmid = p.pmid
        if not pmid:
            continue
        if pmid in failed or pmid in done:
            continue
        if not p.pmcid:
            continue

        # pmids.add(pmid)
        pm2pmc[p.pmid] = p.pmcid

    print("%d failed, %d done, %d todo" % (len(failed), len(done), len(pm2pmc)))
    if not pm2pmc:
        return

    if os.environ.get("PMCIDS") == "1":
        p2mc = getpmcids(set(pm2pmc))

        if p2mc != pm2pmc:
            print(set(p2mc) - set(pm2pmc))
            print(set(pm2pmc) - set(p2mc))

            assert p2mc == pm2pmc, (p2mc, pm2pmc)

    for pmid in pm2pmc:

        pmcid = pm2pmc[pmid]

        xml = epmc(pmcid, session=session)
        if xml is None:
            d = "failed_epmc"
            xml = "failed404"
            failed.add(pmid)
            txt = "failed404"
        else:
            d = "xml_epmc"
            txt = "ok"
            done.add(pmid)

        ensure_dir(d)
        with open(join(Config.DATADIR, d, f"{pmid}.xml"), "w") as fp:
            fp.write(xml)

        print("%d failed (%s %s), %d done" % (len(failed), txt, pmcid, len(done)))
        time.sleep(sleep)


# TRANS = 'translate(text(),"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")'

EXREFS = {"xref"}

EITALIC = {"i"}


def para2txt3(e):
    for t in e.xpath(".//text()"):
        p = t.getparent()
        if p.tag in EXREFS:
            if p.tail == t:
                yield p.tail
            else:
                yield "CITATION"  # '[%s]' % p.attrib['rid']
        elif p.tag in EITALIC and p.tail != t:
            # yield '<i>%s</i>' % t
            yield str(t)
        else:
            yield str(t)


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
    # download_epmc(sleep=2.0)
    # gen_epmc()
    # pmc_subset()
    # html_epmc(issn='epmc')
