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


def dump(pmid, xml):
    with open('dump_{}.html'.format(pmid), 'wb') as fp:
        fp.write(xml)


def download_springer(journal, sleep=5.0, mx=0):
    header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
              'Referer': 'https://link.springer.com'
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

    for idx, (pmid, (doi, issn, year)) in enumerate(lst):
        resp = requests.get('http://doi.org/{}'.format(doi), headers=header)
        if resp.status_code == 404:
            xml = b'failed404'
            d = fdir
            failed.add(pmid)
        else:
            resp.raise_for_status()
            header['Referer'] = resp.url
            xml = resp.content
            soup = BeautifulSoup(BytesIO(xml), 'lxml')
            a = soup.select('main#main-content article.main-body__content')
            if not a and year < 2005:
                dump(pmid, xml)
                d = fdir
                failed.add(pmid)
            else:
                assert a and len(a) == 1, (pmid, resp.url, doi)
                d = gdir
                done.add(pmid)

        with open(DATADIR + '{}/{}.html'.format(d, pmid), 'wb') as fp:
            fp.write(xml)

        del todo[pmid]
        print('%d failed, %d done, %d todo: %s %d' %
              (len(failed), len(done), len(todo), pmid, year))
        if sleep > 0 and idx < len(lst) - 1:
            time.sleep(sleep)


class Springer(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        a = root.select('main#main-content article.main-body__content')
        assert a
        self.article = a

    def results(self):
        secs = self.article.select('div.section.results-discussion')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            h2 = sec.find('h2')
            if h2 and h2.string.lower() == 'results':
                return sec
            if h2 and h2.string.lower() == 'results and discussion':
                return sec

        return None

    def methods(self):
        secs = self.article.select('div.section.methods')
        if not secs:
            secs = self.article.select('div.section.materials-methods')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            if sec.find('h2').text.lower() == 'materials and methods':
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


def gen_springer(journal):
    print(journal)
    with open(JCSV, 'r', encoding='utf8') as fp:
        R = csv.reader(fp)
        next(R)
        done = {pmid: doi for pmid, issn, name, year,
                doi in R if doi and issn == journal}

    if not os.path.isdir(DATADIR + 'cleaned_%s' % journal):
        os.mkdir(DATADIR + 'cleaned_%s' % journal)
    gdir = 'xml_%s' % journal
    for pmid in readxml(gdir):

        fname = DATADIR + gdir + '/{}.html'.format(pmid)
        with open(fname, 'rb') as fp:
            soup = BeautifulSoup(fp, 'html.parser')

        e = Springer(soup)
        # for s in e.article.select('div.section'):
        #     print(s.attrs)
        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            click.secho('{}: missing: abs {}, methods {}, results {} doi={}'.format(
                pmid, a is None, m is None, r is None, done[pmid]), fg='red')
            continue
        fname = DATADIR + 'cleaned_{}/{}_cleaned.txt'.format(journal, pmid)
        if os.path.exists(fname):
            click.secho('overwriting %s, %s' % (fname, done[pmid]), fg='yellow')
        else:
            print(pmid, done[pmid])

        with open(fname, 'w', encoding='utf-8') as fp:
            w = ' '.join(e.tostr(a))
            print('!~ABS~! %s' % w, file=fp)
            w = ' '.join(e.tostr(r))
            print('!~RES~! %s' % w, file=fp)
            w = ' '.join(e.tostr(m))
            print('!~MM~! %s' % w, file=fp)


if __name__ == '__main__':
    # download_springer(journal='1573-5028', sleep=10., mx=5)
    download_springer(journal='0167-4412', sleep=60. * 2, mx=0)
    # gen_pnas(journal='1573-5028')
    gen_springer(journal='0167-4412')
