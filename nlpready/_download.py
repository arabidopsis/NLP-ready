from __future__ import annotations

import csv
import os
import re
import time
from collections import defaultdict
from glob import glob
from io import BytesIO
from itertools import batched
from typing import Any
from typing import Iterator
from typing import Sequence
from typing import TYPE_CHECKING

import click
import requests
from bs4 import BeautifulSoup
from lxml import etree

from ._mlabc import read_pubmed_csv
from ._mlabc import read_suba_papers_csv
from ._types import NCBIPaper

if TYPE_CHECKING:
    from requests import Session

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# html that is sent back by NIH
ERROR = re.compile("<ERROR>([^<]*)</ERROR>")


def fetchpubmed(
    session: Session,
    pmid: str | Sequence[str],
    email: str | None = None,
    api_key: str | None = None,
) -> bytes | None:
    """Fetch article metadata from NCBI using pubmed id."""
    params = dict(db="pubmed", retmode="xml")
    if email is not None:
        params["email"] = email
    if api_key is not None:
        params["api_key"] = api_key
    if isinstance(pmid, str):
        pmid = [pmid]

    params["id"] = ",".join(pmid)
    resp = session.get(EFETCH, params=params)
    return resp.content  # need buffer for parsing


def parse_xml(xml: bytes) -> Iterator[NCBIPaper]:
    """Parse NCBI Journal metadata into a dictionary."""
    ipt = BytesIO(xml)
    tree = etree.parse(ipt)
    error = tree.getroot().tag
    if error == "ERROR":  # no id
        return None
    for a in tree.findall("PubmedArticle"):
        article = a.find("MedlineCitation/Article")
        if article is None:
            continue
        t = a.findtext("MedlineCitation/PMID")
        if not t:
            continue
        pmid: str = t.strip()
        title: str | None = article.findtext("ArticleTitle")
        abstract = article.findtext("Abstract/AbstractText")
        authors = article.findall("AuthorList/Author")
        pages = article.findtext("Pagination/MedlinePgn")
        journal = article.find("Journal")
        if journal is not None:

            name = journal.findtext("ISOAbbreviation", None) or journal.findtext(
                "Title",
                "",
            )
            volume = journal.findtext("JournalIssue/Volume")
            issue = journal.findtext("JournalIssue/Issue")
            yearx = journal.findtext("JournalIssue/PubDate/Year")
            yearx = yearx or journal.findtext("JournalIssue/PubDate/MedlineDate")
            if yearx:
                yearx = yearx.strip()[:4]

                year = int(yearx)

            issn = journal.findtext("ISSN")
            issn = issn.strip() if issn else None
        else:
            name = volume = issue = issn = None
            year = -1

        data = article.find("PubmedData")
        if data is not None:
            ids = data.findall("ArticleIdList/ArticleId")
            if ids:
                doil = [
                    i.text.strip() for i in ids if i.get("IdType") == "doi" and i.text
                ]
                doi: str | None
                if doil:
                    doi = doil[0]
                else:
                    doi = None
                pmcidl = [
                    i.text.strip() for i in ids if i.get("IdType") == "pmc" and i.text
                ]
                if pmcidl:
                    pmcid = pmcidl[0]
                else:
                    pmcid = None
            else:
                doi = pmcid = None
        else:
            doi = pmcid = None

        # elementtree tries to encode everything as ascii
        # or if that fails it leaves the string alone
        # alist = [(a.findtext('LastName'), a.findtext('ForeName'), a.findtext('Initials'))
        #          for a in authors]
        alist = [
            (a.findtext("ForeName"), a.findtext("Initials"), a.findtext("LastName"))
            for a in authors
        ]
        yield NCBIPaper(
            pmid=pmid,
            year=year,
            title=title,
            abstract=abstract,
            authors=alist,
            journal=name,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi or "",
            issn=issn,
            pmcid=pmcid,
        )

    # return data from xml file at NIH in a pythonic dictionary


def pubmed_meta(
    pmids: Sequence[str],
    session: Session | None,
    email: str | None = None,
    api_key: str | None = None,
) -> Iterator[NCBIPaper]:
    if session is None:
        session = requests.Session()
    xml = fetchpubmed(session, pmids, email=email, api_key=api_key)
    if xml is None:
        return
    yield from parse_xml(xml)


