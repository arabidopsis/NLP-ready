from __future__ import annotations

import csv
import os
import re
import time
from io import BytesIO
from itertools import batched
from pathlib import Path
from typing import Iterator
from typing import Sequence
from typing import TYPE_CHECKING

import click
import requests
from lxml import etree
from tqdm import tqdm

from .types import NCBIPaper
from .types import Paper
from .utils import read_papers_csv
from .utils import read_pubmed_csv

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
    for diva in tree.findall("PubmedArticle"):
        article = diva.find("MedlineCitation/Article")
        if article is None:
            continue
        t = diva.findtext("MedlineCitation/PMID")
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

        data = diva.find("PubmedData")
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


class Runner:
    def __init__(
        self,
        papers_csv: str | Path,
        done_csv: str | Path,
        batch_size: int = 1,
        sleep=0.0,
    ):
        self.done_csv = Path(done_csv)
        self.papers_csv = Path(papers_csv)
        self.batch_size = batch_size
        self.sleep = sleep

    def start(self) -> None:
        pass

    def end(self) -> None:
        pass

    def run(self, nb: bool = False):
        from .issn import DATA

        if nb:
            from tqdm.notebook import tqdm
        else:
            from tqdm import tqdm

        if self.done_csv.exists():
            with self.done_csv.open("r", encoding="utf8") as fp:
                R = csv.reader(fp)
                done = {row[0] for row in R}
        else:
            done = set()

        todo = [
            paper
            for paper in read_papers_csv(self.papers_csv)
            if paper.pmid not in done
            and paper.doi
            and paper.issn
            and paper.issn in DATA
        ]
        self.start()
        try:
            with self.done_csv.open("a", encoding="utf8") as fp:
                W = csv.writer(fp)
                with tqdm(total=len(todo)) as pbar:
                    for papers in batched(todo, self.batch_size):
                        for paper in papers:
                            status = self.work(paper, pbar)
                            W.writerow([paper.pmid, status])
                            fp.flush()
                        pbar.update(len(papers))
                        if self.sleep:
                            time.sleep(self.sleep)
        finally:
            self.end()

    def work(self, paper: Paper, tqdm: tqdm) -> str:
        return "done"


def get_ncbi_metadata(
    pubmeds_todo: str,
    papers_csv: str,
    *,
    email: str | None = None,
    api_key: str | None = None,
    header: bool = True,
    pcol: int = 0,
    sleep: float = 0.2,
    batch_size: int = 10,
) -> None:
    """Create a CSV of (pmid, issn, name, year, doi, title) from list of pubmed IDs."""
    from tqdm import tqdm

    session = requests.Session()
    exists = os.path.exists(papers_csv)
    if exists:
        with open(papers_csv, encoding="utf8") as fp:
            R = csv.reader(fp)
            next(R)  # skip header
            done = {row[0] for row in R}
    else:
        done = set()

    todo = [
        pmid
        for pmid in read_pubmed_csv(pubmeds_todo, header=header, pcol=pcol)
        if pmid not in done
    ]
    click.secho(f"{len(done)} done. {len(todo)} todo", fg="blue", bold=True)

    with open(papers_csv, "a", encoding="utf8") as fp:
        W = csv.writer(fp)
        if not exists:
            W.writerow(["pmid", "issn", "name", "year", "doi", "pmcid", "title"])
            fp.flush()
        with tqdm(total=len(todo)) as pbar:
            for pmids in batched(todo, batch_size):
                batch = []
                for m in pubmed_meta(pmids, session, email, api_key):
                    pubmed = m.pmid
                    if not pubmed:
                        continue
                    batch.append(pubmed)
                    W.writerow(
                        [
                            pubmed,
                            m.issn or "",
                            m.journal,
                            str(m.year),
                            m.doi or "",
                            m.pmcid or "",
                            m.title or "",
                        ],
                    )
                    fp.flush()  # in case of interrupt.
                    done.add(pubmed)
                pbar.update(len(pmids))
                missing = [p for p in pmids if p not in batch]
                if missing:
                    msg = ",".join(missing)
                    pbar.write(click.style(f"missing: {msg}", fg="red"), bold=True)
                # pbar.secho(f"{len(done)}/{len(todo)} done", fg="green")
                if sleep:
                    time.sleep(sleep)  # be nice :)
