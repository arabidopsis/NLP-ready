import requests

from .mlabc import Clean, Download, Generate

ISSN = {"0021-9258": "J. Biol. Chem.", "1083-351X": "J. Biol. Chem."}


class JBC(Clean):
    def __init__(self, root):
        super().__init__(root)
        a = root.select("div.article.fulltext-view")
        assert a, a
        self.article = a[0]

    def results(self):
        secs = self.article.select("div.section.results")
        if secs:
            return secs[0]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return sec
        return None

    def methods(self):
        secs = self.article.select("div.section.methods")
        if secs:
            return secs[0]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {
                    "methods",
                    "experimental procedures",
                    "materials and methods",
                }:
                    return sec

        return None

    def abstract(self):
        secs = self.article.select("div.section.abstract")
        return secs[0] if secs else None

    def tostr(self, sec):

        for a in sec.select("div.table.pos-float"):
            a.replace_with(self.newtable(a, caption=".table-caption p"))
        for a in sec.select("div.fig.pos-float"):
            a.replace_with(self.newfig(a, caption=".fig-caption p"))
        for a in sec.select("p a.xref-bibr"):
            a.replace_with("CITATION")
        return super().tostr(sec)


def download_jbc(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "http://www.jbc.org"

        def get_response(self, paper, header):
            resp = requests.get(f"http://doi.org/{paper.doi}", headers=header)
            if not resp.url.endswith(".full"):
                resp = requests.get(resp.url + ".full", headers=header)
            return resp

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article.fulltext-view")
            if not a:
                if paper.year <= 2001:  # probably only a (scanned?) PDF version
                    return b"failed-only-pdf"
                assert a, (a, resp.url, paper.doi)
            return None

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


class GenerateJBC(Generate):
    def create_clean(self, soup, pmid):
        return JBC(soup)


def gen_jbc(issn):

    e = GenerateJBC(issn)
    e.run()


def html_jbc(issn):

    e = GenerateJBC(issn)
    print(e.tohtml())


if __name__ == "__main__":
    # download_jbc(issn='0021-9258', sleep=60. * 2, mx=0)
    # download_jbc(issn='1083-351X', sleep=60. * 2, mx=0)
    # gen_jbc(issn='0021-9258')
    # gen_jbc(issn='1083-351X')
    html_jbc(issn="0021-9258")
