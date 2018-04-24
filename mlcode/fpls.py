from collections import defaultdict
from mlabc import Clean, Download, Generate


ISSN = {
    '1664-462X': 'Front Plant Sci',
    "2296-634X": "Front Cell Dev Biol",
}


class FPLS(Clean):

    def __init__(self, root):
        self.root = root
        a = self.root.select('div.article-section div.JournalFullText')
        assert a, a
        self.article = a[0]
        self.search()

    def search(self):

        objs = defaultdict(list)
        target = None
        for d in self.article.contents:
            if d.name == 'h2':
                target = d.text.lower().strip()
            elif d.name == 'p':
                if target:
                    objs[target].append(d)
            elif d.name == 'div' and 'FigureDesc' in d['class']:
                if target:
                    p = self.newfig(d, caption='p')
                    d.replace_with(p)
                    objs[target].append(p)

        res = {}
        sections = {'results', 'materials and methods', 'results and discussion',
                    'material and methods'}  # spelling!
        for k in objs:
            if k in sections:
                res[k] = objs[k]
        # assert set(res) == sections, (set(res))
        self.resultsd = res

    def results(self):
        return self.resultsd.get('results') or self.resultsd.get('results and discussion')

    def methods(self):
        return self.resultsd.get('materials and methods') or self.resultsd.get('material and methods')

    def abstract(self):
        secs = self.root.select('div.article-section div.JournalAbstract p')
        return secs if secs else None

    def title(self):
        return self.root.select('div.article-section div.JournalAbstract h1')[0].text.strip()

    def tostr(self, secs):
        for p in secs:
            for a in p.select('a'):
                href = a.attrs.get('href')
                if href and href.startswith('#B'):
                    a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in secs]
        return txt


class GenerateFPLS(Generate):
    def create_clean(self, soup, pmid):
        return FPLS(soup)


def gen_fpls(issn):

    g = GenerateFPLS(issn)
    g.run()


def download_fpls(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'https://www.frontiersin.org'

        def check_soup(self, paper, soup, resp):
            a = soup.select('div.article-section div.JournalFullText')

            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_fpls(issn):

    g = GenerateFPLS(issn)
    print(g.tohtml())


if __name__ == '__main__':
    download_fpls(issn='1664-462X', sleep=10., mx=3)
