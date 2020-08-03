from mlabc import Clean, Download, Generate

ISSN = {
    "0021-9533": "J. Cell. Sci.",
    "1477-9137": "J. Cell. Sci.",
    # added
    "0021-9525": "J. Cell Biol.",
    "1540-8140": "J. Cell Biol.",
}


class JCS(Clean):
    def __init__(self, root):
        self.root = root
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
        secs = self.article.select("div.section.materials-methods")
        if secs:
            return secs[0]
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
                    "material and methods",
                }:  # spelling!
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
        txt = [self.SPACE.sub(" ", p.text) for p in sec.select("p")]
        return txt


class GenerateJCS(Generate):
    def create_clean(self, soup, pmid):
        return JCS(soup)


def gen_jcs(issn):

    jcs = GenerateJCS(issn)
    jcs.run()


def download_jcs(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "http://jcs.biologists.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article.fulltext-view")
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_jcs(issn):

    jcs = GenerateJCS(issn)
    print(jcs.tohtml())


if __name__ == "__main__":
    download_jcs(issn="0021-9533", sleep=120.0, mx=0)
    download_jcs(issn="1477-9137", sleep=120.0, mx=0)
    # gen_gad(issn='0890-9369')
