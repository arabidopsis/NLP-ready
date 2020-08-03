import csv
import os
import sys
import time
from collections import defaultdict, namedtuple
from io import BytesIO

import click
import regex as re
import requests
from bs4 import BeautifulSoup
from requests import ConnectionError as RequestConnectionError

import config as Config
from rescantxt import find_primers, reduce_nums

Paper = namedtuple("Paper", ["doi", "year", "pmid", "issn", "name", "pmcid", "title"])

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
)


def pmid2doi(check=lambda doi, issn: True):
    return {p.pmid: p for p in read_suba_papers_csv() if check(p.doi, p.issn)}


def read_journals_csv():
    return pmid2doi()


def read_suba_papers_csv():
    """suba_papers.csv is a list of *all* pubmed ids from SUBA4."""
    return readx_suba_papers_csv(Config.JCSV)


def readx_suba_papers_csv(csvfile):
    with open(csvfile, "r", encoding="utf8") as fp:
        R = csv.reader(fp)
        next(R)  # skip header
        # print(header)
        for row in R:
            if len(row) == 5:
                pmid, issn, name, year, doi = row
                title = pmcid = None
            else:
                pmid, issn, name, year, doi, pmcid, title = row
                if issn == "missing-issn":
                    # click.secho("missing %s" % pmid, fg='yellow')
                    continue
            yield Paper(
                doi=doi,
                year=int(year),
                issn=issn,
                name=name,
                pmid=pmid,
                pmcid=pmcid,
                title=title,
            )


def read_pubmed_csv(csvfile, header=True, pcol=0):
    """File csvfile is a list of *all* pubmed ids from SUBA4."""
    with open(csvfile, "r", encoding="utf8") as fp:
        R = csv.reader(fp)
        if header:
            next(R)  # skip header
        # print(header)
        for row in R:
            yield row[pcol]


def read_issn():

    ISSN = defaultdict(list)
    for p in read_suba_papers_csv():
        ISSN[p.issn].append(p)
    return {k: (len(v), v[0].name) for k, v in ISSN.items()}

    # ISSN = {}
    # with open('jcounts.csv', 'r') as fp:
    #     R = csv.reader(fp)
    #     next(R)
    #     for issn, count, name, _, _ in R:
    #         ISSN[p.issn] = (int(count), p.name)
    # return ISSN


def readxml(d):
    """Scan directory d and return the pubmed ids."""
    dd = Config.DATADIR + d
    if not os.path.isdir(dd):
        # click.secho('readxml: no directory to scan for %s' % d, fg='red', file=sys.stderr)
        return
    for f in os.listdir(dd):
        f, ext = os.path.splitext(f)
        if ext in {".html", ".xml"}:
            yield f


def dump(paper, xml):
    with open("dump_{}.html".format(paper.pmid), "wb") as fp:
        fp.write(xml)


_Plug = object()


class Clean(object):
    SPACE = re.compile(r"\s+", re.I)
    FIGURE = "[[FIGURE: %s]]"
    TABLE = "[[TABLE: %s]]"
    a = _Plug
    m = _Plug
    r = _Plug
    t = _Plug
    f = _Plug
    x = _Plug

    def __init__(self, root):
        self.root = root

    def find_title(self, sec, h="h2", op=lambda h, b: h == b, txt=None):
        if txt is None:
            txt = []
        h = sec.find(h)
        if h:
            h2 = h.text.lower().strip()
            h2 = self.SPACE.sub(" ", h2)
            for a in txt:
                # print('"%s"="%s" %s %s' % (h2, a, op(h2, a), h2.endswith(a)))
                if op(h2, a):
                    return True
        return False

    def title(self):
        t = self.root.find("title")
        if t:
            return t.text.strip()
        return None

    def abstract(self):
        raise NotImplementedError()

    def results(self):
        raise NotImplementedError()

    def methods(self):
        raise NotImplementedError()

    def xrefs(self):
        raise NotImplementedError()

    def full_text(self):
        raise NotImplementedError()

    def tostr(self, sec):

        txt = [self.SPACE.sub(" ", p.text) for p in sec.select("p")]
        return txt

    def tostr2(self, sec):
        def to_p(s):
            a = self.root.new_tag("p")
            a.string = s.text
            s.replace_with(a)

        if isinstance(sec, list):
            for s in sec:
                for p in s.select("h2,h3,h4"):
                    to_p(p)

        else:
            for p in sec.select("h2,h3,h4"):
                to_p(p)
        return self.tostr(sec)

    def s_abstract(self):
        if self.a is not _Plug:
            return self.a
        self.a = self.abstract()
        return self.a

    def s_methods(self):
        if self.m is not _Plug:
            return self.m
        self.m = self.methods()
        return self.m

    def s_results(self):
        if self.r is not _Plug:
            return self.r
        self.r = self.results()
        return self.r

    def s_full_text(self):
        if self.f is not _Plug:
            return self.f
        self.f = self.full_text()
        return self.f

    def s_title(self):
        if self.t is not _Plug:
            return self.t
        self.t = self.title()
        return self.t

    def s_xrefs(self):
        if self.x is not _Plug:
            return self.x
        self.x = self.xrefs()
        return self.x

    def has_all_sections(self):
        a = self.s_abstract()
        m = self.s_methods()
        r = self.s_results()
        return a is not None and m is not None and r is not None

    def has_rmm(self):
        m = self.s_methods()
        r = self.s_results()
        return m is not None or r is not None

    def missing(self):
        a = self.s_abstract()
        m = self.s_methods()
        r = self.s_results()
        ret = []
        if a is None:
            ret.append("a")
        if m is None:
            ret.append("m")
        if r is None:
            ret.append("r")
        return " ".join(ret) if ret else ""

    def _newfig(self, tag, fmt, caption="figcaption p", node="p"):
        captions = [c.text for c in tag.select(caption)]
        txt = " ".join(captions)
        new_tag = self.root.new_tag(node)
        new_tag.string = fmt % txt
        return new_tag

    def newfig(self, tag, caption="figcaption p", node="p"):
        return self._newfig(tag, self.FIGURE, caption=caption, node=node)

    def newtable(self, tag, caption="figcaption p", node="p"):
        return self._newfig(tag, self.TABLE, caption=caption, node=node)


