import csv
import os
import gzip
import time
# import sys
import requests
# import click
from lxml import etree

from mlabc import DATADIR, readxml, Generate, Clean, read_suba_papers_csv


ISSN = {'epmc': 'epmc'}


XML = 'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'  # noqa: E221


def epmc(pmcid, session=None):
    """Given a PUBMED id return the Europmc XML as text."""
    url = XML.format(pmcid=pmcid)
    resp = (session or requests).get(url)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    txt = resp.text

    # ipt = BytesIO(resp.content)
    # t = etree.parse(ipt)
    # txt = etree.tostring(t, pretty_print=True, encoding='unicode')
    return txt


def download_epmc(issn='epmc', sleep=0.5, mx=0):
    """Download any EuroPMC XML files using SUBA4 pubmed ids."""
    failed = set(readxml('failed_epmc'))
    done = set(readxml('xml_epmc'))
    session = requests.Session()

    pmids = set()
    for p in read_suba_papers_csv():
        pmid = p.pmid
        if not pmid:
            continue
        if pmid in failed or pmid in done:
            continue

        pmids.add(pmid)

    print('%d failed, %d done, %d todo' % (len(failed), len(done), len(pmids)))
    if not pmids:
        return

    p2mc = getpmcids(pmids)

    for pmid in pmids:
        if pmid not in p2mc:
            d = 'failed_epmc'
            xml = 'nopmcid'
            failed.add(pmid)
            txt = 'nopmcid'
        else:
            pmcid = p2mc[pmid]

            xml = epmc(pmcid, session=session)
            if xml is None:
                d = 'failed_epmc'
                xml = 'failed'
                failed.add(pmid)
                txt = 'failed'
            else:
                d = 'xml_epmc'
                txt = 'ok'
                done.add(pmid)

        with open(DATADIR + '{}/{}.xml'.format(d, pmid), 'w') as fp:
            fp.write(xml)

        print('%d failed (%s), %d done' % (len(failed), txt, len(done)))
        if txt != 'nopmcid':
            time.sleep(sleep)


def getxmlepmc(pmid):
    parser = etree.XMLParser(ns_clean=True)
    with open(DATADIR + 'xml_epmc/{}.xml'.format(pmid), 'rb') as fp:
        tree = etree.parse(fp, parser)

    root = tree.getroot()
    return root


TRANS = 'translate(text(),"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")'

EXREFS = {'xref'}

EITALIC = {'i'}


def para2txt3(e):
    for t in e.xpath('.//text()'):
        p = t.getparent()
        if p.tag in EXREFS:
            if p.tail == t:
                yield p.tail
            else:
                yield 'CITATION'  # '[%s]' % p.attrib['rid']
        elif p.tag in EITALIC and p.tail != t:
            # yield '<i>%s</i>' % t
            yield str(t)
        else:
            yield str(t)


class EPMC(Clean):

    def __init__(self, root):
        self.root = root

    def title(self):
        res = self.root.xpath('/article/front/article-meta/title-group/article-title')
        if not res:
            return None
        t = res[0]
        txt = ' '.join(t.xpath('.//text()'))
        return txt.strip()

    def abstract(self):
        res = self.root.xpath('/article/front/article-meta/abstract')
        if not res:
            return None
        return res[0]

    def methods(self):
        mm = self.root.xpath('/article/body/sec[@sec-type="methods"]')
        if not mm:
            mm = self.root.xpath('/article/body/sec/title[contains(' + TRANS + ',"methods")]/..')
        if not mm:
            mm = self.root.xpath(
                '/article/body/sec/title[contains(' + TRANS + ',"experimental")]/..')
        if not mm:
            return None
        return mm[0]

    def results(self):
        res = self.root.xpath('/article/body/sec/title[contains(' + TRANS + ',"results")]/..')
        if not res:
            return None
        return res[0]

    def tostr(self, r):
        for p in r.xpath('.//p'):
            res = []
            for t in para2txt3(p):
                res.append(t)

            txt = ''.join(res)
            txt = self.SPACE.sub(' ', txt)
            yield txt.strip()


# PMC ids at ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/ see https://www.ncbi.nlm.nih.gov/pmc/pmctopmid/

def pmc_subset():
    """Create a PMCID subset from PMC-ids.csv.gz."""
    pmids = set(p.pmid for p in read_suba_papers_csv())
    with open('PMC-ids-partial.csv', 'w') as out:
        W = csv.writer(out)
        W.writerow(['pmid', 'pmcid'])
        with gzip.open('PMC-ids.csv.gz', 'rt') as fp:
            R = csv.reader(fp)
            next(R)  # skip header
            for row in R:
                pmcid, pmid = row[8:10]
                if pmcid and pmid in pmids:
                    W.writerow([pmid, pmcid])


def getpmcids(pmids):
    """Map pubmed ids to the "open access" fulltext PMC ids."""
    ret = {}
    pmids = set(pmids)
    if os.path.exists('PMC-ids-partial.csv'):
        with open('PMC-ids-partial.csv', 'r') as fp:
            R = csv.reader(fp)
            next(R)
            for pmid, pmcid in R:
                ret[pmid] = pmcid

        return ret

    if not os.path.exists('PMC-ids.csv.gz'):
        raise RuntimeError(
            'please download PMC-ids.csv.gz (~85MB) file with: "wget ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz"')
    with gzip.open('PMC-ids.csv.gz', 'rt') as fp:
        R = csv.reader(fp)
        next(R)  # skip header
        for row in R:
            pmcid, pmid = row[8:10]
            if pmcid and pmid in pmids:
                assert pmid not in ret, pmid
                ret[pmid] = pmcid

    return ret


class GenerateEPMC(Generate):
    def create_clean(self, soup, pmid):
        return EPMC(soup)

    def get_soup(self, gdir, pmid):
        return getxmlepmc(pmid)


def gen_epmc(issn='epmc'):
    o = GenerateEPMC(issn)
    o.run()


# def gen_epmc_old(issn='epmc'):
#     """Convert EPMC XML files into "cleaned" text files."""
#     if not os.path.isdir(DATADIR + 'cleaned_epmc'):
#         os.mkdir(DATADIR + 'cleaned_epmc')
#     for pmid in readxml('xml_epmc'):
#
#         root = getxmlepmc(pmid)
#         e = EPMC(root)
#
#         a = e.abstract()
#         m = e.methods()
#         r = e.results()
#         if a is None or m is None or r is None:
#             click.secho('{}: missing: abs {}, methods {}, results {}'.format(
#                 pmid, a is None, m is None, r is None), fg='red')
#             continue
#         fname = DATADIR + 'cleaned_epmc/{}_cleaned.txt'.format(pmid)
#         if os.path.exists(fname):
#             click.secho('overwriting %s' % fname, fg='yellow')
#
#         with open(fname, 'w', encoding='utf-8') as fp:
#             w = ' '.join(e.tostr(a))
#             print('!~ABS~! %s' % w, file=fp)
#             w = ' '.join(e.tostr(r))
#             print('!~RES~! %s' % w, file=fp)
#             w = ' '.join(e.tostr(m))
#             print('!~MM~! %s' % w, file=fp)


def html_epmc(issn='epmc'):

    e = GenerateEPMC(issn)
    print(e.tohtml())


if __name__ == '__main__':
    # download_epmc(sleep=2.0)
    # gen_epmc()
    pmc_subset()
    # html_epmc(issn='epmc')
