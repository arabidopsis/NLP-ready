import csv
import os
import re
import sys
import time
import requests
import click
from selenium import webdriver
from io import StringIO
from bs4 import BeautifulSoup


DATADIR = '../data/'
JCSV = 'journals.csv'


def getpage(doi, driver):

    driver.get('http://doi.org/{}'.format(doi))

    h = driver.find_element_by_tag_name('html')
    txt = h.get_attribute('outerHTML')
    soup = BeautifulSoup(StringIO(txt), 'lxml')
    secs = soup.select('article div.Body section')
    if not secs:
        secs = soup.select('div.fullText section')
    assert len(secs) > 3, (doi, secs)

    return txt


def readxml(d):
    for f in os.listdir(DATADIR + d):
        f, ext = os.path.splitext(f)
        if ext == '.html':
            yield f


def dump(pmid, xml):
    with open('dump_{}.html'.format(pmid), 'wb') as fp:
        fp.write(xml)


def download_cell(journal, sleep=5.0, mx=0, headless=True, close=True):
    # header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    #           ' (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
    #           'Referer': 'http://www.sciencedirect.com'
    #           }
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
        todo = {pmid: (doi, issn) for pmid, issn, name, year,
                doi in R if doi and issn in ISSN and pmid not in allpmid}

    print('%s: %d failed, %d done, %d todo' % (journal, len(failed), len(done), len(todo)))
    lst = sorted(todo.items(), key=lambda t: t[0])
    if mx > 0:
        lst = lst[:mx]
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('headless')
    # https://blog.miguelgrinberg.com/post/using-headless-chrome-with-selenium
    driver = webdriver.Chrome(chrome_options=options)
    for idx, (pmid, (doi, issn)) in enumerate(lst):
        print(pmid, doi)
        xml = getpage(doi, driver)
        # session = requests.Session()
        # resp = session.get('http://doi.org/{}'.format(doi), headers=header)
        # if resp.status_code == 404:
        #     xml = b'failed404'
        #     d = fdir
        #     failed.add(pmid)
        # else:
        #     resp.raise_for_status()
        #     header['Referer'] = resp.url
        #     xml = resp.content
        # soup = BeautifulSoup(StringIO(xml), 'lxml')
        # a = soup.select('article div.Abstracts')
        #     if not a:
        #         m = soup.select('meta[http-equiv="REFRESH"]')
        #         if m:
        #             c = m[0].attrs['content']
        #             c = c.split(';')[-1].strip()
        #             _, c = c.split('=', 1)
        #             c = c[1:-1]
        #             p = urlparse(resp.url)
        #             c = '%s://%s%s' % (p.scheme, p.netloc, c)
        #             resp = session.get(c, headers=header)
        #             xml = resp.content
        #             soup = BeautifulSoup(BytesIO(xml), 'lxml')
        #             a = soup.select('article div.Abstracts')
        #         if not m or not a:
        #             print('failed', resp.url, file=sys.stderr)
        #             dump(pmid, xml)
        # assert a and len(a) == 1, (pmid, len(a), doi)
        d = gdir
        done.add(pmid)

        with open(DATADIR + '{}/{}.html'.format(d, pmid), 'w') as fp:
            fp.write(xml)

        del todo[pmid]
        print('%d failed, %d done, %d todo: %s' % (len(failed), len(done), len(todo), pmid))
        if sleep > 0 and idx < len(lst) - 1:
            time.sleep(sleep)
    if close:
        driver.close()
    else:
        return driver


class CELL(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        a = root.select('article')

        a = a[0]
        assert a
        self.article = a

    def results(self):

        secs = self.article.select('div.Body section')
        for sec in secs:
            h2 = sec.find('h2')
            if h2 and h2.text.lower() == 'results':
                return sec
        return None

    def methods(self):
        secs = self.article.select('div.Body section')
        for sec in secs:
            h2 = sec.find('h2')
            if h2 and h2.text.lower() == 'experimental procedures':
                return sec
        return None

    def abstract(self):
        secs = self.article.select('.Abstracts')
        return secs[0] if secs else None

    def tostr(self, sec):
        for a in sec.select('p a.workspace-trigger'):
            if a.attrs['name'].startswith('bbib'):
                a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


class CELL2(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        a = root.select('div.fullText')

        a = a[0]
        assert a
        self.article = a

    def results(self):
        secs = self.article.select('section')
        for sec in secs:
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt == 'results' or txt == 'results and discussion':
                    return sec
        return None

    def methods(self):
        secs = self.article.select('section')
        for sec in secs:
            h2 = sec.find('h2')
            if h2 and h2.text.lower() == 'experimental procedures':
                return sec
        return None

    def abstract(self):
        secs = self.article.select('section.abstract')
        for sec in secs:
            return sec
        return None

    def tostr(self, sec):
        for a in sec.select('p span.bibRef'):

            a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


def gen_cell(journal):
    print(journal)
    if not os.path.isdir(DATADIR + 'cleaned_%s' % journal):
        os.mkdir(DATADIR + 'cleaned_%s' % journal)
    gdir = 'xml_%s' % journal
    for pmid in readxml(gdir):

        fname = DATADIR + gdir + '/{}.html'.format(pmid)
        with open(fname, 'rb') as fp:
            soup = BeautifulSoup(fp, 'lxml')

        try:
            e = CELL(soup)
        except Exception:
            e = CELL2(soup)
            click.secho('cell2', fg='yellow')
        # for s in e.article.select('div.section'):
        #     print(s.attrs)
        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            click.secho('{} {}: missing: abs {}, methods {}, results {}'.format(
                pmid, journal, a is None, m is None, r is None), fg='red')
            continue
        fname = DATADIR + 'cleaned_{}/{}_cleaned.txt'.format(journal, pmid)
        if os.path.exists(fname):
            click.secho('overwriting %s' % fname, fg='yellow')
        else:
            print(pmid)

        with open(fname, 'w', encoding='utf-8') as fp:
            w = ' '.join(e.tostr(a))
            print('!~ABS~! %s' % w, file=fp)
            w = ' '.join(e.tostr(r))
            print('!~RES~! %s' % w, file=fp)
            w = ' '.join(e.tostr(m))
            print('!~MM~! %s' % w, file=fp)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--sleep', default=10.)
@click.option('--mx', default=1)
@click.option('--head', default=False, is_flag=True)
@click.option('--noclose', default=False, is_flag=True)
@click.option('--issn', default='1097-4172,0092-8674', show_default=True)
def download(sleep, mx, issn, head, noclose):
    for i in issn.split(','):
        driver = download_cell(journal=i, sleep=sleep, mx=mx, headless=not head, close=not noclose)
    if noclose:
        import code
        code.interact(local=locals())


@cli.command()
@click.option('--issn', default='1097-4172,0092-8674', show_default=True)
def clean(issn):
    for i in issn.split(','):
        gen_cell(journal=i)


if __name__ == '__main__':
    cli()

    # download_cell(journal='1097-4172', sleep=10., mx=1)
    # gen_cell(journal='1097-4172')
