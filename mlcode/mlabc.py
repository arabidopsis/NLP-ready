import os
import sys
import regex as re
import csv
import time
from io import BytesIO
from collections import namedtuple

import click
import requests
from requests import ConnectionError
from bs4 import BeautifulSoup


DATADIR = '../data/'
JCSV = 'journals.csv'

Paper = namedtuple('Paper', ['doi', 'year', 'pmid', 'issn', 'name'])

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'


def read_journals_csv():
    with open(JCSV, 'r', encoding='utf8') as fp:
        R = csv.reader(fp)
        next(R)
        pmid2doi = {pmid: Paper(doi=doi, year=int(year), issn=issn, name=name, pmid=pmid)
                    for pmid, issn, name, year, doi in R}
    return pmid2doi


def read_suba_papers_csv():
    """suba_papers.csv is a list of *all* pubmed ids from SUBA4."""
    # R = csv.reader(open('SUBA_Data4_JDK.csv', encoding='latin1'))
    with open(JCSV, 'r', encoding='utf8') as fp:
        R = csv.reader(fp)
        next(R)  # skip header
        # print(header)
        for pmid, issn, name, year, doi in R:
            yield Paper(doi=doi, year=int(year), issn=issn, name=name, pmid=pmid)


def read_issn():

    ISSN = {}
    with open('jcounts.csv', 'r') as fp:
        R = csv.reader(fp)
        next(R)
        for issn, count, name, _, _ in R:
            ISSN[issn] = (int(count), name)
    return ISSN


def readxml(d):
    """Scan directory d and return the pubmed ids."""
    dd = DATADIR + d
    if not os.path.isdir(dd):
        click.secho('readxml: no directory to scan for %s' % d, fg='red', file=sys.stderr)
        return
    for f in os.listdir(dd):
        f, ext = os.path.splitext(f)
        if ext in {'.html', '.xml'}:
            yield f


def dump(paper, xml):
    with open('dump_{}.html'.format(paper.pmid), 'wb') as fp:
        fp.write(xml)


_Plug = object()


class Clean(object):
    SPACE = re.compile(r'\s+', re.I)
    a = _Plug
    m = _Plug
    r = _Plug
    t = _Plug

    def __init__(self, root):
        self.root = root

    def find_title(self, sec, h='h2', op=lambda a, b: a == b, txt=[]):
        h = sec.find(h)
        if h:
            h2 = h.text.lower()
            for a in txt:
                if op(h2, a):
                    return True
        return False

    def title(self):
        t = self.root.find('title')
        if t:
            return t.text.strip()
        return None

    def abstract(self):
        return None

    def results(self):
        return None

    def methods(self):
        return None

    def tostr(self, sec):

        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt

    def tostr2(self, sec):
        def to_p(s):
            a = self.root.new_tag('p')
            a.string = s.text
            s.replace_with(a)

        if isinstance(sec, list):
            for s in sec:
                for p in s.select('h2,h3,h4'):
                    to_p(p)

        else:
            for p in sec.select('h2,h3,h4'):
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

    def s_title(self):
        if self.t is not _Plug:
            return self.t
        self.t = self.title()
        return self.t

    def has_all_sections(self):
        a = self.s_abstract()
        m = self.s_methods()
        r = self.s_results()
        return a is not None and m is not None and r is not None

    def missing(self):
        a = self.s_abstract()
        m = self.s_methods()
        r = self.s_results()
        ret = []
        if a is None:
            ret.append('a')
        if m is None:
            ret.append('m')
        if r is None:
            ret.append('r')
        return ' '.join(ret) if ret else ''


