from mlabc import Download, Clean, Generate, dump


ISSN = {
    '1573-5028': 'Plant Mol. Biol.',
    '0167-4412': 'Plant Mol. Biol.',
    '1432-2048': 'Planta',
    '0032-0935': 'Planta',
    '1615-6102': 'Protoplasma',
    '0033-183X': 'Protoplasma',
    '1617-4623': 'Mol. Genet. Genomics',
    '1617-4615': 'Mol. Genet. Genomics',
    '0918-9440': 'J. Plant Res.',
    '1618-0860': 'J. Plant Res.',
    '1432-203X': 'Plant Cell Rep.',
    '0721-7714': 'Plant Cell Rep',
    '0009-5915': 'Chromosoma',
    '1432-0886': 'Chromosoma',
    '1573-4978': 'Mol. Biol. Rep.',

    # added
    '0040-5752': 'Theor. Appl. Genet.',
    '0172-8083': 'Curr. Genet.',
    '0175-7598': 'Appl. Microbiol. Biotechnol.',
    '0219-1032': 'Mol. Cells',
    '0949-944X': 'Dev. Genes Evol.',
    '1420-682X': 'Cell. Mol. Life Sci.',
    '1438-793X': 'Funct. Integr. Genomics',
    '1438-7948': 'Funct. Integr. Genomics',
    '1466-1268': 'Cell Stress Chaperones',
    '1573-5079': 'Photosyn. Res.',
    '2194-7961': 'Plant Reprod',

    '2193-1801': 'Springerplus',

    '1438-2199': 'Amino Acids',


}


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
        for sec in self.article.select('#body section'):
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'results', 'results and discussion'}:
                    return sec
        return None

    def methods(self):
        secs = self.article.select('#body section.SectionTypeMaterialsAndMethods')
        if secs:
            return secs[0]
        for sec in self.article.select('#body section'):
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'materials and methods', 'experimental procedures'}:
                    return sec
        return None

    def abstract(self):

        secs = self.article.select('section.Abstract')
        if secs:
            return secs[0]
        secs = self.article.select('div.section.abstract')
        return secs[0] if secs else None

    def title(self):
        s = self.root.select('h1.ArticleTitle')
        if s:
            return s[0].text.strip()
        return super().title()

    def tostr(self, sec):
        for a in sec.select('figure'):
            # figure inside a div.Para so can't really replace
            # with a "p"
            new_tag = self.root.new_tag("span")
            new_tag.string = " [[FIGURE]] "  # % a.attrs['id']
            a.replace_with(new_tag)
            # a.replace_with('[[FIGURE]]')
        for a in sec.select('div.Table'):
            new_tag = self.root.new_tag("p")
            new_tag.string = "[[TABLE]]"
            a.replace_with(new_tag)
            # a.replace_with('[[TABLE]]')
        for a in sec.select('span.CitationRef'):
            a.replace_with('CITATION')

        def para(tag):
            return tag.name == 'p' or (tag.name == 'div' and tag.has_attr('class') and 'Para' in tag['class'])

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
    print(e.tohtml())


if __name__ == '__main__':
    download_springer(issn='1573-5028', sleep=60. * 2, mx=0)
    download_springer(issn='0167-4412', sleep=60. * 2, mx=0)
    download_springer(issn='0032-0935', sleep=60. * 2, mx=0)
    download_springer(issn='1432-2048', sleep=60. * 2, mx=0)
    download_springer(issn='1615-6102', sleep=60. * 2, mx=0)
    download_springer(issn='0033-183X', sleep=60. * 2, mx=0)
    # gen_springer(issn='1573-5028')
    # gen_springer(issn='0167-4412')
    # html_springer(issn='1573-5028')
    # html_springer(issn='0032-0935')
