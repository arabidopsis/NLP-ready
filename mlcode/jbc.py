import csv
import os
import re
import time
import requests
import click
from io import BytesIO
from bs4 import BeautifulSoup

DATADIR = '../data/'
JCSV = 'journals.csv'


def readxml(d):
    for f in os.listdir(DATADIR + d):
        f, ext = os.path.splitext(f)
        if ext == '.xml':
            yield f


def download_jbc(journal, sleep=5.0, mx=0):
    header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                            '(KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
              'Referer': 'http://www.jbc.org'
              }
    fdir = 'failed_%s' % journal
    gdir = 'xml_%s' % journal
    if not os.path.isdir(DATADIR + fdir):
        os.mkdir(DATADIR + fdir)
    if not os.path.isdir(DATADIR + gdir):
        os.mkdir(DATADIR + gdir)
    failed = set(readxml(fdir))
    done = set(readxml(gdir))

    ISSN = {journal}
    allpmid = failed | done
    with open(JCSV, 'r', encoding='utf8') as fp:
        R = csv.reader(fp)
        next(R)
        todo = {pmid: (doi, issn, int(year)) for pmid, issn, name, year,
                doi in R if doi and issn in ISSN and pmid not in allpmid}

    print('%s: %d failed, %d done, %d todo' % (journal, len(failed), len(done), len(todo)))
    lst = sorted(todo.items(), key=lambda t: t[0])
    if mx > 0:
        lst = lst[:mx]
    for pmid, (doi, issn, year) in lst:
        resp = requests.get('http://doi.org/{}'.format(doi), headers=header)
        if not resp.url.endswith('.full'):
            resp = requests.get(resp.url + '.full', headers=header)

        if resp.status_code == 404:
            xml = b'failed404'
            d = fdir
            failed.add(pmid)
        else:
            resp.raise_for_status()
            header['Referer'] = resp.url
            xml = resp.content
            soup = BeautifulSoup(BytesIO(xml), 'html.parser')
            a = soup.select('div.article.fulltext-view')
            if not a and year <= 2001:  # probably only a (scanned?) PDF version
                xml = b'failed-only-pdf'
                d = fdir
                failed.add(pmid)
            else:
                assert a and len(a) == 1, (pmid, resp.url)
                d = gdir
                done.add(pmid)

        with open(DATADIR + '{}/{}.xml'.format(d, pmid), 'wb') as fp:
            fp.write(xml)

        del todo[pmid]
        print('%d failed, %d done, %d todo: %s' % (len(failed), len(done), len(todo), pmid))
        time.sleep(sleep)


class JBC(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        a = root.select('div.article.fulltext-view')[0]
        assert a
        self.article = a

    def results(self):
        secs = self.article.select('div.section.results')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            h2 = sec.find('h2')
            if h2 and h2.string.lower() == 'results':
                return sec

        return None

    def methods(self):
        secs = self.article.select('div.section.methods')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            h2 = sec.find('h2')
            if h2 and h2.string.lower() == 'methods':
                return sec

        return None

    def abstract(self):
        secs = self.article.select('div.section.abstract')
        return secs[0] if secs else None

    def tostr(self, sec):
        for a in sec.select('p a.xref-bibr'):
            a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


def gen_jbc(journal):
    print(journal)
    if not os.path.isdir(DATADIR + 'cleaned_%s' % journal):
        os.mkdir(DATADIR + 'cleaned_%s' % journal)
    gdir = 'xml_%s' % journal
    for pmid in readxml(gdir):
        print(pmid)
        fname = DATADIR + gdir + '/{}.xml'.format(pmid)
        with open(fname, 'rb') as fp:
            soup = BeautifulSoup(fp, 'html.parser')
        e = JBC(soup)
        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            click.secho('{}: missing: abs {}, methods {}, results {}'.format(
                pmid, a is None, m is None, r is None), fg='red')
            continue
        fname = DATADIR + 'cleaned_{}/{}_cleaned.txt'.format(journal, pmid)
        if os.path.exists(fname):
            click.secho('overwriting %s' % fname, fg='yellow')

        with open(fname, 'w', encoding='utf-8') as fp:
            w = ' '.join(e.tostr(a))
            print('!~ABS~! %s' % w, file=fp)
            w = ' '.join(e.tostr(r))
            print('!~RES~! %s' % w, file=fp)
            w = ' '.join(e.tostr(m))
            print('!~MM~! %s' % w, file=fp)


if __name__ == '__main__':
    download_jbc(journal='0021-9258', sleep=60. * 2, mx=0)
    download_jbc(journal='1083-351X', sleep=60. * 2, mx=0)
    # gen_jbc(journal='0021-9258')
    # gen_jbc(journal='1083-351X')
