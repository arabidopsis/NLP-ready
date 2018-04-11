import csv
import os
import time
import click
from io import StringIO
from bs4 import BeautifulSoup

from mlabc import Clean, Generate, readxml, DownloadSelenium, DATADIR, read_suba_papers_csv, dump

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


ISSN = {
    '1097-4172': 'Cell',
    '0092-8674': 'Cell',
    '1090-2104': 'Biochem. Biophys. Res. Commun.',
    '0006-291X': 'Biochem. Biophys. Res. Commun.',
    '1873-2690': 'Plant Physiol. Biochem.',
    '0981-9428': 'Plant Physiol. Biochem.',
    '0960-9822': 'Curr. Biol.',
    '1879-0445': 'Curr. Biol.',
    '1752-9867': 'Mol Plant',
    '1674-2052': 'Mol Plant',
    '0378-1119': 'Gene',
    '1879-0038': 'Gene',
    '1873-3700': 'Phytochemistry',
    '0031-9422': 'Phytochemistry',
    '1876-7737': 'J Proteomics',
    '1873-2259': 'Plant Sci.',
    '1089-8638': 'J. Mol. Biol.',
    '0022-2836': 'J. Mol. Biol.',

    # added
    '0006-3002': 'Biochim. Biophys. Acta',
    '0171-9335': 'Eur. J. Cell Biol.',
    '1047-8477': 'J. Struct. Biol.',
    '1095-8657': 'J. Struct. Biol.',
    '1095-9998': 'Food Microbiol.',
    '1097-4164': 'Mol. Cell',
    '1360-1385': 'Trends Plant Sci.',
    '1522-4724': 'Mol. Cell Biol. Res. Commun.',
    '1618-1328': 'J. Plant Physiol.',
    "0176-1617": "J. Plant Physiol.",
    '1872-8278': 'Mitochondrion',
    '1873-3778': 'J Chromatogr A',

    # added
    "1096-0309": "Anal. Biochem.",
    "0003-9861": "Arch. Biochem. Biophys.",
    "0006-3495": "Biophys. J.",
    "1934-6069": "Cell Host Microbe",
    "1095-564X": "Dev. Biol.",
    "1534-5807": "Dev. Cell",
    "1090-2422": "Exp. Cell Res.",
    "1097-2765": "Mol. Cell",
    "1046-5928": "Protein Expr. Purif.",
    "0042-6822": "Virology",
    "1096-0341": "Virology",
    "1673-8527": "J Genet Genomics",



}


class DownloadCell(DownloadSelenium):

    def wait(self):

        w = super().wait()
        w.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'article div.Body section,div.fullText section')))
        return w

    def check_soup(self, paper, soup, resp):
        secs = soup.select('article div.Body section')
        if not secs:
            secs = soup.select('div.fullText section')
        if not secs:
            s = soup.select('h1.Head .title-text')
            if s:
                txt = s[0].text
                if 'WITHDRAWN' in txt:
                    return b'withdrawn'
        if len(secs) <= 3:
            dump(paper, resp.content)
        assert len(secs) > 3, (paper.pmid, paper.doi, secs)


def download_cell(issn, sleep=5.0, mx=0, headless=True, close=True):
    download = DownloadCell(issn, sleep=sleep, mx=mx, headless=headless, close=close)

    download.run()


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


def download_cell_old(issn, sleep=5.0, mx=0, headless=True, close=True):
    from selenium import webdriver
    # header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    #           ' (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
    #           'Referer': 'http://www.sciencedirect.com'
    #           }
    fdir = 'failed_%s' % issn
    gdir = 'xml_%s' % issn
    if not os.path.isdir(DATADIR + fdir):
        os.mkdir(DATADIR + fdir)
    if not os.path.isdir(DATADIR + gdir):
        os.mkdir(DATADIR + gdir)
    failed = set(readxml(fdir))
    done = set(readxml(gdir))

    ISSN = {issn}
    allpmid = failed | done
    todo = {p.pmid: p for p in read_suba_papers_csv(
    ) if p.doi and p.issn in ISSN and p.pmid not in allpmid}

    print('%s: %d failed, %d done, %d todo' % (issn, len(failed), len(done), len(todo)))
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