class Generate(object):
    parser = 'lxml'

    def __init__(self, issn, onlynewer=False, **kwargs):
        self.issn = issn
        self._pmid2doi = None
        self._journal = None
        self._onlynower = onlynewer

    @property
    def pmid2doi(self):
        if self._pmid2doi:
            return self._pmid2doi

        def check(doi, issn):
            if self.issn in {'epmc', 'elsevier'}:
                return True
            return doi and issn == self.issn

        with open(JCSV, 'r', encoding='utf8') as fp:
            R = csv.reader(fp)
            next(R)
            pmid2doi = {pmid: Paper(doi=doi, year=int(year), issn=issn, name=name, pmid=pmid)
                        for pmid, issn, name, year, doi in R if check(doi, issn)}
        self._pmid2doi = pmid2doi
        return pmid2doi

    @property
    def journal(self):
        if self.issn in {'epmc', 'elsevier'}:
            return self.issn
        if not self._journal:
            d = read_issn()
            if self.issn in d:
                self._journal = d[self.issn][1]
            else:
                self._journal = self.issn
        return self._journal

    def create_clean(self, soup, pmid):
        raise RuntimeError('unimplemented')

    def ensure_dir(self):
        dname = DATADIR + 'cleaned'
        if not os.path.isdir(dname):
            os.mkdir(dname)
        name = self.journal.replace('.', '').lower()
        name = '-'.join(name.split())
        dname = dname + '/cleaned_{}_{}'.format(self.issn, name)
        if not os.path.isdir(dname):
            os.mkdir(dname)
        return dname

    def get_xml_name(self, gdir, pmid):
        fname = DATADIR + gdir + '/{}.html'.format(pmid)
        if not os.path.isfile(fname):
            fname = DATADIR + gdir + '/{}.xml'.format(pmid)
        return fname

    def get_soup(self, gdir, pmid):
        fname = self.get_xml_name(gdir, pmid)
        with open(fname, 'rb') as fp:
            soup = BeautifulSoup(fp, self.parser)
        return soup

    def run(self, overwrite=True, prefix=None):
        self.ensure_dir()

        gdir = 'xml_%s' % self.issn
        for pmid in readxml(gdir):
            self.generate_pmid(gdir, pmid, overwrite=overwrite, prefix=prefix)

    def tokenize(self):
        gdir = 'xml_%s' % self.issn
        for pmid in readxml(gdir):
            soup = self.get_soup(gdir, pmid)
            e = self.create_clean(soup, pmid)
            a = e.abstract()
            m = e.methods()
            r = e.results()
            if a:
                for p in e.tostr(a):
                    yield 'a', reduce_nums(p)
            if m:
                for p in e.tostr(m):
                    yield 'm', reduce_nums(p)
            if r:
                for p in e.tostr(r):
                    yield 'r', reduce_nums(p)

    def clean_name(self, pmid):
        dname = self.ensure_dir()
        fname = '{}/{}_cleaned.txt'.format(dname, pmid)
        return fname

    def generate_pmid(self, gdir, pmid, overwrite=True, prefix=None):
        fname = self.clean_name(pmid)
        exists = os.path.exists(fname)
        if exists and not overwrite:
            return
        if exists and self._onlynewer:
            xname = self.get_xml_name(gdir, pmid)
            if os.path.exists(xname):
                tgt = os.stat(fname).st_mtime
                src = os.stat(xname).st_mtime
                if tgt >= src:  # target newer that surc
                    return

        soup = self.get_soup(gdir, pmid)
        e = self.create_clean(soup, pmid)
        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            click.secho('{}: missing: abs {}, methods {}, results {} doi={}'.format(
                pmid, a is None, m is None, r is None, self.pmid2doi[pmid].doi), fg='red')
            return

        if exists:
            click.secho('overwriting %s' % fname, fg='yellow')
        else:
            click.secho('generating %s' % fname, fg='magenta')

        with open(fname, 'w', encoding='utf-8') as fp:
            w = ' '.join(e.tostr(a))
            print('!~ABS~! %s' % w, file=fp)
            w = ' '.join(e.tostr(r))
            print('!~RES~! %s' % w, file=fp)
            w = ' '.join(e.tostr(m))
            print('!~MM~! %s' % w, file=fp)

    def tohtml(self, template='template.html', save=False, prefix='', env=None):
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        if env is None:
            env = Environment(
                loader=FileSystemLoader('templates'),
                autoescape=select_autoescape(['html', 'xml'])
            )
            env.filters['prime'] = find_primers

        template = env.get_template(template)
        gdir = 'xml_%s' % self.issn
        papers = []
        pmid2doi = self.pmid2doi
        todo = [pmid2doi[pmid] for pmid in readxml(gdir)]

        todo = sorted(todo, key=lambda p: -p.year)
        nart = len(todo)
        for paper in todo:
            print(paper.pmid, paper.issn, paper.doi)

            soup = self.get_soup(gdir, paper.pmid)
            try:
                e = self.create_clean(soup, paper.pmid)
                if not e.has_all_sections():
                    click.secho('not all sections for %s http://doi.org/%s' %
                                (paper.pmid, paper.doi), fg='magenta', file=sys.stderr)
                papers.append((paper, e))
            except Exception as err:
                click.secho('failed for %s http://doi.org/%s %s' %
                            (paper.pmid, paper.doi, str(err)), fg='red', file=sys.stderr)
                raise err
                papers.append((paper, Clean(soup)))

        t = template.render(papers=papers, issn=self.issn, this=self)
        if save:
            if self.issn not in {'epmc', 'elsevier'}:
                name = self.journal
            else:
                name = self.issn
            name = name.replace('.', '').lower()
            name = '-'.join(name.split())
            fname = prefix + '%s-%s-n%d.html' % (self.issn, name, nart)
            with open(fname, 'w') as fp:
                fp.write(t)
            return fname, papers

        return t


