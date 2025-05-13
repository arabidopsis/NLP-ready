from __future__ import annotations

import os
import warnings
from collections import Counter
from collections import namedtuple
from dataclasses import dataclass
from importlib import import_module
from pickle import dump
from pickle import load
from typing import Any

import click

from ._mlabc import Config
from ._mlabc import Generate

# add module name to this list...

MODS = [
    "ascb",
    "aspb",
    "bbb",
    "bioj",
    "bmcpb",
    "cell",  # cell needs chromedriver... run python3 cell.py download
    "dev",
    "elife",
    # "elsevier",
    "emboj",
    "epmc",
    "fpls",
    "gad",
    "genetics",
    "jbc",
    "jcs",
    "jproteome",
    "mcp",
    "mdpi",
    "mpmi",
    "nature",
    "oup",
    "plos",
    "pnas",
    "science",
    "springer",
    "wiley",
]


KEYMAP = {
    "url": 0,
    "mod": 1,
    "issn": 2,
    "done": 3,
    "journal": 4,
    "notok": 5,
    "failed": 6,
}


Journal = namedtuple(
    "Journal",
    ["url", "mod", "issn", "ndone", "journal", "not_ok", "nfailed"],
)

from typing import TypedDict, Callable, cast


class NLPMod(TypedDict):
    issn: dict[str, str]
    download: Callable[[str, float, int], None]
    Generate: type[Generate]


@dataclass(kw_only=True)
class UserConfig:
    email: str | None = None
    api_key: str | None = None


_CONF = None


def getconfig() -> UserConfig:
    import tomllib

    global _CONF
    if _CONF is not None:
        return _CONF

    if not os.path.exists("config.toml"):
        _CONF = UserConfig()
    else:
        with open("config.toml", "rb") as fp:
            _CONF = UserConfig(**tomllib.load(fp))
    return _CONF


def getmod(mod: str) -> NLPMod:
    mod = "." + mod
    m = import_module(mod, "nlpready")
    ret: dict[str, Any] = dict(issn=m.ISSN)
    for name in dir(m):
        a = getattr(m, name)
        if name.startswith("download_"):
            ret["download"] = a
        elif isinstance(a, type) and Generate in a.__bases__:
            a = getattr(m, name)
            ret["Generate"] = a
    return cast(NLPMod, ret)


def issn2mod() -> dict[str, str]:
    is2mod: dict[str, str] = {}
    for mod in MODS:
        m = getmod(mod)
        d = m["issn"]
        for iissn in d:
            is2mod[iissn] = mod
    return is2mod


def doubles() -> None:
    # pylint: disable=import-outside-toplevel
    from ._summary import get_done
    from ._mlabc import read_journals_csv

    pmid2doi = read_journals_csv()
    res = get_done()
    papers = []
    for pmid in res:
        paper = pmid2doi[pmid]
        if not paper.issn:
            continue
        for iissn in res[pmid]:
            d = getmod(iissn)
            g: Generate = d["Generate"](iissn)
            soup = g.get_soup(paper.issn, pmid)
            e = g.create_clean(soup, pmid)
            papers.append((paper, e))


def mod_option(f):
    return click.option(
        "--mod",
        help="comma separated list of modules to run"
        " (use prefix - to exclude) [default: all]",
    )(f)


def issn_option(f):
    return click.option(
        "--issn",
        help="comma separated list of journals (issn) to run [default: all]",
    )(f)


@click.group()
def cli():
    pass


