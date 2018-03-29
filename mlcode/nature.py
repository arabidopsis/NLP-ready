from lxml import etree
from io import BytesIO
from lxml.html import parse, document_fromstring

from mlabc import Clean, Download, Generate, DATADIR


ISSN = {
    '1476-4687': 'Nature',
    '0028-0836': 'Nature'
}


class Nature(Clean):

    def __init__(self, root):
        self.root = root
        # print(etree.tostring(root))
        a = root.xpath('.//div[@data-article-body="true"]')
        assert a and len(a) == 1, a
        self.article = a[0]

    def results(self):
        secs = self.article.xpath('.//section[@aria-labelledby="main"]')
        return secs[0] if secs else None

    def methods(self):
        secs1 = self.article.xpath('.//section[@aria-labelledby="methods"]')

        secs2 = self.article.xpath('.//section[@aria-labelledby="methods-summary"]')
        secs3 = self.article.xpath('.//section[@aria-labelledby="online-methods"]')
        secs = secs1 + secs2 + secs3
        if len(secs) == 1:
            return secs[0] if secs else None
        div = etree.Element('div')
        for sec in secs:
            for s in sec:
                div.append(s)
        return div

    def abstract(self):
        secs = self.article.xpath('.//section[@aria-labelledby="abstract"]')
        return secs[0] if secs else None

    def title(self):
        txt = ''.join(self.root.xpath('/html/head/title/text()'))
        return txt.rsplit(' | ', 1)[0].strip()

    def tostr(self, sec):
        for fig in sec.xpath('.//div[@data-container-section="figure"]'):
            s = etree.Element('p')
            s.text = '[[FIGURE]]'
            s.tail = fig.tail
            fig.getparent().replace(fig, s)
        for sup in sec.xpath('.//sup'):
            n = sup.xpath('./a[starts-with(@aria-label,"Reference")]')
            if len(n) > 0:
                # for a in n:
                #     a.text = ' CITATION '
                s = etree.Element('span')
                s.text = ' (CITATION x %d) ' % len(n)
                s.tail = sup.tail
                sup.getparent().replace(sup, s)
        txt = [self.SPACE.sub(' ', ''.join(p.xpath('.//text()'))) for p in sec.xpath('.//p')]
        return txt


class GenerateNature(Generate):
    def create_clean(self, soup, pmid):
        return Nature(soup)

    def get_soup(self, gdir, pmid):
        fname = DATADIR + gdir + '/{}.html'.format(pmid)
        with open(fname, 'r', encoding='utf-8') as fp:
            # tree = parse(fp)
            # soup = tree.getroot()
            txt = fp.read()
            soup = document_fromstring(txt)

        return soup


def gen_nature(issn):

    nature = GenerateNature(issn)
    nature.run()


def download_nature(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'https://www.nature.com'

        def create_soup(self, paper, resp):
            # parser = etree.XMLParser(ns_clean=True)
            tree = parse(BytesIO(resp.content))
            return tree.getroot()

        def check_soup(self, paper, soup, resp):
            # print(etree.tostring(soup))
            a = soup.xpath('.//section[@aria-labelledby="abstract"]')
            assert a and len(a) == 1, (paper.pmid, resp.url)
            a = soup.xpath('.//section[@aria-labelledby="methods"]')
            a = a or soup.xpath('.//section[@aria-labelledby="methods-summary"]')
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_nature(issn):

    nature = GenerateNature(issn)
    print(nature.tohtml())


if __name__ == '__main__':
    download_nature(issn='1476-4687', sleep=120., mx=0)
    download_nature(issn='0028-0836', sleep=120., mx=0)
    # gen_gad(issn='0890-9369')
