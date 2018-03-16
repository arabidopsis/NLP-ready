import csv
import os
import re
import time
# import sys
import requests
import click
from lxml import etree
from io import BytesIO
from bs4 import BeautifulSoup


JCSV = 'journals.csv'


PMID_ELSEVIER = 'http://api.elsevier.com/content/article/pubmed_id/{}'
EKEY = '305ac4275ea475891668f6a71234efbc'
Headers = {'X-ELS-APIKey': EKEY}


def elsevier(pmid, url=PMID_ELSEVIER):
    """Given a PUBMED id return the Elsevier XML as text."""
    resp = requests.get(url.format(pmid),
                        headers=Headers,
                        params={'view': 'full'}  # Do we need this?
                        )

    # for row in Events().parse(BytesIO(resp.content),'elsevier'):
    #    print(row)#,end=' ')

    soup = BeautifulSoup(BytesIO(resp.content), "xml")
    if soup.find('service-error'):
        # print('no such document:', pmid, resp.text, file=sys.stderr)
        return None
    else:
        return resp.text
        # return soup.prettify()


def read_suba_papers_csv():
    """suba_papers.csv is a list of *all* pubmed ids from SUBA4."""
    # R = csv.reader(open('SUBA_Data4_JDK.csv', encoding='latin1'))
    R = csv.reader(open('suba_papers.csv', encoding='latin1'))
    next(R)
    # print(header)
    for row in R:
        # print(row)
        yield row


def readxml(d):
    """Scan directory d and return the pubmed ids."""
    for f in os.listdir(d):
        f, ext = os.path.splitext(f)
        if ext == '.xml':
            yield f


def download_elsevier(sleep=0.5, use_issn=False):
    """Download any Elsevier XML files using SUBA4 pubmed ids."""
    failed = set(readxml('failed_elsevier'))
    done = set(readxml('xml_elsevier'))  # | set(readxml('xml_epmc'))  # TODO: don't duplicate EPMC

    if use_issn:
        # find ISSN subset for Elsevier see https://www.elsevier.com/solutions/sciencedirect/content/journal-title-lists
        if not os.path.isfile('jnlactive.csv'):
            raise RuntimeError(
                'please download jnlactive.csv with: "wget https://www.elsevier.com/__data/promis_misc/sd-content/journals/jnlactive.csv"')
        ISSN = set()
        with open('jnlactive.csv', encoding='latin1') as fp:
            R = csv.reader(fp)
            next(R)
            for name, issn, product, history in R:
                assert len(issn) == 8, issn
                if '-' not in issn:
                    issn = issn[:4] + '-' + issn[4:]  # sigh!
                ISSN.add(issn)

        todo = []
        with open(JCSV) as fp:
            R = csv.reader(fp)
            next(R)
            for pmid, issn, name, year, doi in R:
                if issn in ISSN and pmid not in done and pmid not in failed:
                    todo.append(pmid)
    else:
        todo = [row[0].upper() for row in read_suba_papers_csv()
                if row[0].upper() not in (failed | done)]
    print('%d failed, %d done %s todo' % (len(failed), len(done), len(todo)))
    todox = todo.copy()
    for pmid in todo:

        xml = elsevier(pmid)
        if xml is None:
            d = 'failed_elsevier'
            xml = 'failed'
            failed.add(pmid)
        else:
            d = 'xml_elsevier'
            done.add(pmid)
        with open('{}/{}.xml'.format(d, pmid), 'w') as fp:
            fp.write(xml)
        todox.remove(pmid)
        print('%d failed, %d done %s todo %s' % (len(failed), len(done), len(todox), pmid))
        time.sleep(sleep)


def getxmlelsevier(pmid):
    parser = etree.XMLParser(ns_clean=True)
    with open('xml_elsevier/{}.xml'.format(pmid), 'rb') as fp:
        tree = etree.parse(fp, parser)

    root = tree.getroot()
    return root


E = '/e:full-text-retrieval-response'
ART = '*[self::ja:converted-article or self::ja:article]'

CE = 'http://www.elsevier.com/xml/common/dtd'
TAG = '{%s}%%s' % CE
XREFS = {TAG % 'cross-ref', TAG % 'cross-refs'}
ITALIC = {TAG % 'italic'}


def para2txt2(e):
    for t in e.xpath('.//text()'):
        p = t.getparent()
        if p.tag in XREFS:
            if p.tail == t:
                yield p.tail
            else:
                yield 'CITATION'  # '[%s]' % p.attrib['refid']
        elif p.tag in ITALIC and p.tail != t:
            # yield '<i>%s</i>' % t
            yield str(t)
        else:
            yield str(t)


class Elsevier(object):
    SPACE = re.compile(r'\s+', re.I)

    def __init__(self, root):
        self.root = root
        ns = root.nsmap.copy()
        ns['e'] = ns.pop(None)
        self.ns = ns

    def results(self):

        secs = self.root.xpath(E + '/e:originalText/xocs:doc/xocs:serial-item/' + ART + '/ja:body/ce:sections',
                               namespaces=self.ns)
        for sec in secs:
            for s in sec.xpath('./ce:section', namespaces=self.ns):
                for t in s.xpath('.//ce:section-title/text()', namespaces=self.ns):
                    if t.lower().find('results') >= 0:
                        return s

        return None

    def methods(self):

        secs = self.root.xpath(E + '/e:originalText/xocs:doc/xocs:serial-item/' + ART + '/ja:body/ce:sections',
                               namespaces=self.ns)
        for sec in secs:
            for s in sec.xpath('./ce:section', namespaces=self.ns):
                for t in s.xpath('.//ce:section-title/text()', namespaces=self.ns):
                    if t.lower().find('methods') >= 0:
                        return s

        return None

    def abstract(self):

        secs = self.root.xpath(E + '/e:originalText/xocs:doc/xocs:serial-item/' + ART + '/ja:head/ce:abstract/ce:abstract-sec',
                               namespaces=self.ns)
        if not secs:
            return None
        return secs[0]

    def tostr(self, r):
        for p in r.xpath('.//*[self::ce:para or self::ce:simple-para]', namespaces=self.ns):
            res = []
            for t in para2txt2(p):
                res.append(t)

            txt = ''.join(res)
            txt = self.SPACE.sub(' ', txt)
            yield txt.strip()


def gen_elsevier():
    """Convert Elsevier XML files into "cleaned" text files."""
    if not os.path.isdir('cleaned_elsevier'):
        os.mkdir('cleaned_elsevier')

    for pmid in readxml('xml_elsevier'):

        root = getxmlelsevier(pmid)
        e = Elsevier(root)

        a = e.abstract()
        m = e.methods()
        r = e.results()
        if a is None or m is None or r is None:
            click.secho('{}: missing: abs {}, methods {}, results {}'.format(
                pmid, a is None, m is None, r is None), fg='red')
            continue
        fname = 'cleaned_elsevier/{}_cleaned.txt'.format(pmid)
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
    download_elsevier(sleep=5.0, use_issn=False)
    gen_elsevier()