# pylint: disable=redefined-outer-name
@cli.command()
@mod_option
@issn_option
@click.option("--sort", default="journal", help="sort on: " + ",".join(KEYMAP))
@click.option("--num", is_flag=True, help="reduce numbers to NUMBER etc.")
@click.option(
    "--cache",
    default=Config.PKLFILE,
    help="cached pickle file",
    show_default=True,
)
def tohtml(
    cache: str,
    issn: str | None = None,
    mod: str = "",
    num: bool = False,
    sort: str = "journal",
) -> None:
    """Generate HTML documents from downloads."""
    # pylint: disable=too-many-locals
    # pylint: disable=import-outside-toplevel
    from ._mlabc import pmid2doi, make_jinja_env

    # from pickle import load, dump

    env = make_jinja_env()
    jdir = os.path.join(Config.DATADIR, "html", "journals")
    os.makedirs(jdir, exist_ok=True)

    template = env.get_template("index.html")
    if mod:
        mods = [s.strip() for s in mod.split(",")]
    else:
        mods = MODS
    if issn:
        issn_ = {s.strip() for s in issn.split(",")}
    else:
        issn_ = set()
    # journals = []

    total1 = set()
    total2 = set()
    total3 = set()

    p2i = pmid2doi()
    issns = {p.issn: p.journal for p in p2i.values() if not issn_ or p.issn in issn_}
    issnmap = {}

    for mmod in mods:
        d = getmod(mmod)
        for iissn in d["issn"]:
            if iissn not in issns or iissn in FAKE_ISSN:  # no paper from this journal
                continue
            journal = issns.get(iissn, iissn)
            print("writing", mmod, iissn, journal)
            g = d["Generate"](iissn, pmid2doi=p2i)
            # try:
            fname, papers, failed, _ = g.tohtmlx(
                save=True,
                prefix=os.path.join(jdir, mmod + "_"),
                env=env,
                verbose=False,
                num=num,
            )

            not_ok = len([p for p, s in papers if not s.has_all_sections()])
            apmids = [p.pmid for p, s in papers if s.has_all_sections()]
            tpmids = [p.pmid for p, s in papers]
            ndone = len(tpmids)
            i = fname.find("journals/")
            url = fname[i:]
            t = Journal(
                url=url,
                mod=mmod,
                issn=iissn,
                ndone=ndone,
                journal=journal,
                not_ok=not_ok,
                nfailed=len(failed),
            )
            # journals.append(t)
            for p in apmids:
                total1.add(p)
            for p in tpmids:
                total2.add(p)
            for p in tpmids:
                total3.add(p)

            issnmap[iissn] = t

            # except Exception as e:
            #     click.secho("failed %s %s %s" % (m, i, str(e)), fg='magenta')
            #     raise e

    if os.path.exists(cache):
        with open(cache, "rb") as fp:
            issnmap2 = load(fp)
        issnmap2.update(issnmap)  # overwrite
        issnmap = issnmap2

    with open(cache, "wb") as wfp:
        dump(issnmap, wfp)

    journals_ = list(issnmap.values())

    def sortf():
        s = sort
        if sort[0] == "-":
            s = sort[1:]
        k = KEYMAP[s]
        if s == sort:
            return lambda t: t[k]
        return lambda t: -t[k]

    journals_ = sorted(journals_, key=sortf())
    # pylint: disable=no-member
    res = template.render(journals=journals_, name=Config.NAME)

    with open(os.path.join(Config.DATADIR, "html", "index.html"), "w") as fp2:
        fp2.write(res)
    click.secho(
        "found %d pubmeds. %d unique, %d usable"
        % (len(total3), len(total2), len(total1)),
        fg="blue",
    )


# @cli.command()
# @click.option("--mod", help="modules to run")
def tokenize(mod: str = "") -> None:
    # from nltk import word_tokenize, PorterStemmer

    if mod:
        mods = [s.strip() for s in mod.split(",")]
    else:
        mods = MODS
    cc = Counter[str]()
    # porter = PorterStemmer()
    for m in mods:
        d = getmod(m)
        for i in d["issn"]:
            print("tokenizing ", m, i)
            g = d["Generate"](i)
            # print('overwrite', not nowrite)
            for _, p in g.tokenize():
                for w in p.split():
                    while w.startswith(("(", "[")):
                        w = w[1:]
                    while w.endswith((")", ";", ".", ":", ",", "]")):
                        w = w[:-1]
                    # w = porter.stem(w)
                    cc[w] += 1

    for c in cc.most_common():
        print(c)


@cli.command()
@mod_option
@issn_option
@click.option("--nowrite", is_flag=True, help="don't overwrite")
@click.option(
    "--num",
    is_flag=True,
    help="replace numbers with the token NUMBER in the text",
)
def clean(
    num: bool = False,
    issn: str = "",
    mod: str = "",
    nowrite: bool = False,
) -> None:  # pylint: disable=redefined-outer-name
    """Create "clean" documents suitable for input into ML programs."""
    # pylint: disable=import-outside-toplevel
    from ._mlabc import pmid2doi

    if mod:
        mods = [s.strip() for s in mod.split(",")]
    else:
        mods = MODS
    if issn:
        issns = {i.strip() for i in issn.split(",")}
    else:
        issns = None
    p2i = pmid2doi()
    for m in mods:
        d = getmod(m)
        for i in d["issn"]:
            if issns and issn not in issns:
                continue
            print("writing ", m, i)
            g = d["Generate"](i, pmid2doi=p2i)
            # print('overwrite', not nowrite)
            g.run(overwrite=not nowrite, prefix=m, num=num)


