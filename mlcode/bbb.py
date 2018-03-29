import requests
import click
from mlabc import Clean, Download, Generate


ISSN = {
    '0916-8451': 'Biosci. Biotechnol. Biochem.',
    '1347-6947': 'Biosci. Biotechnol. Biochem.'

}


class BBB(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('article.article')
        assert a, a
        self.article = a[0]

    def results(self):
        secs = self.article.select('.hlFld-Fulltext .NLM_sec_level_1')
        for sec in secs:
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'results', 'results and discussion'}:
                    return sec

        return None

    def methods(self):
        secs = self.article.select('.hlFld-Fulltext .MaterialsAndMethods.NLM_sec_level_1')
        if secs:
            return secs[0]
        secs = self.article.select('.hlFld-Fulltext .NLM_sec_level_1')
        for sec in secs:
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                if txt in {'experimental section', 'methods', 'experimental procedures', 'materials and methods',
                           'material and methods'}:  # spelling!
                    return sec

        return None

    def abstract(self):
        secs = self.article.select('.hlFld-Abstract .abstractInFull')
        return secs[0] if secs else None

    def title(self):
        return self.root.select('.NLM_article-title.hlFld-title')[0].text.strip()

    def tostr(self, sec):
        for a in sec.select('div.figure'):
            p = self.root.new_tag('p')  # , **{'class': 'NLM_p'})

            p.string = '[[FIGURE]]'
            a.replace_with(p)
        for a in sec.select('p span.ref-lnk a'):
            a.replace_with('CITATION')

        txt = [self.SPACE.sub(' ', p.text) for p in sec.select('p')]
        return txt


class GenerateBBB(Generate):
    def create_clean(self, soup, pmid):
        return BBB(soup)


def gen_bbb(issn):

    g = GenerateBBB(issn)
    g.run()


def download_bbb(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'https://www.tandfonline.com'

        def get_response(self, paper, header):
            resp = requests.get('http://doi.org/{}'.format(paper.doi), headers=header)
            if resp.url.find('/doi/full/') < 0:
                url = resp.url.replace('/doi/abs/', '/doi/full/')
                print('redirect', url)
                header['Referer'] = resp.url
                resp = requests.get(url, headers=header)
            return resp

        def check_soup(self, paper, soup, resp):
            a = soup.select('article.article div.hlFld-Fulltext')
            if resp.url.find('/doi/full/') < 0:
                click.secho('no full text %s %s' % (paper.pmid, resp.url), fg='red')
                return b'no full text'
            # if not a:
            #    print(soup)
            # if not a and year <= 2001:  # probably only a (scanned?) PDF version
            #    xml = b'failed-only-pdf'
            #     d = fdir
            #    failed.add(pmid)
            # else:
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_bbb(issn):

    g = GenerateBBB(issn)
    print(g.tohtml())


if __name__ == '__main__':
    download_bbb(issn='0916-8451', sleep=10., mx=2)
    download_bbb(issn='1347-6947', sleep=10., mx=2)
