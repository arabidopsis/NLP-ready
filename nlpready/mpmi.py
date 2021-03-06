from .mlabc import Clean, Download, Generate

ISSN = {
    "0894-0282": "Mol. Plant Microbe Interact.",
}


class MPMI(Clean):
    def __init__(self, root):
        super().__init__(root)
        a = root.select("table .pubContent")
        assert a, a
        self.article = a[0]

    def results(self):
        secs = self.article.select(
            ".hlFld-Fulltext .NLM_sec-type_results.NLM_sec_level_1"
        )
        if secs:
            return secs[0]
        secs = self.article.select(".hlFld-Fulltext .NLM_sec_level_1")
        for sec in secs:
            h2 = sec.select("table tr th")
            if h2:
                txt = h2[0].text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return sec

        return None

    def methods(self):
        secs = self.article.select(
            ".hlFld-Fulltext .NLM_sec-type_materials|methods.NLM_sec_level_1"
        )
        if secs:
            return secs[0]
        secs = self.article.select(
            ".hlFld-Fulltext .MaterialsAndMethods.NLM_sec_level_1"
        )
        if secs:
            return secs[0]
        secs = self.article.select(".hlFld-Fulltext .NLM_sec_level_1")
        for sec in secs:
            h2 = sec.select("table tr th")
            if h2:
                txt = h2[0].text.lower().strip()
                if txt in {
                    "experimental section",
                    "methods",
                    "experimental procedures",
                    "materials and methods",
                    "material and methods",
                }:  # spelling!
                    return sec

        return None

    def abstract(self):
        secs = self.article.select(".hlFld-Abstract .abstractInFull")
        return secs[0] if secs else None

    def title(self):
        return self.article.select(".hlFld-Abstract .hlFld-Title")[0].text.strip()

    def tostr(self, sec):
        for a in sec.select("div.figure"):
            p = self.root.new_tag("p")  # , **{'class': 'NLM_p'})

            p.string = "[[FIGURE]]"
            a.replace_with(p)
        for a in sec.select("p span.ref-lnk"):
            a.replace_with("CITATION")
        for a in sec.select("p a.ref.bibr"):
            a.replace_with("CITATION")

        return super().tostr(sec)


class GenerateMPMI(Generate):
    def create_clean(self, soup, pmid):
        return MPMI(soup)


def gen_mpmi(issn):

    g = GenerateMPMI(issn)
    g.run()


def download_mpmi(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "https://apsjournals.apsnet.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("table .pubContent div.hlFld-Fulltext")
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_mpmi(issn):

    g = GenerateMPMI(issn)
    print(g.tohtml())


if __name__ == "__main__":
    download_mpmi(issn="0894-0282", sleep=10.0, mx=2)
