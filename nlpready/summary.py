from __future__ import annotations

import csv
import glob
import os
from collections import Counter
from collections import defaultdict
from os.path import join
from typing import Iterator
from typing import TYPE_CHECKING

import click
import requests
from tabulate import tabulate  # type: ignore

from .mlabc import Config
from .mlabc import read_issn
from .mlabc import read_suba_papers_csv
from .mlabc import USER_AGENT

if TYPE_CHECKING:
    from .mlabc import Paper


def _glob(d, g):
    return join(Config.DATADIR, d, g)


def get_dir(xmld: str, ext: str = ".xml") -> list[str]:
    res = []
    for f in glob.glob(_glob(f"{xmld}", f"*{ext}")):
        _, fname = os.path.split(f)
        pmid, _ = os.path.splitext(fname)
        res.append(pmid)
    return res


def getext(xmld: str) -> str:
    if xmld.endswith(("epmc", "elsevier")):
        return ".xml"
    return ".html"


def get_all_done() -> Iterator[tuple[str, str]]:
    for xmld in glob.glob(join(Config.DATADIR, "xml_*")):
        _, issn = xmld.split("_")
        pmids = get_dir(xmld, ext=getext(xmld))
        for pmid in pmids:
            yield issn, pmid


def get_done() -> dict[str, list[str]]:
    res = defaultdict(list)
    for issn, pmid in get_all_done():
        res[pmid].append(issn)
    return res


def _summary(showall: bool = True, exclude: set[str] | None = None) -> None:
    issns = defaultdict(list)
    for p in read_suba_papers_csv():
        if p.doi:
            issns[p.issn].append(p)

    dd = {}
    for xmld in glob.glob(join(Config.DATADIR, "xml_*")):
        _, issn = xmld.split("_")
        if exclude and issn in exclude:
            continue
        if issn in issns:
            cnt, name = len(issns[issn]), issns[issn][0].name
        else:
            cnt, name = 0, issn
        pmids = get_dir(xmld, ext=getext(xmld))
        dd[issn] = (name, issn, cnt, len(pmids), 0)

    for xmld in glob.glob(join(Config.DATADIR, "failed_*")):
        _, issn = xmld.split("_")
        if exclude and issn in exclude:
            continue
        pmids = get_dir(xmld, ext=getext(xmld))
        name, issn, cnt, n, _ = dd[issn]
        dd[issn] = (name, issn, cnt, n, len(pmids))

    if showall:
        for issn in issns:
            if exclude and issn in exclude:
                continue
            if issn not in dd:
                cnt, name = len(issns[issn]), issns[issn][0].name
                dd[issn] = (name, issn, cnt, 0, 0)

    header = "issn,count,done,failed,total,todo,tname".split(",")
    tbl = []
    tcnt = tdone = tfailed = 0
    for name, issn, cnt, done, failed in dd.values():
        tbl.append(
            (issn, cnt, done, failed, done + failed, cnt - (done + failed), name),
        )
        tdone += done
        tfailed += failed
        tcnt += cnt
    tbl = sorted(tbl, key=lambda t: -t[5])
    tbl.append(("total", tcnt, tdone, tfailed, tdone + tfailed, "", ""))  # type: ignore
    print(tabulate(tbl, headers=header, tablefmt="rst"))


def _counts() -> None:
    ISSN = read_issn()
    papers = {p.pmid for p in read_suba_papers_csv() if p.doi}  # papers with doi
    res = get_done()

    total = sum(len(res[pmid]) for pmid in res)
    doubles = sum(1 if len(res[pmid]) > 1 else 0 for pmid in res)
    print(
        "pubmeds done:",
        len(res),
        "possible",
        len(papers),
        "total",
        total,
        "doubles",
        doubles,
    )

    def d(issn):
        if issn in ISSN:
            return ISSN[issn][1]
        return issn

    for pmid in res:
        issns = res[pmid]
        if len(issns) > 1:
            print(pmid, ",".join(sorted([d(j) for j in issns])))


def get_papers_todo(
    exclude: set[str] | None = None,
    failed: bool = False,
) -> dict[str, Paper]:
    # issns = read_issn()
    papers = {p.pmid: p for p in read_suba_papers_csv() if p.doi}  # papers with doi

    for xmld in glob.glob(join(Config.DATADIR, "xml_*")):
        _, issn = xmld.split("_")
        if exclude and issn in exclude:
            continue
        # cnt, name = issns.get(issn, (0, issn))
        pmids = get_dir(xmld, ext=getext(xmld))
        for pmid in pmids:
            if pmid in papers:
                del papers[pmid]
    if failed:
        for xmld in glob.glob(join(Config.DATADIR, "failed_*")):
            _, issn = xmld.split("_")
            if exclude and issn in exclude:
                continue
            if issn in {"epmc", "elsevier"}:  # elseiver failed has all pubmeds!
                continue
            pmids = get_dir(xmld, ext=getext(xmld))
            for pmid in pmids:
                if pmid in papers:
                    del papers[pmid]
    return papers


