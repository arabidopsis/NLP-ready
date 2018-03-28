from collections import defaultdict
import click
from mlabc import Download, Clean, Generate

ISSN = {
    '1460-2431': 'J. Exp. Bot.',
    '0022-0957': 'J. Exp. Bot.',
    '1471-9053': 'Plant Cell Physiol',
    '0032-0781': 'Plant Cell Physiol.'
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
        sections = {'abstract', 'results', 'materials and methods'}
        for k in objs:
            if k in sections:
                res[k] = objs[k]
        # assert set(res) == sections, (set(res))
        self.resultsd = res

    def results(self):
        return self.resultsd.get('results')

    def methods(self):
        return self.resultsd.get('materials and methods')

    def abstract(self):
        return self.resultsd.get('abstract')

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
                click.secho('%s %s:missing abstract=%s methods=%s results=%s' % (paper.pmid, paper.issn, a is None, m is None, r is None), fg='magenta')

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
    # download_oup(issn='0022-0957', sleep=60. * 2, mx=0)
    # download_oup(issn='1460-2431', sleep=60. * 2, mx=0)
    # download_oup(issn='1471-9053', sleep=60. * 2, mx=0)
    # download_oup(issn='0032-0781', sleep=60. * 2, mx=0)
    # gen_oup(issn='1471-9053')
    # gen_oup(issn='0032-0781')
    html_oup(issn='0032-0781')
