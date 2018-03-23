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
        if ext == '.html':
            yield f


def download_aspb(journal, sleep=5.0, mx=0):
    header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
              'Referer': 'http://www.plantcell.org'
              }

    fdir = 'failed_%s' % journal
    gdir = 'xml_%s' % journal
    if not os.path.isdir(DATADIR + fdir):
        os.mkdir(DATADIR + fdir)
    if not os.path.isdir(DATADIR + gdir):
        os.mkdir(DATADIR + gdir)
    failed = set(readxml(fdir))
    done = set(readxml(gdir))

    ASPB = {journal}  # , '0032-0889'}
    allpmid = failed | done
    with open(JCSV, 'r', encoding='utf8') as fp:
        R = csv.reader(fp)
        next(R)
        todo = {pmid: (doi, issn) for pmid, issn, name, year,
                doi in R if doi and issn in ASPB and pmid not in allpmid}

    print('%s: %d failed, %d done, %d todo' % (journal, len(failed), len(done), len(todo)))
    lst = sorted(todo.items(), key=lambda t: t[0])
    if mx > 0:
        lst = lst[:mx]
    for pmid, (doi, issn) in lst:
        resp = requests.get('https://doi.org/{}'.format(doi), headers=header)
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
            if not a:
                xml = b'failed-no-article'  # but there might be a full PDF! sigh!
                click.secho('failed %s doi=%s no article!' % (pmid, doi), fg='red')
                d = fdir
                failed.add(pmid)
            else:
                d = gdir
                done.add(pmid)

        with open(DATADIR + '{}/{}.html'.format(d, pmid), 'wb') as fp:
            fp.write(xml)

        del todo[pmid]
        print('%d failed, %d done, %d todo: %s' % (len(failed), len(done), len(todo), pmid))
        time.sleep(sleep)


class ASPB(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        a = root.select('div.article.fulltext-view')[0]
        assert a
        self.article = a

    def results(self):
        for s in self.article.select('div.section'):
            if 'results' in s.attrs['class']:
                return s
        for s in self.article.select('div.section'):
            n = s.find('h2')
            if n:
                txt = n.text.lower()
                if txt.find('methods') >= 0:
                    return s
        return None

    def methods(self):
        for s in self.article.select('div.section'):
            if 'materials-methods' in s.attrs['class']:
                return s
            if 'methods' in s.attrs['class']:
                return s
        for s in self.article.select('div.section'):
            n = s.find('h2')
            if n:
                txt = n.text.lower()
                if txt.find('methods') >= 0:
                    return s
        return None

    def abstract(self):
        for s in self.article.select('div.section'):
            if 'abstract' in s.attrs['class']:
                return s

        for s in self.article.select('div.section'):
            txt = s.find('h2').string.lower()
            if txt.find('abstract') >= 0:
                return s
        return None

    def tostr(self, sec):
        for a in sec.select('a.xref-bibr'):
            a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


def gen_aspb(journal):
    cc = set()
    if not os.path.isdir(DATADIR + 'cleaned_%s' % journal):
        os.mkdir(DATADIR + 'cleaned_%s' % journal)
    for pmid in readxml('xml_%s' % journal):
        print(pmid)
        fname = 'xml_{}/{}.html'.format(journal, pmid)
        with open(DATADIR + fname, 'rb') as fp:
            soup = BeautifulSoup(fp, 'html.parser')
        a = soup.select('div.article.fulltext-view')[0]
        for sec in a.select('div.section'):
            for c in sec.attrs['class']:
                cc.add(c)
            n = sec.find('h2')
            if n:
                txt = n.text  # .lower()
                cc.add(txt)
        e = ASPB(soup)
        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            print(pmid, '...missing: abs, methods, results:', a is None, m is None, r is None)
            continue
        fname = DATADIR + 'cleaned_{}/{}_cleaned.txt'.format(journal, pmid)
        if os.path.exists(fname):
            click.secho('overwriting %s' % fname, fg='red')

        with open(fname, 'w', encoding='utf-8') as fp:
            w = ' '.join(e.tostr(a))
            print('!~ABS~! %s' % w, file=fp)
            w = ' '.join(e.tostr(r))
            print('!~RES~! %s' % w, file=fp)
            w = ' '.join(e.tostr(m))
            print('!~MM~! %s' % w, file=fp)

    print(cc)


if __name__ == '__main__':
    download_aspb(sleep=60.*2, mx=0, journal='1040-4651')
    download_aspb(sleep=60.*2, mx=0, journal='0032-0889')
    download_aspb(sleep=60.*2, mx=0, journal='1532-298X') # web issn for the plant cell
    download_aspb(sleep=60.*2, mx=0, journal='1532-2548') # web issn for plant physiology
    gen_aspb(journal='1040-4651')
    gen_aspb(journal='0032-0889')
    gen_aspb(journal='1532-298X') # web issn for the plant cell
    gen_aspb(journal='1532-2548')
