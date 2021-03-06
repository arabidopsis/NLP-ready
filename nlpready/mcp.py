import requests

from .mlabc import Clean, Download, Generate

ISSN = {
    "1535-9484": "Mol. Cell Proteomics",
    "1535-9476": "Mol. Cell Proteomics",
    # these seem to have the same HTML layout
    "0021-9193": "J. Bacteriol.",
    "0022-538X": "J. Virol.",
    "1098-5514": "J. Virol.",
    "0270-7306": "Mol. Cell. Biol.",
    "1098-5549": "Mol. Cell. Biol.",
    "1355-8382": "RNA",
    "1469-9001": "RNA",
}


class MCP(Clean):
    def __init__(self, root):
        super().__init__(root)
        a = root.select("div.article.fulltext-view")
        assert a, a
        self.article = a[0]

    def results(self):
        for sec in self.article.select("div.section"):
            h2 = sec.find("h2")
            if h2:
                txt = h2.text.lower().strip()
                if txt in {"results", "results and discussion"}:
                    return sec

        return None

    def methods(self):
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
            a.replace_with(self.newtable(a, caption=".table-caption"))
        for a in sec.select("div.fig.pos-float"):
            a.replace_with(self.newfig(a, caption=".fig-caption p"))
        for a in sec.select("p a.xref-bibr"):
            a.replace_with("CITATION")
        txt = [self.SPACE.sub(" ", p.text) for p in sec.select("p")]
        return txt


class GenerateMCP(Generate):
    def create_clean(self, soup, pmid):
        return MCP(soup)


def gen_mcp(issn):

    mcp = GenerateMCP(issn)
    mcp.run()


def download_mcp(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "http://www.mcponline.org"

        def get_response(self, paper, header):
            resp = requests.get(f"http://doi.org/{paper.doi}", headers=header)
            if not resp.url.endswith(".full"):
                resp = requests.get(resp.url + ".full", headers=header)
            return resp

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article.fulltext-view")
            # if not a and year <= 2001:  # probably only a (scanned?) PDF version
            #    xml = b'failed-only-pdf'
            #     d = fdir
            #    failed.add(pmid)
            # else:
            assert a and len(a) == 1, (paper.pmid, resp.url)

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_mcp(issn):

    mcp = GenerateMCP(issn)
    print(mcp.tohtml())


if __name__ == "__main__":

    download_mcp(issn="1535-9484", sleep=120.0, mx=0)
    download_mcp(issn="1535-9476", sleep=120.0, mx=0)
    # gen_mcp(issn='0890-9369')
