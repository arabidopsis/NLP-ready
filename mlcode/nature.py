from io import BytesIO

from lxml import etree
from lxml.html import document_fromstring, parse

from mlabc import Clean, Config, Download, Generate, dump

ISSN = {
    "1476-4687": "Nature",
    "0028-0836": "Nature",
    "1748-7838": "Cell Res.",
    "1001-0602": "Cell Res.",
    "1465-7392": "Nat. Cell Biol.",
    "1476-4679": "Nat. Cell Biol.",
    "1087-0156": "Nat. Biotechnol.",
    "1350-9047": "Cell Death Differ.",
    "2041-1723": "Nat Commun",
    "2045-2322": "Sci Rep",
}


class Nature(Clean):
    MM = [
        './/section[@aria-labelledby="methods"]',
        # './/section[@aria-labelledby="methods-summary"]',
        './/section[@aria-labelledby="materials-and-methods"]',
        './/section[@aria-labelledby="material-and-methods"]',
    ]

    def __init__(self, root):
        super().__init__(root)
        # print(etree.tostring(root))
        a = root.xpath('.//div[@data-article-body="true"]')
        assert a and len(a) == 1, a
        self.article = a[0]

    def results(self):
        secs = self.article.xpath('.//section[@aria-labelledby="main"]')
        if secs:
            return secs[0]
        secs = self.article.xpath('.//section[@aria-labelledby="results"]')
        if secs:
            return secs[0]
        return None

    def methods(self):
        secs1 = None
        for t in self.MM:
            secs1 = self.article.xpath('.//section[@aria-labelledby="methods"]')
            if secs1:
                break

        secs2 = self.article.xpath('.//section[@aria-labelledby="methods-summary"]')
        secs3 = self.article.xpath('.//section[@aria-labelledby="online-methods"]')
        secs = secs1 + secs2 + secs3
        if len(secs) == 1:
            return secs[0]
        div = etree.Element("div")
        for sec in secs:
            for s in sec:
                div.append(s)
        return div

    def abstract(self):
        secs = self.article.xpath('.//section[@aria-labelledby="abstract"]')
        return secs[0] if secs else None

    def title(self):
        txt = "".join(self.root.xpath("/html/head/title/text()"))
        return txt.rsplit(" | ", 1)[0].strip()

    def tostr(self, sec):
        for fig in sec.xpath('.//div[@data-container-section="figure"]'):
            s = etree.Element("p")
            txt = " ".join(n or "" for n in fig.xpath(".//figcaption//text()"))
            s.text = self.FIGURE % txt
            s.tail = fig.tail  # important!
            fig.getparent().replace(fig, s)
        for sup in sec.xpath(".//sup"):
            n = sup.xpath('./a[starts-with(@aria-label,"Reference")]')
            if len(n) > 0:
                # for a in n:
                #     a.text = ' CITATION '
                s = etree.Element("span")
                # s.text = ' (CITATION x %d) ' % len(n)
                s.text = " (CITATION) "
                s.tail = sup.tail  # important!
                sup.getparent().replace(sup, s)
        txt = [
            self.SPACE.sub(" ", "".join(p.xpath(".//text()")))
            for p in sec.xpath(".//p")
        ]
        return txt


class GenerateNature(Generate):
    def create_clean(self, soup, pmid):
        return Nature(soup)

    def get_soup(self, gdir, pmid):
        fname = Config.DATADIR + gdir + "/{}.html".format(pmid)
        with open(fname, "r", encoding="utf-8") as fp:
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
        Referer = "https://www.nature.com"

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
            a = a or soup.xpath('.//section[@aria-labelledby="materials-and-methods"]')
            a = a or soup.xpath(
                './/section[@aria-labelledby="material-and-methods"]'
            )  # spelling?
            if not a:
                dump(paper, resp.content)
                return b"failed! no mm"
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_nature(issn):

    nature = GenerateNature(issn)
    print(nature.tohtml())


if __name__ == "__main__":
    download_nature(issn="1476-4687", sleep=10.0, mx=1)
    download_nature(issn="0028-0836", sleep=10.0, mx=1)
