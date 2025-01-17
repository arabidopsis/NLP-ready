from .mlabc import Clean, Download, Generate

ISSN = {
    "0027-8424": "Proc. Natl. Acad. Sci. U.S.A.",
    "1091-6490": "Proc. Natl. Acad. Sci. U.S.A.",
}


class PNAS(Clean):
    def __init__(self, root):
        super().__init__(root)
        a = root.select("div.article.fulltext-view")[0]
        assert a
        self.article = a

    def title(self):
        return self.root.select("#page-title")[0].text.strip()

    def results(self):
        secs = self.article.select("div.section.results-discussion")
        if secs:
            return secs[0]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2 and h2.string.lower() == "results":
                return sec
            if h2 and h2.string.lower() == "results and discussion":
                return sec

        return None

    def methods(self):
        secs = self.article.select("div.section.methods")
        if not secs:
            secs = self.article.select("div.section.materials-methods")
        if secs:
            return secs[0]
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower()
                if txt in {"materials and methods", "experimental procedures"}:
                    return sec
        return None

    def abstract(self):
        secs = self.article.select("div.section.abstract")
        return secs[0] if secs else None

    def tostr(self, sec):

        for a in sec.select("div.fig"):
            a.replace_with(self.newfig(a, caption=".fig-caption p"))
        for a in sec.select("div.table"):
            a.replace_with(
                self.newtable(
                    a,
                    caption=".table-caption p",
                )
            )
            # a.replace_with('[[FIGURE]]')
        for a in sec.select("p a.xref-bibr"):
            a.replace_with("CITATION")
        for a in sec.select("p a.xref-fig"):
            a.replace_with("FIG-REF")

        # def p(tag):
        #     return tag.name == "p" or (tag.name == "div" and ["fig"] == tag["class"])

        txt = [self.SPACE.sub(" ", p.text) for p in sec.select("p")]
        # txt = [self.SPACE.sub(' ', p.text) for p in sec.find_all(p)]
        return txt


def download_pnas(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "http://www.pnas.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article.fulltext-view")
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GeneratePNAS(Generate):
    def create_clean(self, soup, pmid):
        return PNAS(soup)


def gen_pnas(issn):
    e = GeneratePNAS(issn)
    e.run()


def html_pnas(issn):
    e = GeneratePNAS(issn)
    print(e.tohtml())


if __name__ == "__main__":
    # download_pnas(issn='0027-8424', sleep=60. * 2, mx=0)
    # download_pnas(issn='1091-6490', sleep=60. * 2, mx=0)
    # gen_pnas(issn='0027-8424')
    # gen_pnas(issn='1091-6490')
    html_pnas(issn="1091-6490")
