from __future__ import annotations

from collections import defaultdict

import click

from ._mlabc import Clean
from ._mlabc import Download
from ._mlabc import Generate

ISSN = {
    "1460-2431": "J. Exp. Bot.",
    "0022-0957": "J. Exp. Bot.",
    "1471-9053": "Plant Cell Physiol",
    "0032-0781": "Plant Cell Physiol.",
    # added
    "0305-7364": "Ann. Bot.",
    "1095-8290": "Ann. Bot.",
    "1567-1364": "FEMS Yeast Res.",
    "1460-2423": "Glycobiology",
    "1756-2651": "J. Biochem.",
    "1537-1719": "Mol. Biol. Evol.",
    "0737-4038": "Mol. Biol. Evol.",
    "1362-4962": "Nucleic Acids Res.",
    "2041-2851": "AoB Plants",
    "1340-2838": "DNA Res.",
    "1756-1663": "DNA Res.",
}


def has_class(d, cls):
    return d.has_attr("class") and cls in d["class"]


def ok_elem(tag):
    if tag.name == "p":
        return True
    if tag.name == "div":
        if has_class(tag, "fig-section") or has_class(tag, "table-wrap"):
            return True
    return False


class OUP(Clean):
    def __init__(self, root):
        super().__init__(root)
        a = root.select("div.article-body div.widget-items")
        assert a, a
        self.article = a[0]

        objs = defaultdict(list)
        target = None
        for d in self.article.contents:
            if d.name == "h2":
                target = d.text.lower().strip()
            elif d.name == "section" and d.attrs["class"] == ["abstract"]:
                target = "abstract"
                for p in d.select("p"):
                    objs[target].append(p)
            elif ok_elem(d):
                if target:
                    objs[target].append(d)
        res = {}
        # sections = {'abstract', 'results', 'materials and methods', 'results and discussion',
        #             'material and methods'}  # spelling!
        for k in objs:
            # if k in sections:
            res[k] = objs[k]
        # assert set(res) == sections, (set(res))
        self.resultsd = res

    def results(self):
        K = ("results and discussion", "results")
        for k in K:
            if k in self.resultsd:
                return self.resultsd[k]
        for k in self.resultsd:
            if k.endswith(K):
                return self.resultsd[k]
        return None

    def methods(self):
        K = ("materials and methods", "material and methods")
        for k in K:
            if k in self.resultsd:
                return self.resultsd[k]
        for k in self.resultsd:
            if k.endswith(K):
                return self.resultsd[k]
        return None

    def abstract(self):
        s = self.article.select("section.abstract")
        if s:
            return s[0].select("p") or s
        return self.resultsd.get("abstract")

    def title(self):
        s = self.root.select("h1.wi-article-title")
        if s:
            return s[0].text.strip()
        return super().title()

    def tostr(self, sec):

        for p in sec:
            for a in p.select("a.xref-bibr"):
                a.replace_with("CITATION")
        ss = []
        for p in sec:
            if p.name == "div":
                if has_class(p, "fig-section"):
                    ss.append(self.newfig(p, caption=".fig-caption p", node="div"))
                elif has_class(p, "table-wrap"):
                    ss.append(self.newtable(p, caption=".caption p", node="div"))
            else:
                ss.append(p)

        txt = [self.SPACE.sub(" ", p.text) for p in ss]
        return txt


def download_oup(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "https://academic.oup.com"

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article-body div.widget-items")
            assert (
                a and len(a) == 1 and a[0].attrs["data-widgetname"] == "ArticleFulltext"
            ), (paper.pmid, resp.url)
            o = OUP(soup)
            a = o.abstract()
            m = o.methods()
            r = o.results()
            if not (a and m and r):
                click.secho(
                    "%s %s:missing abstract=%s methods=%s results=%s"
                    % (paper.pmid, paper.issn, a is None, m is None, r is None),
                    fg="magenta",
                )

    o = D(issn, sleep=sleep, mx=mx)
    o.run()


class GenerateOUP(Generate):
    def create_clean(self, soup, pmid):
        return OUP(soup)


def gen_oup(issn):

    e = GenerateOUP(issn)
    e.run()


def html_oup(issn):
    e = GenerateOUP(issn)
    print(e.tohtml())


def run():
    for issn in ISSN:
        download_oup(issn, sleep=10.0, mx=1)


if __name__ == "__main__":
    run()
