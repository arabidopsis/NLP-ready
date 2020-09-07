from .mlabc import Clean, Download, Generate

ISSN = {
    "0016-6731": "Genetics",
    "1943-2631": "Genetics",
}


class Genetics(Clean):
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
            # print(a, file=sys.stderr)
            a.replace_with(self.newfig(a))
        for a in sec.select("p a.xref-bibr"):
            a.replace_with("CITATION")
        txt = [self.SPACE.sub(" ", p.text) for p in sec.select("p")]
        return txt


def download_genetics(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "http://www.genetics.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article.fulltext-view")
            if not a:
                if paper.year <= 2001:  # probably only a (scanned?) PDF version
                    return b"failed-only-pdf"
                else:
                    assert a, (a, resp.url, paper.doi)
            return None

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


class GenerateGenetics(Generate):
    def create_clean(self, soup, pmid):
        return Genetics(soup)


def gen_genetics(issn):

    e = GenerateGenetics(issn)
    e.run()


def html_genetics(issn):

    e = GenerateGenetics(issn)
    print(e.tohtml())


def run():
    for issn in ISSN:
        download_genetics(issn, sleep=10.0, mx=1)


if __name__ == "__main__":
    run()