def getmeta(
    csvfile: str,
    pubmeds: str,
    email: str | None = None,
    api_key: str | None = None,
    header: bool = True,
    pcol: int = 0,
    sleep: float = 0.2,
    batch_size: int = 10,
) -> None:
    """Create a CSV of (pmid, issn, name, year, doi, title) from list of pubmed IDs."""

    session = requests.Session()
    e = os.path.exists(pubmeds)
    if e:
        with open(pubmeds, encoding="utf8") as fp:
            R = csv.reader(fp)
            next(R)  # skip header
            done = {row[0] for row in R}
    else:
        done = set()

    todo = [
        pmid
        for pmid in read_pubmed_csv(csvfile, header=header, pcol=pcol)
        if pmid not in done
    ]
    click.secho(f"{len(done)} done. {len(todo)} todo", fg="blue")

    with open(pubmeds, "a", encoding="utf8") as fp:
        W = csv.writer(fp)
        if not e:
            W.writerow(["pmid", "issn", "name", "year", "doi", "pmcid", "title"])
            fp.flush()
        for pmids in batched(todo, batch_size):
            d = []
            for m in pubmed_meta(pmids, session, email, api_key):
                pubmed = m.pmid
                if not pubmed:
                    continue
                d.append(pubmed)
                W.writerow(
                    [
                        pubmed,
                        m.issn or "",
                        m.journal,
                        str(m.year),
                        m.doi or "",
                        m.pmcid or "",
                        m.title,
                    ],
                )
                fp.flush()  # in case of interrupt.
                done.add(pubmed)
            for p in pmids:
                if p not in d:
                    click.secho(f"missing {p}", fg="red")
            click.secho(f"{len(done)} done", fg="green")
            if sleep:
                time.sleep(sleep)  # be nice :)


def journal_summary() -> None:
    """Summarize journal statistics."""
    # pylint: disable=import-outside-toplevel
    from ._cli import issn2mod

    d = defaultdict(list)
    for p in read_suba_papers_csv():
        if p.doi:
            d[(p.issn, p.journal)].append(p.doi)
    header = [["ISSN", "mod", "count", "journal", "doi prefix", "example doi"]]
    ret = []
    i2mod = issn2mod()
    for k in d:
        (issn, name) = k
        if not issn:
            continue
        prefix = os.path.commonprefix(d[k])
        ret.append(
            (issn, i2mod.get(issn, "missing!"), len(d[k]), name, prefix, d[k][-1]),
        )

    ret = sorted(ret, key=lambda t: (-t[2], t[3]))
    # ret = sorted(ret, key=lambda t: t[2])
    for r in header + ret:
        print(",".join(str(x) for x in r))


HREF = re.compile(r"^/journal/.*/\(ISSN\)(.{4}-.{4})$")


def fetch_issn(href: str, session: Session | None = None) -> str | None:
    if session is None:
        session = Session()

    resp = session.get("http://onlinelibrary.wiley.com" + href)
    soup = BeautifulSoup(BytesIO(resp.content), "lxml")
    issn = soup.select("#issn")
    if not issn:
        return None
    return issn[0].text.strip()


def wiley_journals(
    start=0,
    session: Session | None = None,
) -> tuple[int, list[tuple[str, str]]]:
    if session is None:
        session = Session()

    resp = session.get(
        "http://onlinelibrary.wiley.com/browse/publications",
        params=dict(type="journal", start=start),
    )
    soup = BeautifulSoup(BytesIO(resp.content), "html.parser")
    journals = soup.select("#publications li div.details a")
    ret = []
    for j in journals:
        href = j.attrs["href"]
        name = j.text.strip()
        m = HREF.match(href)
        if m:
            issn = m.group(1)
            ret.append((issn, name))
        else:
            issn = fetch_issn(href, session)
            if issn:
                ret.append((issn, name))
    return len(journals), ret


def get_wiley() -> dict[str, Any]:
    start = 0
    res = {}
    session = requests.Session()
    while True:
        n, journals = wiley_journals(start=start, session=session)
        print("found", n, "at ", start)

        if not journals:
            break
        start += n
        for issn, name in journals:
            res[issn] = name

    with open("wiley_journals.csv", "w") as fp:
        W = csv.writer(fp)
        W.writerow(["name", "issn"])
        for issn, name in sorted(res.items(), key=lambda t: t[1]):
            W.writerow([name, issn])
    return res


def get_all_cleaned() -> Iterator[tuple[str, str]]:

    for folder in glob("cleaned_*"):
        for f in glob(f"{folder}/*_cleaned.txt"):
            _, fname = os.path.split(f)
            fname, _ = os.path.splitext(fname)
            pmid, _ = fname.split("_")
            yield folder, pmid


def wiley_issn() -> None:

    with open("wiley_journals.csv") as fp:
        R = csv.reader(fp)
        next(R)
        i2n = {issn: name for name, issn in R}
    ISSN = {}
    print("pmid,issn,journal,year,doi")
    for p in read_suba_papers_csv():
        if p.issn in i2n:
            ISSN[p.issn] = p.journal
            print(",".join((p.pmid, p.issn, p.journal or "", str(p.year), p.doi)))
    print(ISSN)
