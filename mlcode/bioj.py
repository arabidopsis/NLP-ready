import click
import requests

from .mlabc import Clean, Download, Generate

ISSN = {"1470-8728": "Biochem. J.", "0264-6021": "Biochem. J."}


class BIOJ(Clean):
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

        for a in sec.select("p a.xref-bibr"):
            a.replace_with("CITATION")
        for a in sec.select("div.fig.pos-float"):
            a.replace_with(self.newfig(a, caption=".fig-caption p"))
        for a in sec.select("div.table.pos-float"):
            a.replace_with(self.newtable(a, caption=".table-caption p"))

        return super().tostr(sec)


class GenerateBIOJ(Generate):
    def create_clean(self, soup, pmid):
        return BIOJ(soup)


def gen_bioj(issn):

    gad = GenerateBIOJ(issn)
    gad.run()


def download_bioj(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "http://www.biochemj.org"

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
            if not a:
                click.secho(
                    f"no full text {paper.pmid} http://doi.org/{paper.doi}", fg="red",
                )
                return b"no full-text"
            assert a and len(a) == 1, (paper.pmid, resp.url)
            return None

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


def html_bioj(issn):

    b = GenerateBIOJ(issn)
    print(b.tohtml())


if __name__ == "__main__":
    download_bioj(issn="1470-8728", sleep=120.0, mx=0)
    download_bioj(issn="0264-6021", sleep=120.0, mx=0)
    # gen_bioj(issn='0264-6021')
