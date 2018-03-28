import requests

from mlabc import Clean, Download, Generate

# http://genesdev.cshlp.org


ISSN = {
    '0890-9369': 'Genes Dev.'
}


class GAD(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.article.fulltext-view')[0]
        assert a
        self.article = a

    def results(self):
        secs = self.article.select('div.section.results')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'results', 'results and discussion'}:
                    return sec

        return None

    def methods(self):
        secs = self.article.select('div.section.materials-methods')
        if secs:
            return secs[0]
        secs = self.article.select('div.section.methods')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'methods', 'experimental procedures', 'materials and methods',
                           'material and methods'}:  # spelling!
                    return sec

        return None

    def abstract(self):
        secs = self.article.select('div.section.abstract')
        return secs[0] if secs else None

    def tostr(self, sec):
        for a in sec.select('div.fig.pos-float'):
            p = self.root.new_tag('p')
            p.string = '[[FIGURE]]'
            a.replace_with(p)
        for a in sec.select('p a.xref-bibr'):
            a.replace_with('CITATION')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


class GenerateGAD(Generate):
    def create_clean(self, soup, pmid):
        return GAD(soup)


def gen_gad(issn):

    gad = GenerateGAD(issn)
    gad.run()


def download_gad(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'http://genesdev.cshlp.org'

        def get_response(self, paper, header):
            resp = requests.get('http://doi.org/{}'.format(paper.doi), headers=header)
            if not resp.url.endswith('.full'):
                resp = requests.get(resp.url + '.full', headers=header)
            return resp

        def check_soup(self, paper, soup, resp):
            a = soup.select('div.article.fulltext-view')
            # if not a and year <= 2001:  # probably only a (scanned?) PDF version
            #    xml = b'failed-only-pdf'
            #     d = fdir
            #    failed.add(pmid)
            # else:
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_gad(issn):

    gad = GenerateGAD(issn)
    print(gad.tohtml())


if __name__ == '__main__':

    download_gad(issn='0890-9369', sleep=10., mx=5)
    # gen_gad(issn='0890-9369')
