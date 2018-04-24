from mlabc import Download, Clean, Generate


ISSN = {
    '1932-6203': 'PLoS ONE',
    '1553-7404': 'PLoS Genet.',
    "1545-7885": "PLoS Biol.",
    "1553-7374": "PLoS Pathog.",

}


class PLOS(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.article-text')
        assert a, a
        self.article = a[0]

    def results(self):
        secs = self.article.select('div.section.toc-section')
        for sec in secs:
            if self.find_title(sec, txt=['results and discussion', 'results', 'result']):
                return sec

        return None

    def methods(self):
        secs = self.article.select('div.section.toc-section')
        for sec in secs:
            if self.find_title(sec, txt=['materials & methods', 'materials and methods',
                                         'material and methods', 'methods']):  # spelling!
                return sec

        return None

    def abstract(self):
        secs = self.article.select('div.toc-section.abstract')
        return secs[0] if secs else None

    def tostr(self, sec):

        for a in sec.select('div.figure'):
            a.replace_with(self.newfig(a, caption='.figcaption'))
        for a in sec.select('span.equation'):  # e.g. math equations
            a.replace_with('[[EQUATION]]')
        for a in sec.select('span.inline-formula'):  # e.g. math equations
            a.replace_with('[[EQUATION]]')
        for a in sec.select('p a.ref-tip'):
            a.replace_with('CITATION')

        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


def download_plos(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = 'http://www.plosone.org'

        def check_soup(self, paper, soup, resp):
            a = soup.select('div.article-text')
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GeneratePLOS(Generate):
    def create_clean(self, soup, pmid):
        return PLOS(soup)


def gen_plos(issn):
    e = GeneratePLOS(issn)
    e.run()


def html_plos(issn):
    e = GeneratePLOS(issn)
    print(e.tohtml())


if __name__ == '__main__':
    download_plos(issn='1932-6203', sleep=60 * 2., mx=0)
    # html_plos(issn='1932-6203')
