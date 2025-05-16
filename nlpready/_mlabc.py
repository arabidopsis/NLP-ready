from __future__ import annotations

import csv
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from os.path import join
from typing import Any
from typing import cast
from typing import Iterator
from typing import Literal
from typing import TYPE_CHECKING
from typing import TypedDict

import click
import requests
from bs4 import BeautifulSoup
from requests import ConnectionError as RequestConnectionError
from requests import Response as RequestResponse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ._rescantxt import find_primers
from ._rescantxt import reduce_nums
from ._types import Paper
from ._utils import data_dir
from ._utils import getconfig

if TYPE_CHECKING:
    from jinja2 import Environment
    from bs4 import Tag
    from selenium.webdriver.remote.webdriver import WebDriver


# Simple fake requests Response Object
@dataclass
class SeleniumResponse:
    content: bytes
    url: str
    status_code: int = 200
    encoding: str = "UTF-8"

    def raise_for_status(self) -> None:
        pass

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding)

    @property
    def ok(self) -> bool:
        return True

    def close(self):
        pass


Response = RequestResponse | SeleniumResponse


class XRef(TypedDict):
    doi: str
    title: str | None


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
)


def ok(doi: str, issn: str) -> bool:
    return True


def pmid2doi(check=ok) -> dict[str, Paper]:
    return {p.pmid: p for p in read_suba_papers_csv() if check(p.doi, p.issn)}


def read_journals_csv() -> dict[str, Paper]:
    return pmid2doi()


def read_suba_papers_csv() -> Iterator[Paper]:
    """suba_papers.csv is a list of *all* pubmed IDs."""
    conf = getconfig()
    return readx_suba_papers_csv(conf.suba_csv)


