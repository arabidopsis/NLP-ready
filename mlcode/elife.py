from mlabc import Clean, Download, Generate

# http://genesdev.cshlp.org


ISSN = {
    "2050-084X": "Elife",
}


class Elife(Clean):
    def __init__(self, root):
        self.root = root
        a = root.select("main")
        assert a, a
        self.article = a[0]

    def results(self):
        for sec in self.article.select("section.article-section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return sec

        return None

    def methods(self):
        for sec in self.article.select("section.article-section"):
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
        secs = self.article.select("#abstract")
        return secs[0] if secs else None

    def title(self):
        return self.article.select("h1.content-header__title")[0].text.strip()

    def tostr(self, sec):

        for a in sec.select("div.asset-viewer-inline"):
            id = a.attrs.get("id")
            if not id:
                continue

            if id.startswith("fig"):
                a.replace_with(self.newfig(a))
            elif id.startswith("tbl"):
                a.replace_with(self.newtable(a))
        for a in sec.select("p a"):
            href = a.attrs.get("href")
            if not href or not href.startswith("#bib"):
                continue
            a.replace_with("CITATION")
        txt = [self.SPACE.sub(" ", p.text) for p in sec.select("p")]
        return txt


class GenerateElife(Generate):
    def create_clean(self, soup, pmid):
        return Elife(soup)


def gen_elife(issn):

    elife = GenerateElife(issn)
    elife.run()


def download_elife(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "https://elifesciences.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("main section.article-section")
            assert a, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_elife(issn):

    elife = GenerateElife(issn)
    print(elife.tohtml())


if __name__ == "__main__":
    for issn in ISSN:
        download_elife(issn=issn, sleep=10.0, mx=1)