# [SIC!] unicode dashes utf-8 b'\xe2\x80\x90' 0x2010
PRIMER = re.compile(
    r'''\b((?:5[′'][-‐]?)?[CTAG\s-]{7,}[CTAG](?:[-‐]?3[′'])?)(\b|$|[\s;:)/,\.])''', re.I)
pf = r'[0-9]+(?:\.[0-9]+)?'
number = r'[+-]?' + pf + r'(?:\s*±\s*' + pf + r')?'
pm = r'[0-9]+(?:\s*±\s*[0-9]+)?'
TEMP = re.compile(number + r'\s*°C')
MM = re.compile(number + r'\s*μ[Mm]')
MGL = re.compile(number + r'\s*mg/l')

N = re.compile(number + r'(?:\s|-)?(°C|μM|μl|mg/l|%|mM|nM|rpm|ml|NA|h|K|M|min|g/l|s|kb|μg/μl|μg)\b')
FPCT = re.compile(r'[0-9]+\.[0-9]*%')
PCT = re.compile(pm + '%')
PH = re.compile(r'\bpH\s*' + number)
INT = re.compile(r'\b[0-9]+\b')  # picks up ncb-111 !!!!
FLOAT = re.compile(r'\b[0-9]+\.[0-9]*\b')

INT = re.compile(r'\s[0-9]+(?=\s)')  # [sic] spaces. \b picks up ncb-111 !!!!
FLOAT = re.compile(r'\s[0-9]+\.[0-9]*(?=\s)')
EXP = re.compile(r'\b[0-9]+(?:\.[0-9]*)?\s*×\s*(e|E|10)[+−-]?[0-9]+\b')
EXP2 = re.compile(r'\b[0-9]+\.[0-9]*(?:e|E|10)[+−-]?[0-9]+\b')


from jinja2 import Markup


def reduce_nums(txt):
    txt = N.sub(r'NUMBER_\1', txt)
    txt = PH.sub(r'NUMBER_pH', txt)
    txt = FPCT.sub(r'NUMBER_%', txt)
    txt = PCT.sub(r'NUMBER_%', txt)
    txt = EXP.sub('EXPNUM', txt)
    txt = EXP2.sub(' EXPNUM', txt)
    txt = FLOAT.sub(' FLOAT ', txt)
    txt = INT.sub(' INT ', txt)
    return txt


def find_primers(txt):
    txt = reduce_nums(txt)

    return Markup(PRIMER.sub(r'<b class="primer">\1</b>\2', txt))


