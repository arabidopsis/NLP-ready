import os
import glob
from collections import defaultdict, Counter
from tabulate import tabulate
import click

from mlabc import DATADIR, read_issn, read_suba_papers_csv


def get_dir(xmld, ext='.xml'):
    res = []
    for f in glob.glob(DATADIR + '%s/*%s' % (xmld, ext)):
        _, fname = os.path.split(f)
        pmid, _ = os.path.splitext(fname)
        res.append(pmid)
    return res


def getext(xmld):
    if xmld.endswith(('epmc', 'elsevier')):
        return '.xml'
    return '.html'


def get_all_done():
    for xmld in glob.glob(DATADIR + 'xml_*'):
        _, issn = xmld.split('_')
        pmids = get_dir(xmld, ext=getext(xmld))
        for pmid in pmids:
            yield issn, pmid


def _summary(showall=True):
    issns = read_issn()
    dd = {}
    for xmld in glob.glob(DATADIR + 'xml_*'):
        _, issn = xmld.split('_')
        cnt, name = issns.get(issn, (0, issn))
        pmids = get_dir(xmld, ext=getext(xmld))
        dd[issn] = (name, issn, cnt, len(pmids), 0)

    for xmld in glob.glob(DATADIR + 'failed_*'):
        _, issn = xmld.split('_')
        pmids = get_dir(xmld, ext=getext(xmld))
        name, issn, cnt, n, _ = dd[issn]
        dd[issn] = (name, issn, cnt, n, len(pmids))

    if showall:
        for issn in issns:
            if issn not in dd:
                cnt, name = issns[issn]
                dd[issn] = (name, issn, cnt, 0, 0)

    header = 'issn,count,done,failed,total,todo,tname'.split(',')
    tbl = []
    tcnt = tdone = tfailed = 0
    for name, issn, cnt, done, failed in dd.values():
        tbl.append((issn, cnt, done, failed, done + failed, cnt - (done + failed), name))
        tdone += done
        tfailed += failed
        tcnt += cnt
    tbl = sorted(tbl, key=lambda t: -t[5])
    tbl.append(['total', tcnt, tdone, tfailed, tdone + tfailed, '', ''])
    print(tabulate(tbl, headers=header, tablefmt='rst'))


def _counts():
    ISSN = read_issn()
    papers = {p.pmid for p in read_suba_papers_csv() if p.doi}  # papers with doi
    res = defaultdict(list)
    for xmld in glob.glob(DATADIR + 'xml_*'):
        _, issn = xmld.split('_')
        for pmid in get_dir(xmld, ext=getext(xmld)):
            res[pmid].append(issn)

    print('done:', len(res), 'possible', len(papers))

    def d(issn):
        if issn in ISSN:
            return ISSN[issn][1]
        return issn

    for pmid in res:
        issns = res[pmid]
        if len(issns) > 1:
            print(pmid, [d(j) for j in issns])


def _todo():
    issns = read_issn()
    papers = {p.pmid: p for p in read_suba_papers_csv() if p.doi}  # papers with doi

    for xmld in glob.glob(DATADIR + 'xml_*'):
        _, issn = xmld.split('_')
        cnt, name = issns.get(issn, (0, issn))
        pmids = get_dir(xmld, ext=getext(xmld))
        for pmid in pmids:
            if pmid in papers:
                del papers[pmid]

    # for xmld in glob.glob(DATADIR + 'failed_*'):
    #     _, issn = xmld.split('_')
    #     pmids = get_dir(xmld, ext=getext(xmld))
    #     for pmid in pmids:
    #         if pmid in papers:
    #             del papers[pmid]

    ISSN = Counter()
    for pmid, p in papers.items():
        ISSN[p.issn] += 1

    header = ["ISSN", "Journal", "ToDo"]
    tbl = []
    for issn, cnt in reversed(sorted(ISSN.items(), key=lambda t: t[1])):
        tbl.append([issn, issns[issn][1], cnt])
    print(tabulate(tbl, headers=header, tablefmt="rst"))


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


@click.group()
def cli():
    pass


@cli.command()
@click.option('--showall', is_flag=True, help='show journals not done yet')
def summary(showall):
    _summary(showall)


@cli.command()
def counts():
    _counts()


@cli.command()
def todo():
    _todo()


if __name__ == '__main__':
    cli()
    # counts()
