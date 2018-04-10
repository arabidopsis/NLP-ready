import csv
import os
import re
# import gzip
import time
from collections import defaultdict
# import sys
import requests
import click
from lxml import etree
from io import BytesIO

from bs4 import BeautifulSoup

from mlabc import JCSV, read_pubmed_csv, read_suba_papers_csv


EFETCH = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id='

# html that is sent back by NIH
ERROR = re.compile('<ERROR>([^<]*)</ERROR>')


def fetchpubmed(session, id):
    """Fetch article metadata from NCBI using pubmed id."""
    resp = session.get(EFETCH + str(id))
    return resp.content  # need buffer for parsing


def parse_xml(xml):
    """Parse NCBI Journal metadata into a dictionary."""
    ipt = BytesIO(xml)
    tree = etree.parse(ipt)
    error = tree.getroot().tag
    if error == 'ERROR':  # no id
        return None
    article = tree.find('PubmedArticle/MedlineCitation/Article')
    if article is None:
        return None

    pmid = tree.findtext('PubmedArticle/MedlineCitation/PMID').strip()
    title = article.findtext('ArticleTitle')
    abstract = article.findtext('Abstract/AbstractText')
    authors = article.findall('AuthorList/Author')
    pages = article.findtext('Pagination/MedlinePgn')
    journal = article.find('Journal')

    name = journal.findtext('ISOAbbreviation', None) or journal.findtext('Title', '')
    volume = journal.findtext('JournalIssue/Volume')
    issue = journal.findtext('JournalIssue/Issue')
    year = journal.findtext('JournalIssue/PubDate/Year')
    year = year or journal.findtext('JournalIssue/PubDate/MedlineDate')
    year = year.strip()[:4]

    year = int(year)

    issn = journal.findtext('ISSN')
    issn = issn.strip() if issn else None

    data = tree.find('PubmedArticle/PubmedData')
    ids = data.findall('ArticleIdList/ArticleId')
    doi = [i.text.strip() for i in ids if i.get('IdType') == 'doi']
    if doi:
        doi = doi[0]
    else:
        doi = None

    pmcid = [i.text.strip() for i in ids if i.get('IdType') == 'pmc']
    if pmcid:
        pmcid = pmcid[0]
    else:
        pmcid = None

    # elementtree tries to encode everything as ascii
    # or if that fails it leaves the string alone
    # alist = [(a.findtext('LastName'), a.findtext('ForeName'), a.findtext('Initials'))
    #          for a in authors]
    alist = [(a.findtext('ForeName'), a.findtext('Initials'), a.findtext('LastName'))
             for a in authors]
    return {
        'pmid': pmid,
        'year': year,
        'title': title,
        'abstract': abstract,
        'authors': alist,
        'journal': name,
        'volume': volume,
        'issue': issue,
        'pages': pages,
        'doi': doi,
        'issn': issn,
        'pmcid': pmcid,
    }


def getmeta(csvfile, pubmeds, sleep=.2):
    """Create a CSV of (pmid, issn, name, year, doi, title) from list of SUBA4 pubmed ids."""
    # return data from xml file at NIH in a pythonic dictionary
    def pubmed_meta(session, id):
        xml = fetchpubmed(session, id)
        return parse_xml(xml)

    session = requests  # .Session()
    e = os.path.exists(pubmeds)
    if e:
        with open(pubmeds, 'r', encoding='utf8') as fp:
            R = csv.reader(fp)
            next(R)  # skip header
            done = {row[0] for row in R}
    else:
        done = set()
    print('%d done' % len(done))
    with open(pubmeds, 'a', encoding='utf8') as fp:
        W = csv.writer(fp)
        if not e:
            W.writerow(['pmid', 'issn', 'name', 'year', 'doi', 'pmcid', 'title'])
        for pmid in read_pubmed_csv(csvfile):
            if pmid not in done:
                m = pubmed_meta(session, pmid)
                if m is None:
                    click.secho('missing: %s' % pmid, fg='red')
                    W.writerow([pmid, 'missing-issn', '', '', '', '', ''])
                    continue
                assert pmid == m['pmid'], m
                W.writerow([pmid, m['issn'] or '', m['journal'],
                            str(m['year']), m['doi'] or '',
                            m['pmcid'] or '',
                            m['title']])
                done.add(pmid)
                print('%s: %d done' % (pmid, len(done)))
                if sleep:
                    time.sleep(sleep)  # be nice :)