class CELL(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('article')
        assert a, a
        self.article = a[0]

    def results(self):

        secs = self.article.select('div.Body section')
        for sec in secs:
            if self.find_title(sec, op=lambda h2, b: h2.endswith(b),
                               txt=['results', 'results and discussion', 'results and discussions']):
                return sec
            if self.find_title(sec,
                               txt=['experimental']):
                return sec
        return None

    def methods(self):
        secs = self.article.select('div.Body section')
        for sec in secs:
            if self.find_title(sec, op=lambda h2, b: h2.endswith(b),
                               txt=['experimental procedures', 'materials and methods',
                                    'material and methods', 'methods']):
                return sec

        return None

    def abstract(self):
        secs = self.article.select('.Abstracts')
        return secs[0] if secs else None

    def title(self):
        t = self.article.select('.Head .title-text')
        if t:
            return t[0].text.strip()
        return super().title()

    def tostr(self, sec):
        for a in sec.select('p a.workspace-trigger'):
            if a.attrs['name'].startswith('bbib'):
                a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


class CELL2(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.fullText')

        a = a[0]
        assert a, a
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

    def title(self):
        for t in self.root.select('h1.articleTitle'):
            txt = t.text.strip()
            if txt:
                return txt
        return super().title()

    def tostr(self, sec):
        for a in sec.select('p span.bibRef'):

            a.replace_with('CITATION')
        for a in sec.select('div.floatDisplay'):
            p = self.root.new_tag('p')
            p.string = '[[FIGURE]]'
            a.replace_with(p)
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


class GenerateCell(Generate):
    def create_clean(self, soup, pmid):
        try:
            e = CELL(soup)
        except Exception:
            e = CELL2(soup)
        return e


def gen_cell(issn):
    e = GenerateCell(issn)
    e.run()


def html_cell(issn):
    e = GenerateCell(issn)
    print(e.tohtml())
    # fname = issn + '.html'
    # print('writing', fname)
    # with open(fname, 'w') as fp:
    #     fp.write(e.tohtml())


@click.group()
def cli():
    pass


DEFAULT = ','.join(ISSN)


@cli.command()
@click.option('--sleep', default=10., help='wait sleep seconds between requests', show_default=True)
@click.option('--mx', default=1, help='max documents to download 0=all')
@click.option('--head', default=False, is_flag=True, help='don\'t run browser headless')
@click.option('--noclose', default=False, is_flag=True, help='don\'t close browser at end')
@click.option('--issn', default=DEFAULT, show_default=True)
def download(sleep, mx, issn, head, noclose):
    for i in issn.split(','):
        driver = download_cell(issn=i, sleep=sleep, mx=mx, headless=not head, close=not noclose)
    if noclose:
        import code
        code.interact(local=locals())


@cli.command()
@click.option('--issn', default=DEFAULT, show_default=True)
def clean(issn):
    for i in issn.split(','):
        gen_cell(issn=i)


@cli.command()
@click.option('--issn', default=DEFAULT, show_default=True)
def html(issn):
    for i in issn.split(','):
        html_cell(issn=i)


@cli.command()
def issn():
    print(' '.join(ISSN))


if __name__ == '__main__':
    cli()

    # download_cell(issn='1097-4172', sleep=120., mx=0, headless=False)
    # download_cell(issn='0092-8674', sleep=120., mx=0, headless=False)
    # download_cell(issn='1873-2690', sleep=120., mx=0, headless=False)
    # download_cell(issn='0981-9428', sleep=120., mx=0, headless=False)
    # gen_cell(issn='1097-4172')
