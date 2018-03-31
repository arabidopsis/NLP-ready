from collections import defaultdict
import click
from mlabc import Download, Clean, Generate

ISSN = {
    '1460-2431': 'J. Exp. Bot.',
    '0022-0957': 'J. Exp. Bot.',
    '1471-9053': 'Plant Cell Physiol',
    '0032-0781': 'Plant Cell Physiol.',

    # added
    '0305-7364': 'Ann. Bot.',
    '1095-8290': 'Ann. Bot.',
    '1567-1364': 'FEMS Yeast Res.',
    '1460-2423': 'Glycobiology',
    '1756-2651': 'J. Biochem.',
    '1537-1719': 'Mol. Biol. Evol.',
    "1756-1663": "DNA Res.",
    "1362-4962": "Nucleic Acids Res.",

}


class OUP(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.article-body div.widget-items')[0]
        assert a
        self.article = a
        objs = defaultdict(list)
        target = None
        for d in a.contents:
            if d.name == 'h2':
                target = d.text.lower().strip()
            elif d.name == 'section' and d.attrs['class'] == ['abstract']:
                target = 'abstract'
                for p in d.select('p'):
                    objs[target].append(p)
            elif d.name == 'p':
                if target:
                    objs[target].append(d)
        res = {}
        sections = {'abstract', 'results', 'materials and methods', 'results and discussion',
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
        s = self.article.select('section.abstract')
        if s:
            return s[0].select('p') or s
        return self.resultsd.get('abstract')

    def title(self):
        s = self.root.select('h1.wi-article-title')
        if s:
            return s[0].text.strip()
        return super().title()

    def tostr(self, sec):

        for p in sec:
            for a in p.select('a.xref-bibr'):
                a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec]
        return txt


def download_oup(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'https://academic.oup.com'

        def check_soup(self, paper, soup, resp):
            a = soup.select('div.article-body div.widget-items')
            assert a and len(
                a) == 1 and a[0].attrs['data-widgetname'] == "ArticleFulltext", (paper.pmid, resp.url)
            o = OUP(soup)
            a = o.abstract()
            m = o.methods()
            r = o.results()
            if not (a and m and r):
                click.secho('%s %s:missing abstract=%s methods=%s results=%s' %
                            (paper.pmid, paper.issn, a is None, m is None, r is None), fg='magenta')

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateOUP(Generate):
    def create_clean(self, soup, pmid):
        return OUP(soup)


def gen_oup(issn):

    e = GenerateOUP(issn)
    e.run()


def html_oup(issn):
    e = GenerateOUP(issn)
    print(e.tohtml())


if __name__ == '__main__':
    for issn in ISSN:
        download_oup(issn, sleep=10., mx=1)
