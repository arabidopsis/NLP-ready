from collections import defaultdict
from mlabc import Download, Clean, Generate


# 1059-1524 ,Mol. Biol. Cell

ISSN = {
    '1059-1524': 'Mol. Biol. Cell',
    '1939-4586': 'Mol. Biol. Cell'
}


class ASCB(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.article__body')[0]
        assert a
        self.article = a
        objs = defaultdict(list)
        target = None
        a = self.article.select('div.hlFld-Fulltext')[0]
        for d in a.contents:
            if d.name == 'h2':
                target = d.text.lower().strip()
            elif d.name == 'p' or d.name == 'figure':
                if target:
                    objs[target].append(d)
        res = {}
        sections = {'results', 'materials and methods'}
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
        s = self.article.select('div.abstractSection.abstractInFull')
        if s:
            return s[0].select('p') or s
        return None

    def title(self):
        s = self.root.select('h1.citation__title')
        if s:
            return s[0].text.strip()
        return super().title()

    def tostr(self, secs):
        # import sys
        ss = []
        for sec in secs:
            for a in sec.select('a.tab-link'):
                a.replace_with('CITATION')
            if sec.name == 'figure':
                new_tag = self.root.new_tag("p")
                new_tag.string = "[[FIGURE]]"
                # sec.replace_with(new_tag)  # doesn't seem to work
                ss.append(new_tag)
            else:
                for s in sec.select('figure'):
                    new_tag = self.root.new_tag("p")
                    new_tag.string = "[[FIGURE]]"
                    s.replace_with(new_tag)
                ss.append(sec)

        txt = [self.SPACE.sub(' ', p.text) for p in ss]
        return txt


def download_ascb(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'https://www.molbiolcell.org'

        def check_soup(self, paper, soup, resp):
            a = soup.select('div.article__body div.abstractSection.abstractInFull')
            assert a, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateASCB(Generate):
    def create_clean(self, soup, pmid):
        return ASCB(soup)


def gen_ascb(issn):

    e = GenerateASCB(issn)
    e.run()


def html_ascb(issn):

    e = GenerateASCB(issn)
    print(e.tohtml())


if __name__ == '__main__':
    download_ascb(issn='1059-1524', sleep=120., mx=0)
    download_ascb(issn='1939-4586', sleep=120., mx=0)
    # html_ascb(issn='1059-1524')
