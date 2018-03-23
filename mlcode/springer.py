
from mlabc import Download, Clean, Generate, dump


class Springer(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('main#main-content article.main-body__content')
        assert a
        self.article = a[0]

    def results(self):
        secs = self.article.select('#body section.SectionTypeResults')
        if secs:
            return secs[0]
        return None

    def methods(self):
        secs = self.article.select('#body section.SectionTypeMaterialsAndMethods')
        if secs:
            return secs[0]
        return None

    def abstract(self):

        secs = self.article.select('section.Abstract')
        if secs:
            return secs[0]
        secs = self.article.select('div.section.abstract')
        return secs[0] if secs else None

    def tostr(self, sec):
        for a in sec.select('figure'):
            a.replace_with('[[FIGURE]]')
        for a in sec.select('div.Table'):
            a.replace_with('[[TABLE]]')
        for a in sec.select('span.CitationRef'):
            a.replace_with('CITATION')

        def para(tag):
            return tag.name == 'p' or (tag.name == 'div' and 'Para' in tag['class'])

        # txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p, div.Para')]
        txt = [self.SPACE.sub(' ', p.text) for p in sec.find_all(para)]
        return txt


def download_springer(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = 'https://link.springer.com'

        def check_soup(self, paper, soup, resp):
            a = soup.select('main#main-content article.main-body__content')
            if not a and paper.year < 2005:
                dump(paper, resp.content)
                return b'failed-only-pdf'
            else:
                assert a and len(a) == 1, (paper.pmid, resp.url, paper.doi)
    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateSpringer(Generate):
    def create_clean(self, soup, pmid):
        return Springer(soup)


def gen_springer(issn):
    e = GenerateSpringer(issn)
    e.run()


def html_springer(issn):
    e = GenerateSpringer(issn)
    print(e.tohtml('template.html'))


if __name__ == '__main__':
    # download_springer(issn='1573-5028', sleep=10., mx=4)
    # download_springer(issn='0167-4412', sleep=60. * 2, mx=0)
    # gen_springer(issn='1573-5028')
    # gen_springer(issn='0167-4412')
    html_springer(issn='1573-5028')
