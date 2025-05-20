from __future__ import annotations

import csv
import os
import tomllib
from dataclasses import dataclass
from typing import Iterator

from . import config as Config
from .types import Paper


def read_papers_csv(csvfile: str) -> Iterator[Paper]:
    if not os.path.isfile(csvfile):
        raise ValueError(f'"{csvfile}" is not a file!')
    with open(csvfile, encoding="utf8") as fp:
        R = csv.reader(fp)
        r = next(R)  # skip header pylint: disable=stop-iteration-return
        if tuple(r) != ("pmid", "issn", "name", "year", "doi", "pmcid", "title"):
            raise ValueError(f'"{csvfile}" is not a papers file!')
        # print(header)
        for row in R:
            pmid, issn, journal, year, doi, pmcid, title = row
            if not issn or issn == "missing-issn":
                # click.secho("missing %s" % pmid, fg='yellow')
                continue
            yield Paper(
                doi=doi,
                pmid=pmid,
                year=int(year),
                issn=issn,
                journal=journal or None,
                pmcid=pmcid or None,
                title=title or None,
            )


def read_pubmed_csv(csvfile: str, header: bool = True, pcol: int = 0) -> Iterator[str]:
    """File csvfile is a list of *all* pubmed IDs."""
    with open(csvfile, encoding="utf8") as fp:
        R = csv.reader(fp)
        if header:
            next(R)  # skip header # pylint: disable=stop-iteration-return
        # print(header)
        for row in R:
            yield row[pcol]


@dataclass(kw_only=True)
class UserConfig:
    suba_csv: str
    data_dir: str
    name: str
    email: str | None = None
    api_key: str | None = None


_CONF = None


def getconfig() -> UserConfig:

    global _CONF
    if _CONF is not None:
        return _CONF
    default = dict(
        suba_csv=Config.JCSV,
        data_dir=Config.DATADIR,
        name=Config.NAME,
    )
    if not os.path.exists("config.toml"):
        _CONF = UserConfig(**default)
    else:
        with open("config.toml", "rb") as fp:
            _CONF = UserConfig(**{**default, **tomllib.load(fp)})
    return _CONF


def data_dir() -> str:
    return getconfig().data_dir