def readx_suba_papers_csv(csvfile: str) -> Iterator[Paper]:
    if not os.path.isfile(csvfile):
        click.secho(f"No such file: {csvfile}!", fg="red", bold="True", err=True)
        return
    with open(csvfile, encoding="utf8") as fp:
        R = csv.reader(fp)
        next(R)  # skip header pylint: disable=stop-iteration-return
        # print(header)
        for row in R:
            if len(row) == 5:
                pmid, issn, journal, year, doi = row
                title = pmcid = None
            else:
                pmid, issn, journal, year, doi, pmcid, title = row
                if issn == "missing-issn":
                    # click.secho("missing %s" % pmid, fg='yellow')
                    continue
            yield Paper(
                doi=doi,
                year=int(year),
                issn=issn,
                journal=journal,
                pmid=pmid,
                pmcid=pmcid,
                title=title,
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


def read_issn() -> dict[str, tuple[int, str]]:

    ISSN: defaultdict[str, list[Paper]] = defaultdict(list[Paper])
    for p in read_suba_papers_csv():
        if p.issn:
            ISSN[p.issn].append(p)
    return {
        k: (len(v), v[0].journal) for k, v in ISSN.items() if v[0].journal is not None
    }

    # ISSN = {}
    # with open('jcounts.csv', 'r') as fp:
    #     R = csv.reader(fp)
    #     next(R)
    #     for issn, count, name, _, _ in R:
    #         ISSN[p.issn] = (int(count), p.journal)
    # return ISSN


def readxml(d: str) -> Iterator[str]:
    """Scan directory d and return the pubmed ids."""
    dd = join(data_dir(), d)
    if not os.path.isdir(dd):
        return
    for f in os.listdir(dd):
        f, ext = os.path.splitext(f)
        if ext in {".html", ".xml"}:
            yield f


def dump(paper: Paper, xml: bytes) -> None:
    with open(f"dump_{paper.pmid}.html", "wb") as fp:
        fp.write(xml)


_Plug = object()


class Clean:
    SPACE: re.Pattern = re.compile(r"\s+", re.I)
    FIGURE: str = "[[FIGURE: %s]]"
    TABLE: str = "[[TABLE: %s]]"
    a: object | list[Tag] = _Plug
    m: object | list[Tag] = _Plug
    r: object | list[Tag] = _Plug
    t: object | str | None = _Plug
    f: object | list[Tag] = _Plug
    x = _Plug

    def __init__(self, root: BeautifulSoup) -> None:
        self.root = root

    def find_title(
        self,
        sec: Tag,
        h: str = "h2",
        op=lambda h, b: h == b,
        txt: list[str] | None = None,
    ) -> bool:
        if txt is None:
            txt = []
        hs = sec.find(h)
        if hs and hs.text:
            # pylint: disable=no-member
            h2 = hs.text.lower().strip()
            h2 = self.SPACE.sub(" ", h2)
            for a in txt:
                # print('"%s"="%s" %s %s' % (h2, a, op(h2, a), h2.endswith(a)))
                if op(h2, a):
                    return True
        return False

    def title(self) -> str | None:
        t = self.root.find("title")
        if t and t.text:
            return t.text.strip()
        return None

    def abstract(self) -> list[Tag]:
        raise NotImplementedError()

    def results(self) -> list[Tag]:
        raise NotImplementedError()

    def methods(self) -> list[Tag]:
        raise NotImplementedError()

    def xrefs(self) -> list[XRef]:
        # pylint: disable=no-self-use
        return []

    def full_text(self) -> list[Tag]:
        # pylint: disable=no-self-use
        return []

    def tostr(self, seclist: list[Tag]) -> list[str]:

        txt = [
            self.SPACE.sub(" ", p.get_text(" ", strip=True))
            for sec in seclist
            for p in sec.select("p")
        ]
        return txt

    def tostr2(self, sec: list[Tag]) -> list[str]:
        def to_p(s: Tag) -> None:
            a = self.root.new_tag("p")
            a.string = s.text
            s.replace_with(a)

        for s in sec:
            for p in s.select("h2,h3,h4"):
                to_p(p)

        return self.tostr(sec)

    def s_abstract(self) -> list[Tag]:
        if self.a is not _Plug:
            return cast(list[Tag], self.a)
        self.a = self.abstract()
        return self.a

    def s_methods(self) -> list[Tag]:
        if self.m is not _Plug:
            return cast(list[Tag], self.m)
        self.m = self.methods()
        return self.m

    def s_results(self) -> list[Tag]:
        if self.r is not _Plug:
            return cast(list[Tag], self.r)
        self.r = self.results()
        return self.r

    def s_full_text(self) -> list[Tag]:
        if self.f is not _Plug:
            return cast(list[Tag], self.f)
        self.f = self.full_text()  # pylint: disable=assignment-from-none
        return self.f

    def s_title(self) -> str | None:
        if self.t is not _Plug:
            return cast(str | None, self.t)
        self.t = self.title()
        return self.t

    def s_xrefs(self) -> list[XRef]:
        if self.x is not _Plug:
            return cast(list[XRef], self.x)
        self.x = self.xrefs()  # pylint: disable=assignment-from-none
        return self.x

    def has_all_sections(self):
        a = self.s_abstract()
        m = self.s_methods()
        r = self.s_results()
        return a and m and r

    def has_rmm(self):
        m = self.s_methods()
        r = self.s_results()
        return m or r

    def missing(self):
        a = self.s_abstract()
        m = self.s_methods()
        r = self.s_results()
        ret = []
        if not a:
            ret.append("a")
        if not m:
            ret.append("m")
        if not r:
            ret.append("r")
        return " ".join(ret) if ret else ""

    def _newfig(
        self,
        tag: Tag,
        fmt: str,
        caption: str = "figcaption p",
        node: str = "p",
    ) -> Tag:
        captions = [c.get_text(" ", strip=True) for c in tag.select(caption)]
        txt = " ".join(captions)
        new_tag = self.root.new_tag(node)
        new_tag.string = fmt % txt
        return new_tag

    def newfig(self, tag: Tag, caption: str = "figcaption p", node: str = "p") -> Tag:
        return self._newfig(tag, self.FIGURE, caption=caption, node=node)

    def newtable(self, tag: Tag, caption: str = "figcaption p", node: str = "p") -> Tag:
        return self._newfig(tag, self.TABLE, caption=caption, node=node)


def make_jinja_env() -> Environment:
    # pylint: disable=import-outside-toplevel
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["prime"] = find_primers
    return env


class Generate:
    parser = "lxml"
    need_all = False

    def __init__(
        self,
        issn: str,
        onlynewer: bool = False,
        pmid2doi: (
            dict[str, Paper] | None
        ) = None,  # pylint: disable=redefined-outer-name
        journal: str | None = None,
        partial: bool = False,
        **kwargs: Any,
    ):
        self.issn = issn
        self._pmid2doi = pmid2doi
        self._journal = journal
        self._onlynewer = onlynewer
        self.partial = partial

    @property
    def pmid2doi(self) -> dict[str, Paper]:
        if self._pmid2doi:
            return self._pmid2doi

        def check(doi, issn):
            if self.issn in {"epmc", "elsevier"}:
                return True
            return doi and issn == self.issn

        self._pmid2doi = pmid2doi(check)
        return self._pmid2doi

    @property
    def journal(self) -> str:
        if self._journal:
            return self._journal
        if self.issn in {"epmc", "elsevier"}:
            self._journal = self.issn
        else:
            d = {p.issn: p.journal for p in self.pmid2doi.values() if p.journal}
            # d = read_issn()
            if self.issn in d:
                # self._journal = d[self.issn][1]
                self._journal = d[self.issn]
            else:
                self._journal = self.issn
        return self._journal

    def create_clean(self, soup: BeautifulSoup, pmid: str) -> Clean:
        raise NotImplementedError()

    def ensure_dir(self) -> str:
        dname = join(data_dir(), "cleaned")
        if not os.path.isdir(dname):
            os.mkdir(dname)
        name = self.journal.replace(".", "").lower()
        name = "-".join(name.split())
        dname = join(dname, f"cleaned_{self.issn}_{name}")
        if not os.path.isdir(dname):
            os.mkdir(dname)
        return dname

    def get_xml_name(self, gdir: str, pmid: str) -> str:
        # pylint: disable=no-self-use
        fname = join(data_dir(), gdir, f"{pmid}.html")
        if not os.path.isfile(fname):
            fname = join(data_dir(), gdir, f"{pmid}.xml")
        return fname

    def get_soup(self, gdir: str, pmid: str) -> BeautifulSoup:
        fname = self.get_xml_name(gdir, pmid)
        with open(fname, "rb") as fp:
            soup = BeautifulSoup(fp, self.parser)
        return soup

    def run(
        self,
        overwrite: bool = True,
        prefix: str | None = None,
        num: bool = False,
    ) -> None:
        gdir = "xml_%s" % self.issn
        papers = readxml(gdir)
        if not papers:
            return

        dname = self.ensure_dir()

        written = False

        for pmid in papers:
            ok = self.generate_pmid(
                gdir,
                pmid,
                overwrite=overwrite,
                prefix=prefix,
                num=num,
            )
            written = written or ok

        if not written:
            click.secho("no data for %s" % self.issn, fg="red", file=sys.stderr)
            try:
                os.rmdir(dname)
            except OSError:
                pass

    def tokenize(self) -> Iterator[tuple[Literal["m", "a", "r"], str]]:
        gdir = "xml_%s" % self.issn
        for pmid in readxml(gdir):
            soup = self.get_soup(gdir, pmid)
            e = self.create_clean(soup, pmid)
            a = e.abstract()
            m = e.methods()
            r = e.results()
            if a:
                for p in e.tostr(a):
                    yield "a", reduce_nums(p)
            if m:
                for p in e.tostr(m):
                    yield "m", reduce_nums(p)
            if r:
                for p in e.tostr(r):
                    yield "r", reduce_nums(p)

    def clean_name(self, pmid: str) -> str:
        dname = self.ensure_dir()
        fname = join(dname, f"{pmid}_cleaned.txt")
        return fname

    def generate_pmid(
        self,
        gdir: str,
        pmid: str,
        overwrite: bool = True,
        prefix: str | None = None,
        num: bool = False,
    ) -> bool:
        fname = self.clean_name(pmid)
        exists = os.path.exists(fname)
        if exists and not overwrite:
            return True
        if exists and self._onlynewer:
            xname = self.get_xml_name(gdir, pmid)
            if os.path.exists(xname):
                tgt = os.stat(fname).st_mtime
                src = os.stat(xname).st_mtime
                if tgt >= src:  # target newer that surc
                    return True

        soup = self.get_soup(gdir, pmid)
        e = self.create_clean(soup, pmid)

        a = e.abstract()
        m = e.methods()
        r = e.results()
        ft = e.full_text() if (not m and not r) else None

        if self.need_all:
            if not a or not m or not r:
                click.secho(
                    "{}: missing: abs {}, methods {}, results {} doi={}".format(
                        pmid,
                        a is None or a == [],
                        m is None or m == [],
                        r is None or r == [],
                        self.pmid2doi[pmid].doi,
                    ),
                    fg="red",
                )
                return False

        if exists:
            click.secho("overwriting %s" % fname, fg="yellow")
        else:
            click.secho("generating %s" % fname, fg="magenta")

        def con(seclist: list[Tag]) -> str:
            if num:
                return " ".join(reduce_nums(a) for a in e.tostr(seclist))
            return " ".join(e.tostr(seclist))

        with open(fname, "w", encoding="utf-8") as fp:
            if a:
                w = con(a)
                print("!~ABS~! %s" % w, file=fp)
            if r:
                w = con(r)
                print("!~RES~! %s" % w, file=fp)
            if m:
                w = con(m)
                print("!~MM~! %s" % w, file=fp)
            if ft and (not r and not m):
                w = con(ft)
                print("!~FT~! %s" % w, file=fp)

        return True

    def tohtmlx(
        self,
        template: str = "template.html",
        save: bool = False,
        prefix: str = "",
        env: Environment | None = None,
        verbose: bool = True,
        num: bool = False,
    ) -> tuple[str, list[tuple[Paper, Clean]], list[Paper], str]:
        if env is None:
            env = make_jinja_env()

        def getfname() -> str:
            if self.issn not in {"epmc", "elsevier"}:
                name = self.journal
            else:
                name = self.issn
            name = name.replace(".", "").lower()
            name = "-".join(name.split())
            fname = prefix + f"{self.issn}-{name}.html"
            return fname

        templatet = env.get_template(template)
        gdir = "xml_%s" % self.issn
        fdir = "failed_%s" % self.issn
        papers = []

        # only look for pmids that we want.
        pmid2doif = self.pmid2doi
        todo = [pmid2doif[pmid] for pmid in readxml(gdir) if pmid in pmid2doif]
        failed = [pmid2doif[pmid] for pmid in readxml(fdir) if pmid in pmid2doif]

        todo = sorted(todo, key=lambda p: -p.year)
        failed = sorted(failed, key=lambda p: -p.year)
        # nart = len(todo)
        fname = getfname()

        for paper in todo:
            if verbose:
                print(paper.pmid, paper.issn, paper.doi)

            soup = self.get_soup(gdir, paper.pmid)
            try:
                e = self.create_clean(soup, paper.pmid)
                missing = e.missing()
                if missing:
                    click.secho(
                        f"missing {missing} for {paper.pmid} http://doi.org/{paper.doi}",
                        fg="magenta",
                        err=True,
                    )
                papers.append((paper, e))
            except Exception as err:
                click.secho(
                    f"failed for {paper.pmid} http://doi.org/{paper.doi} {err}",
                    fg="red",
                    err=True,
                )
                raise err
                # papers.append((paper, Clean(soup)))
        # pylint: disable=no-member
        t: str = templatet.render(
            papers=papers,
            issn=self.issn,
            failed=failed,
            this=self,
            mod=self.__class__.__module__,
            num=num,
        )
        if save:
            with open(fname, "w") as fp:
                fp.write(t)
        return fname, papers, failed, t

    def tohtml(
        self,
        template: str = "template.html",
        save: bool = False,
        prefix: str = "",
        env: Environment | None = None,
        verbose: bool = True,
        num: bool = False,
    ) -> str:
        _, _, _, t = self.tohtmlx(template, save, prefix, env, verbose, num)
        return t


class Download:
    parser = "lxml"
    Referer = "http://google.com"

    def __init__(
        self,
        issn: str,
        mx: int = 0,
        sleep: float = 10.0,
        **kwargs: Any,
    ) -> None:
        self.issn = issn
        self.sleep = sleep
        self.mx = mx

    def ensure_dirs(self) -> None:
        # pylint: disable=no-self-use
        fdir = f"failed_{self.issn}"
        gdir = f"xml_{self.issn}"
        for t in [fdir, gdir]:
            target = join(data_dir(), t)
            if not os.path.isdir(target):
                os.makedirs(target, exist_ok=True)

    def get_response(self, paper: Paper, header: dict[str, str]) -> Response:
        # pylint: disable=no-self-use
        resp = requests.get(f"http://doi.org/{paper.doi}", headers=header)
        return resp

    def check_soup(
        self,
        paper: Paper,
        soup: BeautifulSoup,
        resp: Response,
    ) -> bytes | None:
        raise NotImplementedError()

    def start(self):
        pass

    def end(self):
        pass

    def create_soup(self, paper: Paper, resp: Response) -> BeautifulSoup:
        xml = resp.content
        soup = BeautifulSoup(BytesIO(xml), self.parser)
        return soup

    def save_page(self, xml: bytes, targetd: str, paper: Paper) -> None:
        with open(join(data_dir(), targetd, f"{paper.pmid}.html"), "wb") as fp:
            fp.write(xml)

    def remove_page(self, targetd: str, paper: Paper) -> None:
        try:
            os.unlink(join(data_dir(), targetd, f"{paper.pmid}.html"))
        except FileNotFoundError:
            pass

    def run(self) -> None:
        header = {"User-Agent": USER_AGENT, "Referer": self.Referer}
        # self.ensure_dirs()
        fdir = "failed_%s" % self.issn
        gdir = "xml_%s" % self.issn

        failed = set(readxml(fdir))
        done = set(readxml(gdir))

        allpmid = failed | done
        todo = {
            p.pmid: p
            for p in read_suba_papers_csv()
            if p.doi and p.issn == self.issn and p.pmid not in allpmid
        }
        if len(failed) > 0 or len(done) > 0 or len(todo) > 0:
            print(
                f"{self.issn}: {len(failed)} failed, {len(done)} done, {len(todo)} todo",
            )
        lst = sorted(todo.values(), key=lambda p: -p.year)
        if self.mx > 0:
            lst = lst[: self.mx]
        if not lst:
            return
        self.ensure_dirs()
        self.start()
        for idx, paper in enumerate(lst):
            try:
                resp = self.get_response(paper, header)
                if resp.status_code == 404:
                    xml = b"failed404"
                    failed.add(paper.pmid)
                else:
                    resp.raise_for_status()
                    header["Referer"] = resp.url
                    xml = resp.content
                    self.save_page(xml, gdir, paper)
                    soup = self.create_soup(paper, resp)

                    err = self.check_soup(paper, soup, resp)
                    if err:
                        failed.add(paper.pmid)
                        self.save_page(xml, fdir, paper)
                        self.remove_page(gdir, paper)
                    else:
                        done.add(paper.pmid)

            except (
                RequestConnectionError,
                AssertionError,
                requests.exceptions.HTTPError,
            ) as e:
                xml = str(e).encode("utf-8")
                click.secho(
                    f"failed {paper.pmid} {paper.doi} {str(e)}",
                    fg="red",
                )
                failed.add(paper.pmid)
                self.save_page(xml, fdir, paper)
                self.remove_page(gdir, paper)

            # with open(join(data_dir(), targetd, f"{paper.pmid}.html"), "wb") as fp:
            #     fp.write(xml)

            del todo[paper.pmid]
            print(
                f"{len(failed)} failed, {len(done)} done, {len(todo)} todo: {paper.pmid}",
            )
            if self.sleep > 0 and idx < len(lst) - 1:
                time.sleep(self.sleep)
        self.end()


# pylint: disable=abstract-method
class DownloadSelenium(Download):

    WAIT = 10

    def __init__(
        self,
        issn: str,
        mx: int = 0,
        sleep: float = 10.0,
        headless: bool = False,
        close: bool = True,
        driver: WebDriver | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(issn, mx=mx, sleep=sleep, **kwargs)
        self.headless = headless
        self.close = close
        self.driver = driver
        self.wait_: WebDriverWait | None = None

    def start(self) -> None:
        # pylint: disable=import-outside-toplevel
        if self.driver is not None:
            return
        from selenium import webdriver

        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("headless")
        print("starting Chrome")
        self.driver = webdriver.Chrome(options=options)
        # self.driver.implicitly_wait(10)  # seconds

    def end(self) -> None:
        if self.close and self.driver is not None:
            self.driver.close()

    @property
    def wait(self) -> WebDriverWait:

        if self.wait_ is not None:
            return self.wait_
        self.wait_ = WebDriverWait(self.driver, self.WAIT)
        return self.wait_

    def wait_for_css(self, css: str) -> None:
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css)))

    def get_response(self, paper: Paper, header: dict[str, str]) -> Response:
        # pylint: disable=import-outside-toplevel
        from selenium.common.exceptions import TimeoutException

        assert self.driver is not None
        url = f"https://doi.org/{paper.doi}"
        self.driver.get(url)
        try:
            self.wait_for_css("html")
        except TimeoutException:
            assert False, "selenium timeout"  # trigger failure with

        h = self.driver.find_element(by=By.TAG_NAME, value="html")

        txt = h.get_attribute("outerHTML") or ""

        return SeleniumResponse(
            content=txt.encode("utf-8"),
            url=self.driver.current_url or "<unknown>",
        )
