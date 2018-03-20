import csv
import os
import re
import time
from collections import defaultdict
import requests
import click
from io import BytesIO
from bs4 import BeautifulSoup

DATADIR = '../data/'
JCSV = 'journals.csv'

OUP_ISSN = {'1460-2431': 'J. Exp. Bot.',
            '1471-9053': 'Plant Cell Physiol'
            }


def readxml(d):
    for f in os.listdir(DATADIR + d):
        f, ext = os.path.splitext(f)
        if ext == '.xml':
            yield f


def download_oup(journal, sleep=5.0, mx=0):
    header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
              'Referer': 'https://academic.oup.com'
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
            soup = BeautifulSoup(BytesIO(xml), 'html.parser')
            a = soup.select('div.article-body div.widget-items')
            assert a and len(
                a) == 1 and a[0].attrs['data-widgetname'] == "ArticleFulltext", (pmid, resp.url)  # no
            d = gdir
            done.add(pmid)

        with open(DATADIR + '{}/{}.xml'.format(d, pmid), 'wb') as fp:
            fp.write(xml)

        del todo[pmid]
        print('%d failed, %d done, %d todo: %s' % (len(failed), len(done), len(todo), pmid))
        if sleep > 0 and idx < len(lst) - 1:
            time.sleep(sleep)


class OUP(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        a = root.select('div.article-body div.widget-items')[0]
        assert a
        self.article = a
        objs = defaultdict(list)
        target = None
        for d in a.contents:
            if d.name == 'h2':
                target = d.text.lower().strip()
            elif d.name == 'section' and d.attrs['class'] == ['abstract']:
                target = 'abstract'
                for p in d.select('p'):
                    objs[target].append(p)
            elif d.name == 'p':
                if target:
                    objs[target].append(d)
        res = {}
        for k in objs:
            if k in {'abstract', 'results', 'materials and methods'}:
                res[k] = objs[k]
        self.resultsd = res

    def results(self):
        return self.resultsd.get('results')

    def methods(self):
        return self.resultsd.get('materials and methods')

    def abstract(self):
        return self.resultsd.get('abstract')

    def tostr(self, sec):
        for p in sec:
            for a in p.select('a.xref-bibr'):
                a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec]
        return txt


def gen_oup(journal):
    print(journal)
    if not os.path.isdir(DATADIR + 'cleaned_%s' % journal):
        os.mkdir(DATADIR + 'cleaned_%s' % journal)
    gdir = 'xml_%s' % journal
    for pmid in readxml(gdir):
        print(pmid)
        fname = DATADIR + gdir + '/{}.xml'.format(pmid)
        with open(fname, 'rb') as fp:
            soup = BeautifulSoup(fp, 'html.parser')
        e = OUP(soup)
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
    # download_oup(journal='1471-9053', sleep=60. *2, mx=0)
    download_oup(journal='0032-0781', sleep=60. * 2, mx=0)
    # gen_oup(journal='1471-9053')
    # gen_oup(journal='0032-0781')
