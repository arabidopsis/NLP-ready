import click

from .mlabc import Clean, Download, Generate

ISSN = {
    "1040-4651": "Plant Cell",
    "1532-298X": "Plant Cell",  # web issn for the plant cell
    "0032-0889": "Plant Physiol.",
    "1532-2548": "Plant Physiol.",
    # not part of ASPB
    "1471-2970": "Philos. Trans. R. Soc. Lond., B, Biol. Sci.",
}


def download_aspb(issn, sleep=5.0, mx=0):
    class D(Download):
        Referer = "http://www.plantcell.org"

        def check_soup(self, paper, soup, resp):
            a = soup.select("div.article.fulltext-view")
            if not a:
                xml = b"failed-no-article"  # but there might be a full PDF! sigh!
                click.secho(
                    f"failed {paper.pmid} doi={paper.doi} no article!", fg="red"
                )
                return xml
            return None  # OK!

    download = D(issn, sleep=sleep, mx=mx)
    download.run()


class ASPB(Clean):
    def __init__(self, root):
        super().__init__(root)
        a = root.select("div.article.fulltext-view")
        assert a, a
        self.article = a[0]

    def results(self):
        for s in self.article.select("div.section"):
            cls = s.attrs.get("class", [])
            if "results" in cls:
                return s
        for s in self.article.select("div.section"):
            n = s.find("h2")
            if n:
                txt = n.text.lower()
                if txt.find("results") >= 0:
                    return s
        return None

    def methods(self):
        for s in self.article.select("div.section"):
            cls = s.attrs.get("class", [])
            if "materials-methods" in cls:
                return s
            if "methods" in cls:
                return s
        for s in self.article.select("div.section"):
            n = s.find("h2")
            if n:
                txt = n.text.lower()
                if txt.find("methods") >= 0:
                    return s
        return None

    def abstract(self):
        for s in self.article.select("div.section"):
            if "abstract" in s.attrs["class"]:
                return s

        for s in self.article.select("div.section"):
            txt = s.find("h2").string.lower()
            if txt.find("abstract") >= 0:
                return s
        return None

    def tostr(self, sec):

        for a in sec.select("a.xref-bibr"):
            a.replace_with("CITATION")
        for a in sec.select("div.fig.pos-float"):
            a.replace_with(self.newfig(a, caption=".fig-caption p"))

        txt = [self.SPACE.sub(" ", p.text) for p in sec.select("p")]
        return txt

    def title(self):
        s = self.root.select("#page-title")
        if s:
            return s[0].text.strip()
        s = self.root.select(
            "h1.highwire-cite-title"
        )  # philo trans of royal society B.
        if s:
            return s[0].text.strip()

        return super().title()

    def xrefs(self):
        def xref(s):
            for c in s.select("li div[data-doi]"):
                cite = c.find("cite")
                title = cite.select(".cit-article-title")[0].text
                yield dict(doi=c.attrs["data-doi"], title=title)

        for s in self.article.select("div.section"):
            if "ref-list" in s.attrs["class"]:
                return list(xref(s))

        for s in self.article.select("div.section"):
            txt = s.find("h2").string.lower()
            if txt.find("references") >= 0:
                return list(xref(s))
        return None


class GenerateASPB(Generate):
    cc = set()

    def create_clean(self, soup, pmid):
        aspb = ASPB(soup)
        a = soup.select("div.article.fulltext-view")[0]
        for sec in a.select("div.section"):
            for c in sec.attrs["class"]:
                self.cc.add(c)
            n = sec.find("h2")
            if n:
                txt = n.text  # .lower()
                self.cc.add(txt)
        return aspb


def gen_aspb(issn):
    e = GenerateASPB(issn)
    e.run()
    print(e.cc)


def html_aspb(issn):
    e = GenerateASPB(issn)
    print(e.tohtml())


if __name__ == "__main__":
    download_aspb(sleep=60.0 * 2, mx=0, issn="1040-4651")
    download_aspb(sleep=60.0 * 2, mx=0, issn="1532-298X")  # web issn for the plant cell
    download_aspb(sleep=60.0 * 2, mx=0, issn="0032-0889")
    download_aspb(
        sleep=60.0 * 2, mx=0, issn="1532-2548"
    )  # web issn for plant physiology
    # gen_aspb(issn='1040-4651')
    # gen_aspb(issn='0032-0889')
    # gen_aspb(issn='1532-298X')  # web issn for the plant cell
    # gen_aspb(issn='1532-2548')