@cli.command()
@click.option("--d", help="directory to scan", default=Config.DATADIR)
def cleandirs(d: str) -> None:
    """Remove empty directories."""
    d = d or Config.DATADIR
    for f in os.listdir(d):
        d = os.path.join(d, f)
        if os.path.isdir(d):
            n = len(os.listdir(d))
            if n == 0:
                print("removing", f)
                os.removedirs(d)


@cli.command()
@mod_option
@issn_option
@click.option(
    "--sleep",
    default=10.0,
    help="wait sleep seconds between requests",
    show_default=True,
)
@click.option("--mx", default=3, help="max documents to download 0=all")
def download(mod: str = "", sleep: float = 10.0, mx: int = 1, issn: str = "") -> None:
    """Download html/xml from websites."""
    if mod:
        mods = [s.strip() for s in mod.split(",")]
        exclude = {m[1:] for m in mods if m[0] == "-"}
        mods = [m for m in mods if m[0] != "-"]
        if not mods:
            mods = MODS
    else:
        mods = MODS
        exclude = set()
    if issn:
        issns = {i.strip() for i in issn.split(",")}
    else:
        issns = None
    for m in mods:
        if m in exclude:
            continue
        d = getmod(m)
        for iissn in d["issn"]:
            if issns and iissn not in issns:
                continue
            # print("downloading:", m, iissn)
            func = d["download"]
            func(iissn, sleep=sleep, mx=mx)  # type: ignore


@cli.command()
def summary() -> None:
    """Summary of current download status."""
    # pylint: disable=import-outside-toplevel
    from ._download import journal_summary

    journal_summary()


@cli.command()
@click.option("--email", help="your email address for NCBI E-Utilities")
@click.option("--api-key", help="your NCBI API_KEY")
@click.option(
    "--out",
    default=Config.JCSV,
    help="output filename (will be appended to if exists)",
    show_default=True,
    type=click.Path(dir_okay=False, file_okay=True, exists=False),
)
@click.option(
    "--col",
    default=0,
    help="column in file that contains the pubmed ID",
    show_default=True,
)
@click.option(
    "-b",
    "--batch-size",
    default=10,
    help="batch size to hit NCBI",
    show_default=True,
)
@click.option(
    "--sleep",
    default=1.0,
    help="wait sleep seconds between requests",
    show_default=True,
)
@click.option("--noheader", is_flag=True, help="csvfile has no header")
@click.argument("csvfile", type=click.Path(dir_okay=False, exists=True, file_okay=True))
def journals(
    csvfile: str,
    out: str,
    email: str | None,
    api_key: str | None,
    noheader: bool = False,
    col: int = 0,
    sleep: float = 0.37,
    batch_size: int = 10,
) -> None:
    """Create a CSV of (pmid, issn, name, year, doi, pmcid, title) from list of pubmed IDs."""
    # pylint: disable=import-outside-toplevel
    from ._download import getmeta

    conf = getconfig()

    if not email:
        if conf.email:
            email = conf.email
        else:
            warnings.warn(
                """
Email address is not specified.

To make use of NCBI's E-utilities, NCBI requires you to specify your
email address with each request.

In case of excessive usage of the E-utilities, NCBI will attempt to contact
a user at the email address provided before blocking access to the
E-utilities.""",
                UserWarning,
            )
    api_key = api_key or conf.api_key
    if not api_key and sleep < 0.37:
        warnings.warn(
            """
More than 3 hits per second without an --api-key may get you
blocked from the NCBI site.""",
            UserWarning,
        )
    getmeta(
        csvfile,
        sleep=sleep,
        pubmeds=out,
        header=not noheader,
        pcol=col,
        email=email,
        api_key=api_key,
        batch_size=batch_size,
    )


FAKE_ISSN = {"epmc", "elsevier"}


@cli.command()
def issn() -> None:
    """Print all known ISSN,journals."""
    for m in MODS:
        if m in FAKE_ISSN:
            continue
        mod = getmod(m)
        d = mod["issn"]
        for iissn in d:
            print(f"{iissn},{d[iissn]}")


@cli.command()
def show_modules() -> None:
    """Print all available modules."""
    mx = len(sorted(MODS, key=len, reverse=True)[0])
    for m in sorted(MODS):
        if m in FAKE_ISSN:
            continue
        mod = getmod(m)
        d = mod["issn"]
        space = " " * (mx - len(m))
        print(f"{m}{space} issn[{len(d)}]: {','.join(sorted(d.keys()))}")


if __name__ == "__main__":
    cli()