def make_jinja_env():
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["prime"] = find_primers
    return env


class Generate(object):
    parser = "lxml"

    def __init__(
        self,
        issn,
        onlynewer=False,
        pmid2doi=None,
        journal=None,
        partial=False,
        **kwargs
    ):
        self.issn = issn
        self._pmid2doi = pmid2doi
        self._journal = journal
        self._onlynewer = onlynewer
        self.partial = partial

    @property
    def pmid2doi(self):
        if self._pmid2doi:
            return self._pmid2doi

        def check(doi, issn):
            if self.issn in {"epmc", "elsevier"}:
                return True
            return doi and issn == self.issn

        self._pmid2doi = pmid2doi(check)
        return self._pmid2doi

    @property
    def journal(self):
        if self._journal:
            return self._journal
        if self.issn in {"epmc", "elsevier"}:
            self._journal = self.issn
        else:
            d = {p.issn: p.name for p in self.pmid2doi.values() if p.name}
            # d = read_issn()
            if self.issn in d:
                # self._journal = d[self.issn][1]
                self._journal = d[self.issn]
            else:
                self._journal = self.issn
        return self._journal

    def create_clean(self, soup, pmid):
        raise NotImplementedError()

    def ensure_dir(self):
        dname = Config.DATADIR + "cleaned"
        if not os.path.isdir(dname):
            os.mkdir(dname)
        name = self.journal.replace(".", "").lower()
        name = "-".join(name.split())
        dname = dname + "/cleaned_{}_{}".format(self.issn, name)
        if not os.path.isdir(dname):
            os.mkdir(dname)
        return dname

    def get_xml_name(self, gdir, pmid):
        fname = Config.DATADIR + gdir + "/{}.html".format(pmid)
        if not os.path.isfile(fname):
            fname = Config.DATADIR + gdir + "/{}.xml".format(pmid)
        return fname

    def get_soup(self, gdir, pmid):
        fname = self.get_xml_name(gdir, pmid)
        with open(fname, "rb") as fp:
            soup = BeautifulSoup(fp, self.parser)
        return soup

    def run(self, overwrite=True, prefix=None, num=False):
        gdir = "xml_%s" % self.issn
        papers = readxml(gdir)
        if not papers:
            return

        dname = self.ensure_dir()

        written = False

        for pmid in papers:
            ok = self.generate_pmid(
                gdir, pmid, overwrite=overwrite, prefix=prefix, num=num
            )
            written = written or ok

        if not written:
            click.secho("no data for %s" % self.issn, fg="red", file=sys.stderr)
            try:
                os.rmdir(dname)
            except OSError:
                pass

    def tokenize(self):
        gdir = "xml_%s" % self.issn
        for pmid in readxml(gdir):
            soup = self.get_soup(gdir, pmid)
            e = self.create_clean(soup, pmid)
            a = e.abstract()
            m = e.methods()
            r = e.results()
            if a is not None:
                for p in e.tostr(a):
                    yield "a", reduce_nums(p)
            if m is not None:
                for p in e.tostr(m):
                    yield "m", reduce_nums(p)
            if r is not None:
                for p in e.tostr(r):
                    yield "r", reduce_nums(p)

    def clean_name(self, pmid):
        dname = self.ensure_dir()
        fname = "{}/{}_cleaned.txt".format(dname, pmid)
        return fname

    def generate_pmid(self, gdir, pmid, overwrite=True, prefix=None, num=False):
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

        if a is None or m is None or r is None:
            click.secho(
                "{}: missing: abs {}, methods {}, results {} doi={}".format(
                    pmid, a is None, m is None, r is None, self.pmid2doi[pmid].doi
                ),
                fg="red",
            )
            return False

        if exists:
            click.secho("overwriting %s" % fname, fg="yellow")
        else:
            click.secho("generating %s" % fname, fg="magenta")

        def con(sec):
            if num:
                return " ".join(reduce_nums(a) for a in e.tostr(sec))
            else:
                return " ".join(e.tostr(sec))

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

    def tohtml(
        self,
        template="template.html",
        save=False,
        prefix="",
        env=None,
        verbose=True,
        num=False,
    ):
        if env is None:
            env = make_jinja_env()

        def getfname():
            if self.issn not in {"epmc", "elsevier"}:
                name = self.journal
            else:
                name = self.issn
            name = name.replace(".", "").lower()
            name = "-".join(name.split())
            fname = prefix + "%s-%s.html" % (self.issn, name)
            return fname

        template = env.get_template(template)
        gdir = "xml_%s" % self.issn
        fdir = "failed_%s" % self.issn
        papers = []

        # only look for pmids that we want.
        pmid2doi = self.pmid2doi
        todo = [pmid2doi[pmid] for pmid in readxml(gdir) if pmid in pmid2doi]
        failed = [pmid2doi[pmid] for pmid in readxml(fdir) if pmid in pmid2doi]

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
                        "missing %s for %s http://doi.org/%s"
                        % (missing, paper.pmid, paper.doi),
                        fg="magenta",
                        file=sys.stderr,
                    )
                papers.append((paper, e))
            except Exception as err:
                click.secho(
                    "failed for %s http://doi.org/%s %s"
                    % (paper.pmid, paper.doi, str(err)),
                    fg="red",
                    file=sys.stderr,
                )
                raise err
                # papers.append((paper, Clean(soup)))

        t = template.render(
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
            return fname, papers, failed

        return t


class Download(object):
    parser = "lxml"
    Referer = "http://google.com"

    def __init__(self, issn, mx=0, sleep=10.0, **kwargs):
        self.issn = issn
        self.sleep = sleep
        self.mx = mx

    def ensure_dirs(self):
        fdir = "failed_%s" % self.issn
        gdir = "xml_%s" % self.issn
        if not os.path.isdir(Config.DATADIR + fdir):
            os.mkdir(Config.DATADIR + fdir)
        if not os.path.isdir(Config.DATADIR + gdir):
            os.mkdir(Config.DATADIR + gdir)

    def get_response(self, paper, header):
        resp = requests.get("http://doi.org/{}".format(paper.doi), headers=header)
        return resp

    def check_soup(self, paper, soup, resp):
        raise NotImplementedError()

    def start(self):
        pass

    def end(self):
        pass

    def create_soup(self, paper, resp):
        xml = resp.content
        soup = BeautifulSoup(BytesIO(xml), self.parser)
        return soup

    def run(self):
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

        print(
            "%s: %d failed, %d done, %d todo"
            % (self.issn, len(failed), len(done), len(todo))
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
                    d = fdir
                    failed.add(paper.pmid)
                else:
                    resp.raise_for_status()
                    header["Referer"] = resp.url
                    xml = resp.content
                    soup = self.create_soup(paper, resp)
                    err = self.check_soup(paper, soup, resp)
                    if err:
                        xml = err
                        d = fdir
                        failed.add(paper.pmid)
                    else:
                        d = gdir
                        done.add(paper.pmid)

            except (RequestConnectionError, AssertionError) as e:
                d = fdir
                xml = str(e).encode("utf-8")
                click.secho(
                    "failed %s %s %s" % (paper.pmid, paper.doi, str(e)), fg="red"
                )
                failed.add(paper.pmid)

            with open(Config.DATADIR + "{}/{}.html".format(d, paper.pmid), "wb") as fp:
                fp.write(xml)

            del todo[paper.pmid]
            print(
                "%d failed, %d done, %d todo: %s"
                % (len(failed), len(done), len(todo), paper.pmid)
            )
            if self.sleep > 0 and idx < len(lst) - 1:
                time.sleep(self.sleep)
        self.end()


class FakeResponse(object):
    content = None
    status_code = 200
    encoding = "UTF-8"
    url = None

    def raise_for_status(self):
        pass


class DownloadSelenium(Download):

    WAIT = 10

    def __init__(
        self, issn, mx=0, sleep=10.0, headless=True, close=True, driver=None, **kwargs
    ):
        super().__init__(issn, mx=mx, sleep=sleep, **kwargs)
        self.headless = headless
        self.close = close
        self.driver = driver

    def start(self):
        if self.driver is not None:
            return
        from selenium import webdriver

        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("headless")
        print("starting Chrome")
        self.driver = webdriver.Chrome(chrome_options=options)
        # self.driver.implicitly_wait(10)  # seconds

    def end(self):
        if self.close and self.driver is not None:
            self.driver.close()

    def wait(self):
        from selenium.webdriver.support.ui import WebDriverWait

        return WebDriverWait(self.driver, self.WAIT)

    def get_response(self, paper, header):
        from selenium.common.exceptions import TimeoutException

        url = "http://doi.org/{}".format(paper.doi)
        self.driver.get(url)
        try:
            self.wait()
        except TimeoutException as e:
            assert False, "selenium timeout"  # trigger failure with

        h = self.driver.find_element_by_tag_name("html")
        txt = h.get_attribute("outerHTML")
        resp = FakeResponse()
        resp.url = self.driver.current_url
        resp.content = txt.encode("utf-8")
        return resp
