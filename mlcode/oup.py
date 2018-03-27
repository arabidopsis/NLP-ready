from collections import defaultdict
from mlabc import Download, Clean, Generate

OUP_ISSN = {'1460-2431': 'J. Exp. Bot.',
            '1471-9053': 'Plant Cell Physiol'
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
        assert set(res) == sections
        self.resultsd = res

    def results(self):
        return self.resultsd.get('results')

    def methods(self):
        return self.resultsd.get('materials and methods')

    def abstract(self):
        return self.resultsd.get('abstract')

    def tostr(self, sec):
        for a in sec.select('div.fig.fig-section'):
            p = self.root.new_tag('p')
            p.string = '[[FIGURE]]'
            a.replace_with(p)
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

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def gen_oup(issn):
    class G(Generate):
        def create_clean(self, soup, pmid):
            return OUP(soup)

    e = G(issn)
    e.run()


if __name__ == '__main__':
    download_oup(issn='1460-2431', sleep=60. * 2, mx=0)
    # download_oup(issn='1471-9053', sleep=60. * 2, mx=0)
    # download_oup(issn='0032-0781', sleep=60. * 2, mx=0)
    # gen_oup(issn='1471-9053')
    # gen_oup(issn='0032-0781')
