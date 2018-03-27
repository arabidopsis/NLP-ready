from mlabc import Download, Clean, Generate


ISSN = {
    '0950-1991': 'Development'
}


class Dev(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('div.article.fulltext-view')[0]
        assert a
        self.article = a

    def results(self):
        # secs = self.article.select('div.section.results-discussion')
        # if secs:
        #     return secs[0]
        for sec in self.article.select('div.section'):
            h2 = sec.find('h2')
            if h2:
                txt = h2.string.lower()
                if txt == 'results':
                    return sec
                if txt == 'results and discussion':
                    return sec

        return None

    def methods(self):
        # secs = self.article.select('div.section.methods')
        # if not secs:
        #     secs = self.article.select('div.section.materials-methods')
        # if secs:
        #     return secs[0]
        for sec in self.article.select('div.section'):
            if sec.find('h2').text.lower() == 'materials and methods':
                return sec
        return None

    def abstract(self):
        secs = self.article.select('div.section.abstract')
        return secs[0] if secs else None

    def tostr(self, sec):
        for a in sec.select('div.fig'):
            p = self.root.new_tag('p')
            p.string = '[[FIGURE]]'
            a.replace_with(p)
            # a.replace_with('[[FIGURE]]')
        for a in sec.select('p a.xref-ref'):
            a.replace_with('CITATION')

        def p(tag):
            return tag.name == 'p' or (tag.name == 'div' and 'fig' in tag['class'])
        # txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        txt = [self.SPACE.sub(' ', p.text) for p in sec.find_all(p)]
        return txt


def download_dev(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = 'http://dev.biologists.org'

        def check_soup(self, paper, soup, resp):
            a = soup.select('div.article.fulltext-view')
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateDev(Generate):
    def create_clean(self, soup, pmid):
        return Dev(soup)


def gen_dev(issn):
    e = GenerateDev(issn)
    e.run()


def html_dev(issn):
    e = GenerateDev(issn)
    print(e.tohtml())


if __name__ == '__main__':
    # download_dev(issn='0950-1991', sleep=10.0, mx=2)
    # gen_dev(issn='0950-1991')
    html_dev(issn='0950-1991')
