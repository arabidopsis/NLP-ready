import os
import re
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
    for f in os.listdir(DATADIR + d):
        f, ext = os.path.splitext(f)
        if ext in {'.html', '.xml'}:
            yield f


def dump(paper, xml):
    with open('dump_{}.html'.format(paper.pmid), 'wb') as fp:
        fp.write(xml)


class Clean(object):
    SPACE = re.compile(r'\s+', re.I)

    def find_title(self, sec, h='h2', op=lambda a, b: a == b, txt=[]):
        h = sec.find(h)
        if h:
            h2 = h.text.lower()
            for a in txt:
                if op(h2, a):
                    return True
        return False

    def tostr(self, sec):

        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


class Generate(object):
    parser = 'lxml'

    def __init__(self, issn):
        self.issn = issn
        self._pmid2doi = None
        self._journal = None

    @property
    def pmid2doi(self):
        if self._pmid2doi:
            return self._pmid2doi
        with open(JCSV, 'r', encoding='utf8') as fp:
            R = csv.reader(fp)
            next(R)
            pmid2doi = {pmid: Paper(doi=doi, year=year, issn=issn, name=name, pmid=pmid)
                        for pmid, issn, name, year, doi in R if doi and issn == self.issn}
        self._pmid2doi = pmid2doi
        return pmid2doi

    @property
    def journal(self):
        if not self._journal:
            d = read_issn()
            self._journal = d[self.issn][1]
        return self._journal

    def create_clean(self, soup, pmid):
        raise RuntimeError('unimplemented')

    def ensure_dir(self):
        if not os.path.isdir(DATADIR + 'cleaned_%s' % self.issn):
            os.mkdir(DATADIR + 'cleaned_%s' % self.issn)

    def get_soup(self, gdir, pmid):
        fname = DATADIR + gdir + '/{}.html'.format(pmid)
        with open(fname, 'rb') as fp:
            soup = BeautifulSoup(fp, self.parser)
        return soup

    def run(self):
        print(self.issn)
        self.ensure_dir()

        gdir = 'xml_%s' % self.issn
        for pmid in readxml(gdir):
            self.generate_pmid(gdir, pmid)

    def clean_name(self, pmid):
        fname = DATADIR + 'cleaned_{}/{}_cleaned.txt'.format(self.issn, pmid)
        return fname

    def generate_pmid(self, gdir, pmid):

        soup = self.get_soup(gdir, pmid)
        e = self.create_clean(soup, pmid)
        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            click.secho('{}: missing: abs {}, methods {}, results {} doi={}'.format(
                pmid, a is None, m is None, r is None, self.pmid2doi[pmid].doi), fg='red')
            return
        fname = self.clean_name(pmid)
        if os.path.exists(fname):
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

    def tohtml(self, template='template.html'):
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader('templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(template)
        gdir = 'xml_%s' % self.issn
        papers = []
        pmid2doi = self.pmid2doi
        for idx, pmid in enumerate(readxml(gdir)):
            soup = self.get_soup(gdir, pmid)
            e = self.create_clean(soup, pmid)
            papers.append((pmid2doi[pmid], e))
            if idx > 5:
                break
        return template.render(papers=papers, issn=self.issn, this=self)


class FakeResponse(object):
    content = None
    status_code = 200
    url = None

    def raise_for_status(self):
        pass


class Download(object):
    parser = 'lxml'
    Referer = 'http://google.com'

    def __init__(self, issn, mx=0, sleep=10.):
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
                    soup = BeautifulSoup(BytesIO(xml), self.parser)
                    err = self.check_soup(paper, soup, resp)
                    if err:
                        xml = err
                        d = fdir
                        failed.add(paper.pmid)
                    else:
                        d = gdir
                        done.add(paper.pmid)

            except ConnectionError as e:
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