def journal_summary():
    """Summarize journal statistics."""
    d = defaultdict(list)
    for p in read_suba_papers_csv():
        if p.doi:
            d[(p.issn, p.name)].append(p.doi)
    header = [['ISSN', 'count', 'journal', 'doi prefix', 'example doi']]
    ret = []
    for k in d:
        (issn, name) = k
        prefix = os.path.commonprefix(d[k])
        ret.append((issn, len(d[k]), name, prefix, d[k][-1]))

    ret = sorted(ret, key=lambda t: (-t[1], t[2]))
    # ret = sorted(ret, key=lambda t: t[2])
    for r in header + ret:
        print(','.join(str(x) for x in r))


HREF = re.compile(r'^/journal/.*/\(ISSN\)(.{4}-.{4})$')


def fetch_issn(href, session=None):
    session = session or requests
    resp = session.get('http://onlinelibrary.wiley.com' + href)
    soup = BeautifulSoup(BytesIO(resp.content), 'lxml')
    issn = soup.select('#issn')
    if not issn:
        return None
    return issn[0].text.strip()


def wiley_journals(start=0, session=None):
    session = session or requests
    resp = session.get('http://onlinelibrary.wiley.com/browse/publications',
                       params=dict(type='journal', start=start))
    soup = BeautifulSoup(BytesIO(resp.content), 'html.parser')
    journals = soup.select('#publications li div.details a')
    ret = []
    for j in journals:
        href = j.attrs['href']
        name = j.text.strip()
        m = HREF.match(href)
        if m:
            issn = m.group(1)
            ret.append((issn, name))
        else:
            issn = fetch_issn(href, session)
            if issn:
                ret.append((issn, name))
    return len(journals), ret


def get_wiley():
    start = 0
    res = {}
    session = requests.Session()
    while True:
        n, journals = wiley_journals(start=start, session=session)
        print('found', n, 'at ', start)

        if not journals:
            break
        start += n
        for issn, name in journals:
            res[issn] = name

    with open('wiley_journals.csv', 'w') as fp:
        W = csv.writer(fp)
        W.writerow(['name', 'issn'])
        for issn, name in sorted(res.items(), key=lambda t: t[1]):
            W.writerow([name, issn])
    return res


def get_all_cleaned():
    from glob import glob
    for folder in glob('cleaned_*'):
        for f in glob('{}/*_cleaned.txt'.format(folder)):
            _, fname = os.path.split(f)
            fname, _ = os.path.splitext(fname)
            pmid, _ = fname.split('_')
            yield folder, pmid


def wiley_issn():

    with open('wiley_journals.csv', 'r') as fp:
        R = csv.reader(fp)
        next(R)
        i2n = {issn: name for name, issn in R}
    ISSN = {}
    print('pmid,issn,journal,year,doi')
    for p in read_suba_papers_csv():
        if p.issn in i2n:
            ISSN[p.issn] = p.name
            print(','.join((p.pmid, p.issn, p.name, str(p.year), p.doi)))
    print(ISSN)


@click.group()
def cli():
    pass


@cli.command()
def summary():
    journal_summary()


@cli.command()
@click.option('--out', default=JCSV, help="output filename", show_default=True)
@click.option('--sleep', default=1., help='wait sleep seconds between requests', show_default=True)
@click.argument('csvfile')
def journals(csvfile, out, sleep=.2):
    """Create a CSV of (pmid, issn, name, year, doi, title) from list of SUBA4 pubmed ids."""
    getmeta(csvfile, sleep=sleep, pubmeds=out)


if __name__ == '__main__':
    cli()
