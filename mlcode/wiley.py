import csv
import os
import re
import time
import requests
import click
from io import BytesIO
from bs4 import BeautifulSoup

JCSV = 'journals.csv'

# generated from downloads.py:wiley_issn()
# only gives online version for Plant J. !!!!
WILEY_ISSN = {'1460-2075': 'EMBO J.', '1399-3054': 'Physiol Plant',
              '1365-313X': 'Plant J.', '1600-0854': 'Traffic',
              '0960-7412': 'Plant J.',  # added by hand
              '1467-7652': 'Plant Biotechnol. J.', '1469-8137': 'New Phytol.',
              '1469-3178': 'EMBO Rep.', '1873-3468': 'FEBS Lett.',
              '1567-1364': 'FEMS Yeast Res.', '1522-2683': 'Electrophoresis',
              '1744-7909': 'J Integr Plant Biol', '1742-4658': 'FEBS J.',
              '1744-4292': 'Mol. Syst. Biol.', '1364-3703': 'Mol. Plant Pathol.',
              '1365-2591': 'Int Endod J', '1615-9861': 'Proteomics',
              '1365-3040': 'Plant Cell Environ.'}


def readxml(d):
    for f in os.listdir(d):
        f, ext = os.path.splitext(f)
        if ext == '.xml':
            yield f


def download_wiley(journal, sleep=5.0, mx=0):
    header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
              'Referer': 'http://onlinelibrary.wiley.com'
              }
    fdir = 'failed_%s' % journal
    gdir = 'xml_%s' % journal
    if not os.path.isdir(fdir):
        os.mkdir(fdir)
    if not os.path.isdir(gdir):
        os.mkdir(gdir)
    failed = set(readxml(fdir))
    done = set(readxml(gdir))

    ISSN = {journal}
    allpmid = failed | done
    with open(JCSV, 'r', encoding='utf8') as fp:
        R = csv.reader(fp)
        next(R)
        todo = {pmid: (doi, issn) for pmid, issn, name, year,
                doi in R if doi and issn in ISSN and pmid not in allpmid}

    print('%s: %d failed, %d done, %d todo' % (WILEY_ISSN.get(journal, journal), len(failed), len(done), len(todo)))
    if not todo:
        return
    lst = sorted(todo.items(), key=lambda t: t[0])
    if mx > 0:
        lst = lst[:mx]
    nn = 0
    for pmid, (doi, issn) in lst:
        url = 'http://onlinelibrary.wiley.com/doi/{}/full'.format(doi)
        resp = requests.get(url, headers=header)
        if resp.status_code == 404:
            xml = b'failed404'
            d = fdir
            failed.add(pmid)
        else:
            resp.raise_for_status()
            header['Referer'] = resp.url
            xml = resp.content
            soup = BeautifulSoup(BytesIO(xml), 'html.parser')
            a = soup.select('article.journal article.issue article.article')
            assert a and len(a) == 1, (pmid, resp.text)
            d = gdir
            done.add(pmid)

        with open('{}/{}.xml'.format(d, pmid), 'wb') as fp:
            fp.write(xml)

        del todo[pmid]
        print('%d failed, %d done, %d todo: %s' % (len(failed), len(done), len(todo), pmid))
        nn += 1
        if sleep > 0 and nn < len(lst) - 1:
            time.sleep(sleep)


class Wiley(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        a = root.select('article.journal article.issue article.article')[0]
        assert a
        self.article = a

    def results(self):
        for sec in self.article.select('section.article-body-section'):
            h2 = sec.find('h2')
            if h2 and h2.string.lower() == 'results':
                return sec

        return None

    def methods(self):
        for sec in self.article.select('section.article-body-section'):
            h2 = sec.find('h2')
            if h2 and h2.string.lower() == 'experimental procedures':
                return sec

        return None

    def abstract(self):
        for s in self.article.select('section.article-section--abstract'):
            if 'abstract' == s.attrs['id']:
                return s
        return None

    def tostr(self, sec):
        for a in sec.select('p a[title="Link to bibliographic citation"]'):
            a.replace_with('CITATION')

        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


def gen_wiley(journal):
    print(journal)
    if not os.path.isdir('cleaned_%s' % journal):
        os.mkdir('cleaned_%s' % journal)
    gdir = 'xml_%s' % journal
    for pmid in readxml(gdir):
        print(pmid)
        fname = gdir + '/{}.xml'.format(pmid)
        with open(fname, 'rb') as fp:
            soup = BeautifulSoup(fp, 'html.parser')
        e = Wiley(soup)
        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            click.secho('{}: missing: abs {}, methods {}, results {}'.format(
                pmid, a is None, m is None, r is None), fg='red')
            continue
        fname = 'cleaned_{}/{}_cleaned.txt'.format(journal, pmid)
        if os.path.exists(fname):
            click.secho('overwriting %s' % fname, fg='yellow')

        with open(fname, 'w', encoding='utf-8') as fp:
            w = ' '.join(e.tostr(a))
            print('!~ABS~! %s' % w, file=fp)
            w = ' '.join(e.tostr(r))
            print('!~RES~! %s' % w, file=fp)
            w = ' '.join(e.tostr(m))
            print('!~MM~! %s' % w, file=fp)


def download_all(sleep=10., mx=5):
    for issn in WILEY_ISSN:
        download_wiley(journal=issn, sleep=sleep, mx=mx)


if __name__ == '__main__':
    # download_wiley(journal='0960-7412', sleep=20., mx=50)
    # download_wiley(journal='1467-7652', sleep=10., mx=5)
    download_wiley(journal='1365-313X', sleep=10., mx=20)

    # gen_wiley(journal='0960-7412')
    # gen_wiley(journal='1467-7652')
    gen_wiley(journal='1365-313X')
