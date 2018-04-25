import requests
from mlabc import Clean, Download, Generate


ISSN = {
    '1535-3907': 'J. Proteome Res.',
    '1535-3893': 'J. Proteome Res.',
    '0006-2960': 'Biochemistry',
    '1520-4995': 'Biochemistry',
}


class JProteome(Clean):

    def __init__(self, root):
        self.root = root
        a = root.select('article.article')
        assert a, a
        self.article = a[0]

    def results(self):
        secs = self.article.select('#articleBody .hlFld-Fulltext .NLM_sec_level_1')
        for sec in secs:
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                # [sic!] spelling
                for t in ['results', 'results and discussion', 'results and discussiom']:
                    if txt.endswith(t):
                        return sec

        return None

    def methods(self):
        secs = self.article.select('#articleBody .hlFld-Fulltext .NLM_sec_level_1')
        for sec in secs:
            h2 = sec.find('h2')
            if h2:
                txt = h2.text.lower().strip()
                for t in ['experimental section', 'methods', 'experimental procedures', 'materials and methods',
                          'material and methods']:  # spelling!
                    if txt.endswith(t):
                        return sec

        return None

    def abstract(self):
        secs = self.article.select('#articleBody .hlFld-Abstract #abstractBox')
        return secs[0] if secs else None

    def title(self):
        return self.article.select('h1.articleTitle')[0].text.strip()

    def tostr(self, sec):

        for a in sec.select('div.figure'):
            a.replace_with(self.newfig(a, caption='.caption p'))
        for a in sec.select('div.NLM_table-wrap'):
            a.replace_with(self.newtable(a, caption='.NLM_caption'))
        for a in sec.select('div.NLM_p a.ref'):
            a.replace_with(' CITATION ')

        def paraordiv(tag):

            ret = tag.name == 'p' or (
                tag.name == 'div' and tag.has_attr('class') and 'NLM_p' in tag['class'])

            return ret

        txt = [self.SPACE.sub(' ', p.text) for p in sec.find_all(paraordiv)]
        return txt


class GenerateJProteome(Generate):
    def create_clean(self, soup, pmid):
        return JProteome(soup)


def gen_jproteome(issn):

    g = GenerateJProteome(issn)
    g.run()


def download_jproteome(issn, sleep=5.0, mx=0):

    class D(Download):
        Referer = 'https://pubs.acs.org'

        def get_response(self, paper, header):
            resp = requests.get('http://doi.org/{}'.format(paper.doi), headers=header)
            if resp.url.find('/doi/abs/') > 0 and resp.url.find('/doi/full/') < 0:
                url = resp.url.replace('/doi/abs/', '/doi/full/')
                print('redirect', url)
                header['Referer'] = resp.url
                resp = requests.get(url, headers=header)
            return resp

        def check_soup(self, paper, soup, resp):
            a = soup.select('article.article #articleBody')
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_jproteome(issn):

    g = GenerateJProteome(issn)
    print(g.tohtml())


if __name__ == '__main__':
    # download_jproteome(issn='1535-3907', sleep=120., mx=0)
    # download_jproteome(issn='1535-3893', sleep=120., mx=0)
    download_jproteome(issn='0006-2960', sleep=10., mx=2)
