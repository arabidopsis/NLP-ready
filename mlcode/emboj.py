from mlabc import Clean, Generate, Download


ISSN = {
    '1460-2075': 'EMBO J.'
}


class EMBOJ(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.article.fulltext-view')[0]
        assert a
        self.article = a

    def results(self):
        secs = self.article.select('div.section.results-discussion')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            h2 = sec.find('h2')
            if h2 and h2.string.lower() == 'results':
                return sec
            if h2 and h2.string.lower() == 'results and discussion':
                return sec

        return None

    def methods(self):
        secs = self.article.select('div.section.methods')
        if not secs:
            secs = self.article.select('div.section.materials-methods')
        if secs:
            return secs[0]
        for sec in self.article.select('div.section'):
            if sec.find('h2').text.lower() == 'materials and methods':
                return sec
        return None

    def abstract(self):
        secs = self.article.select('div.section.abstract')
        return secs[0] if secs else None

    def tostr(self, sec):
        for a in sec.select('p a.xref-ref'):
            a.replace_with('CITATION')
        for a in sec.select('p a.xref-fig'):
            a.replace_with('FIGURE')
        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


def download_emboj(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = 'http://www.pnas.org'

        def check_soup(self, pmid, soup, resp):
            a = soup.select('div.article.fulltext-view')
            assert a and len(a) == 1, (pmid, resp.url)

    e = D(issn, sleep=sleep, mx=mx)
    e.run()


class EMBJ(Generate):
    def create_clean(self, soup, pmid):
        return EMBOJ(soup)


def gen_emboj(issn):

    e = EMBJ(issn)
    e.run()


def html_emboj(issn):

    e = EMBJ(issn)
    print(e.tohtml())


if __name__ == '__main__':
    # this is also a Wiley thing
    # download_emboj(issn='1460-2075', sleep=60. * 2, mx=0)
    html_emboj(issn='1460-2075')
