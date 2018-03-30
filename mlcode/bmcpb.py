from mlabc import Clean, Download, Generate

# BMC Plant Biology

ISSN = {
    '1471-2229': 'BMC Plant Biol.'
}


class PMCPB(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('.FulltextWrapper section.Abstract')

        assert a, a
        abs = a[0]
        self.article = abs.parent

    def results(self):
        secs = self.article.select('section.Section1')
        for sec in secs:
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'results', 'results and discussion'}:
                    return sec

        return None

    def methods(self):
        secs = self.article.select('section.Section1')
        for sec in secs:
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'experimental section', 'methods', 'experimental procedures', 'materials and methods',
                           'material and methods'}:  # spelling!
                    return sec

        return None

    def abstract(self):
        secs = self.article.select('section.Abstract')
        return secs[0] if secs else None

    def title(self):
        t = self.root.select('.FulltextWrapper .MainTitleSection h1')
        return t[0].text.strip()

    def tostr(self, sec):
        for a in sec.select('p figure,div.Para figure'):
            p = self.root.new_tag('span')

            p.string = '[[TABLE]]' if 'FigureTable' in a['class'] else '[[FIGURE]]'
            a.replace_with(p)

        for a in sec.select('span.CitationRef'):
            a.replace_with('CITATION')

        def paraordiv(tag):
            return tag.name == 'p' or (tag.name == 'div' and 'Para' in tag['class'])

        txt = [self.SPACE.sub(' ', p.text) for p in sec.find_all(paraordiv)]
        return txt


class GeneratePMCPB(Generate):
    def create_clean(self, soup, pmid):
        return PMCPB(soup)


def gen_bmcpb(issn):

    g = GeneratePMCPB(issn)
    g.run()


def download_bmcpb(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'https://bmcplantbiol.biomedcentral.com'

        def check_soup(self, paper, soup, resp):
            a = soup.select('.FulltextWrapper section.Abstract')
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_jproteome(issn):

    g = GeneratePMCPB(issn)
    print(g.tohtml())


if __name__ == '__main__':
    download_bmcpb(issn='1471-2229', sleep=120., mx=0)
