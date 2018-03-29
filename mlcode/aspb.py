import click

from mlabc import Download, Generate, Clean


ISSN = {
    '1040-4651': 'Plant Cell',
    '0032-0889': 'Plant Physiol.',
    '1532-298X': 'Plant Cell',  # web issn for the plant cell
    '1532-2548': 'Plant Physiol.'
}


def download_aspb(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = 'http://www.plantcell.org'

        def check_soup(self, paper, soup, resp):
            a = soup.select('div.article.fulltext-view')
            if not a:
                xml = b'failed-no-article'  # but there might be a full PDF! sigh!
                click.secho('failed %s doi=%s no article!' % (paper.pmid, paper.doi), fg='red')
                return xml
            return None  # OK!

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


class ASPB(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.article.fulltext-view')[0]
        assert a
        self.article = a

    def results(self):
        for s in self.article.select('div.section'):
            if 'results' in s.attrs['class']:
                return s
        for s in self.article.select('div.section'):
            n = s.find('h2')
            if n:
                txt = n.text.lower()
                if txt.find('methods') >= 0:
                    return s
        return None

    def methods(self):
        for s in self.article.select('div.section'):
            if 'materials-methods' in s.attrs['class']:
                return s
            if 'methods' in s.attrs['class']:
                return s
        for s in self.article.select('div.section'):
            n = s.find('h2')
            if n:
                txt = n.text.lower()
                if txt.find('methods') >= 0:
                    return s
        return None

    def abstract(self):
        for s in self.article.select('div.section'):
            if 'abstract' in s.attrs['class']:
                return s

        for s in self.article.select('div.section'):
            txt = s.find('h2').string.lower()
            if txt.find('abstract') >= 0:
                return s
        return None

    def tostr(self, sec):
        for a in sec.select('a.xref-bibr'):
            a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt

    def title(self):
        s = self.root.select('#page-title')
        if s:
            return s[0].text.strip()

        return super().title()


class GenerateASPB(Generate):
    cc = set()

    def create_clean(self, soup, pmid):
        aspb = ASPB(soup)
        a = soup.select('div.article.fulltext-view')[0]
        for sec in a.select('div.section'):
            for c in sec.attrs['class']:
                self.cc.add(c)
            n = sec.find('h2')
            if n:
                txt = n.text  # .lower()
                self.cc.add(txt)
        return aspb


def gen_aspb(issn):
    e = GenerateASPB(issn)
    e.run()
    print(e.cc)


def html_aspb(issn):
    e = GenerateASPB(issn)
    print(e.tohtml())


if __name__ == '__main__':
    download_aspb(sleep=60. * 2, mx=0, issn='1040-4651')
    download_aspb(sleep=60. * 2, mx=0, issn='0032-0889')
    download_aspb(sleep=60. * 2, mx=0, issn='1532-298X')  # web issn for the plant cell
    download_aspb(sleep=60. * 2, mx=0, issn='1532-2548')  # web issn for plant physiology
    gen_aspb(issn='1040-4651')
    gen_aspb(issn='0032-0889')
    gen_aspb(issn='1532-298X')  # web issn for the plant cell
    gen_aspb(issn='1532-2548')
