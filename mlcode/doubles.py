import os
import csv
import glob
from collections import defaultdict
from tabulate import tabulate

DATADIR = '../data/'
JCSV = 'journals.csv'


def read_papers():
    with open(JCSV, 'r', encoding='utf8') as fp:
        R = csv.reader(fp)
        next(R)
        todo = {pmid: (doi, issn, int(year)) for pmid, issn, name, year, doi in R}
    return todo


def read_issn():

    ISSN = {}
    with open('jcounts.csv', 'r') as fp:
        R = csv.reader(fp)
        next(R)
        for issn, count, name, _, _ in R:
            ISSN[issn] = (int(count), name)
    return ISSN


def get_dir(xmld, ext='.xml'):
    res = []
    for f in glob.glob(DATADIR + '%s/*%s' % (xmld, ext)):
        _, fname = os.path.split(f)
        pmid, _ = os.path.splitext(fname)
        res.append(pmid)
    return res


def getext(xmld):
    if xmld.endswith(('epmc','elsevier')):
        return '.xml'
    return '.html'


def get_all_done():
    for xmld in glob.glob(DATADIR + 'xml_*'):
        _, issn = xmld.split('_')
        pmids = get_dir(xmld, ext=getext())
        for pmid in pmids:
            yield issn, pmid


def summary():
    issns = read_issn()
    dd = {}
    for xmld in glob.glob(DATADIR + 'xml_*'):
        _, issn = xmld.split('_')
        cnt, name = issns.get(issn, (0, issn))
        pmids = get_dir(xmld, ext=getext())
        dd[issn] = (name, issn, cnt, len(pmids), 0)

    for xmld in glob.glob(DATADIR + 'failed_*'):
        _, issn = xmld.split('_')
        pmids = get_dir(xmld, ext=getext())
        name, issn, cnt, n, _ = dd[issn]
        dd[issn] = (name, issn, cnt, n, len(pmids))

    res = sorted(dd.values(), key=lambda t: t[0])
    header = 'issn,count,done,failed,total,tname'.split(',')
    tbl = []
    tcnt = tdone = tfailed = 0
    for name, issn, cnt, done, failed in res:
        tbl.append((issn, cnt, done, failed, done + failed, name))
        tdone += done
        tfailed += failed
        tcnt += cnt
    tbl.append(['total', tcnt, tdone, tfailed, tdone + tfailed, ''])
    print(tabulate(tbl, headers=header, tablefmt='rst'))


def counts():
    ISSN = read_issn()
    res = defaultdict(list)
    for xmld in glob.glob(DATADIR + 'xml_*'):
        _, issn = xmld.split('_')
        for pmid in get_dir(xmld, ext=getext()):
            res[pmid].append(issn)

    print('done:', len(res))

    def d(issn):
        if issn in ISSN:
            return ISSN[issn][1]
        return issn

    for pmid in res:
        issns = res[pmid]
        if len(issns) > 1:
            print(pmid, [d(j) for j in issns])


def parsed():
    ISSN = {}
    res = defaultdict(list)
    for xmld in glob.glob(DATADIR + 'cleaned_*'):
        _, issn = xmld.split('_')
        for f in glob.glob(DATADIR + '%s/*.txt' % xmld):
            _, fname = os.path.split(f)
            pmid, _ = os.path.splitext(fname)
            pmid, _ = pmid.split('_')
            res[issn] = [pmid for fname in get_dir(xmld, ext='.txt')
                         for pmid in [fname.split('_')[0]]]

    print('done:', len(res))
    for pmid in res:
        issns = res[pmid]
        if len(issns) > 1:
            print(pmid, [ISSN.get(j, j) for j in issns])


if __name__ == '__main__':
    summary()
    # counts()