def _todo(
    byname: bool = False,
    exclude: set[str] | None = None,
    failed: bool = False,
) -> None:
    papers = get_papers_todo(exclude=exclude, failed=failed)
    issns = {p.issn: p.name for p in papers.values()}

    ISSN = Counter[str]()
    for _, p in papers.items():
        ISSN[p.issn] += 1

    tbl: list[tuple[str, str, int]]
    if byname:
        d1 = Counter[str]()
        d2 = defaultdict(list)
        header = ["Journal", "ISSNs", "ToDo"]
        for issn, cnt in ISSN.items():
            j = issns[issn]
            d1[j] += cnt
            d2[j].append(issn)
        tbl = []
        total = 0
        for j in d1:
            issn = ",".join(d2[j])
            cnt = d1[j]
            tbl.append((j, issn, cnt))
            total += cnt
        tbl = sorted(tbl, key=lambda t: -t[2])
        tbl.append(("total", "", total))
        print(tabulate(tbl, headers=header, tablefmt="rst"))
    else:
        header = ["ISSN", "Journal", "ToDo"]
        tbl = []
        total = 0
        for issn, cnt in reversed(sorted(ISSN.items(), key=lambda t: t[1])):
            tbl.append((issn, issns[issn], cnt))
            total += cnt
        tbl.append(("total", "", total))
        print(tabulate(tbl, headers=header, tablefmt="rst"))


def _urls(exclude: set[str] | None = None, failed: bool = False) -> None:

    papers = get_papers_todo(exclude=exclude, failed=failed)
    issns = {p.issn: p.name for p in papers.values()}
    header = {"User-Agent": USER_AGENT, "Referer": "http://www.google.com"}

    print("todo", len(papers))
    fname = "paper_urls.csv"

    e = os.path.exists(fname)
    redo = []
    if e:
        with open(fname, encoding="utf8") as fp:
            R = csv.reader(fp)
            next(R)  # skip header
            for row in R:
                pmid = row[0]
                if pmid in papers:
                    del papers[pmid]
                    redo.append(row)

    papersl = sorted(papers.values(), key=lambda p: (p.name, p.issn, -p.year))
    print("%d to scrape" % len(papers))
    with open(fname, "w", encoding="utf8") as fp:
        W = csv.writer(fp)
        W.writerow(["PubMed", "ISSN", "Journal", "url"])
        for row in redo:
            W.writerow(row)
        for idx, p in enumerate(papersl):
            try:
                resp = requests.get(f"https://doi.org/{p.doi}", headers=header)
                url = resp.url
            except Exception as e:  # pylint: disable=broad-except
                click.secho(f"failed {p} err={str(e)}", fg="red")
                url = "Failed! %s" % p.doi
            W.writerow([p.pmid, p.issn, issns[p.issn], url])
            if (idx + 1) % 10 == 0:
                print("done ", idx + 1)


def parsed() -> None:
    ISSN: dict[str, str] = {}
    res = defaultdict(list)
    for xmld in glob.glob(os.path.join(Config.DATADIR, "cleaned_*")):
        _, issn = xmld.split("_")
        for f in glob.glob(os.path.join(Config.DATADIR, xmld, "*.txt")):
            _, fname = os.path.split(f)
            pmid, _ = os.path.splitext(fname)
            pmid, _ = pmid.split("_")
            res[pmid].append(issn)
            # res[issn] = [pmid for fname in get_dir(xmld, ext='.txt')
            #              for pmid in [fname.split('_')[0]]]

    print("done:", len(res))
    for pmid in res:
        issns = res[pmid]
        if len(issns) > 1:
            print(pmid, ",".join(sorted(ISSN.get(j, j) for j in issns)))


@click.group()
def cli():
    pass


@cli.command()
@click.option("--showall", is_flag=True, help="also show journals not done yet")
@click.option("--exclude", help="comma separated list of ISSN to exclude")
def summary(showall: bool, exclude: str | None = None):
    """Show a summary as a CSV."""
    _summary(showall, exclude=set(exclude.split(",")) if exclude else None)


@cli.command()
def counts():
    """Count journals."""
    _counts()


@cli.command()
def cleaned():
    """Show stats on cleaned data."""
    parsed()


@cli.command()
@click.option("--failed", is_flag=True, help="include failed documents")
@click.option("--exclude", help="comma separated list of ISSN to exclude")
def urls(exclude: str | None = None, failed: bool = False):
    """Generate a CSV (to stdout) of URL of journals."""

    _urls(exclude=set(exclude.split(",")) if exclude else None, failed=failed)


@cli.command()
@click.option("--byname", is_flag=True, help="group table by journal name")
@click.option("--failed", is_flag=True, help="include failed documents")
@click.option("--exclude", help="comma separated list of ISSN to exclude")
def todo(byname: bool, exclude: str | None = None, failed: bool = False):
    """Generate a CSV (to stdout) of Papers remaining to be downloaded."""
    _todo(byname, set(exclude.split(",")) if exclude else None, failed=failed)


if __name__ == "__main__":
    cli()
    # counts()