class Download(object):
    parser = 'lxml'
    Referer = 'http://google.com'

    def __init__(self, issn, mx=0, sleep=10., **kwargs):
        self.issn = issn
        self.sleep = sleep
        self.mx = mx

    def check_dirs(self):
        fdir = 'failed_%s' % self.issn
        gdir = 'xml_%s' % self.issn
        if not os.path.isdir(DATADIR + fdir):
            os.mkdir(DATADIR + fdir)
        if not os.path.isdir(DATADIR + gdir):
            os.mkdir(DATADIR + gdir)

    def get_response(self, paper, header):
        resp = requests.get('http://doi.org/{}'.format(paper.doi), headers=header)
        return resp

    def check_soup(self, paper, soup, resp):
        raise RuntimeError("not implemented")

    def start(self):
        pass

    def end(self):
        pass

    def create_soup(self, paper, resp):
        xml = resp.content
        soup = BeautifulSoup(BytesIO(xml), self.parser)
        return soup

    def run(self):
        header = {'User-Agent': USER_AGENT,
                  'Referer': self.Referer
                  }
        self.check_dirs()
        fdir = 'failed_%s' % self.issn
        gdir = 'xml_%s' % self.issn

        failed = set(readxml(fdir))
        done = set(readxml(gdir))

        allpmid = failed | done
        with open(JCSV, 'r', encoding='utf8') as fp:
            R = csv.reader(fp)
            next(R)
            todo = {pmid: Paper(doi=doi, year=int(year), issn=issn, name=name, pmid=pmid)
                    for pmid, issn, name, year, doi in R
                    if doi and issn in self.issn and pmid not in allpmid}

        print('%s: %d failed, %d done, %d todo' % (self.issn, len(failed), len(done), len(todo)))
        lst = sorted(todo.values(), key=lambda p: -p.year)
        if self.mx > 0:
            lst = lst[:self.mx]
        if not lst:
            return
        self.start()
        for idx, paper in enumerate(lst):
            try:
                resp = self.get_response(paper, header)
                if resp.status_code == 404:
                    xml = b'failed404'
                    d = fdir
                    failed.add(paper.pmid)
                else:
                    resp.raise_for_status()
                    header['Referer'] = resp.url
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

            except (ConnectionError, AssertionError) as e:
                d = fdir
                xml = str(e).encode('utf-8')
                click.secho('failed %s %s %s' % (paper.pmid, paper.doi, str(e)), fg='red')
                failed.add(paper.pmid)

            with open(DATADIR + '{}/{}.html'.format(d, paper.pmid), 'wb') as fp:
                fp.write(xml)

            del todo[paper.pmid]
            print('%d failed, %d done, %d todo: %s' %
                  (len(failed), len(done), len(todo), paper.pmid))
            if self.sleep > 0 and idx < len(lst) - 1:
                time.sleep(self.sleep)
        self.end()


class FakeResponse(object):
    content = None
    status_code = 200
    encoding = 'UTF-8'
    url = None

    def raise_for_status(self):
        pass


class DownloadSelenium(Download):
    driver = None
    headless = True
    WAIT = 10

    def __init__(self, issn, mx=0, sleep=10., headless=True, close=True, **kwargs):
        super().__init__(issn, mx=mx, sleep=sleep, **kwargs)
        self.headless = headless
        self.close = close

    def start(self):
        from selenium import webdriver
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('headless')
        self.driver = webdriver.Chrome(chrome_options=options)
        # self.driver.implicitly_wait(10)  # seconds

    def end(self):
        if self.close and self.driver:
            self.driver.close()

    def wait(self):
        from selenium.webdriver.support.ui import WebDriverWait
        return WebDriverWait(self.driver, self.WAIT)

    def get_response(self, paper, header):
        url = 'http://doi.org/{}'.format(paper.doi)
        self.driver.get(url)
        self.wait()

        h = self.driver.find_element_by_tag_name('html')
        txt = h.get_attribute('outerHTML')
        resp = FakeResponse()
        resp.url = self.driver.current_url
        resp.content = txt.encode('utf-8')
        return resp
