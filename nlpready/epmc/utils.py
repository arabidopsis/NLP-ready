from __future__ import annotations

import re

from lxml import etree
from lxml.etree import Element

NS = {
    "xlink": "http://www.w3.org/1999/xlink",
    "mml": "http://www.w3.org/1998/Math/MathML",
    "ali": "http://www.niso.org/schemas/ali/1.0/",
}
NSRE = re.compile("^{([^}]+)}(.*)$")

HTMLTAGS = {
    "a",
    "abbr",
    "address",
    "area",
    "article",
    "aside",
    "audio",
    "b",
    "base",
    "bdi",
    "bdo",
    "blockquote",
    "body",
    "br",
    "button",
    "canvas",
    "caption",
    "cite",
    "code",
    "col",
    "colgroup",
    "data",
    "datalist",
    "dd",
    "del",
    "details",
    "dfn",
    "dialog",
    "div",
    "dl",
    "dt",
    "em",
    "embed",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hgroup",
    "hr",
    "html",
    "i",
    "iframe",
    "img",
    "input",
    "ins",
    "kbd",
    "label",
    "legend",
    "li",
    "link",
    "main",
    "map",
    "mark",
    "math",
    "menu",
    "meta",
    "meter",
    "nav",
    "noscript",
    "object",
    "ol",
    "optgroup",
    "option",
    "output",
    "p",
    "picture",
    "pre",
    "progress",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "script",
    "search",
    "section",
    "select",
    "slot",
    "small",
    "source",
    "span",
    "strong",
    "style",
    "sub",
    "summary",
    "sup",
    "svg",
    "table",
    "tbody",
    "td",
    "template",
    "textarea",
    "tfoot",
    "th",
    "thead",
    "time",
    "title",
    "tr",
    "track",
    "u",
    "ul",
    "var",
    "video",
    "wbr",
}

PMCTAGS = {
    "p": "p",
    "italic": "i",
    "bold": "b",
    "ref-list": "ol",
    "ref": "li",
    "sec": "div",
    "title": "h2",
    "ext-link": "a",
    "body": "div",
    "abstract": "div",
    "caption": "div",
    "xref": "a",
    "fig": "div",
    "pub-id": "a",
    "sup": "sup",
    "sub": "sub",
    "label": "span",
    "article-title": "i",
    "graphic": "a",
    "article-id": "a",
    "license": "div",
    "journal-meta": "div",
    "list": "ul",
    "list-item": "li",
    "media": "a",
    "object-id": "a",
    "def-list": "dl",
    "term": "dt",
    "def": "dd",
    "table": "table",
    "colgroup": "colgroup",
    "tbody": "tbody",
    "tr": "tr",
    "th": "th",
    "td": "td",
    "col": "col",
    "email": "span",
    "title-group": "h1",
    "article": "article",
    "article-meta": "div",
}

MISSING = set()


class Events:
    TAGS: dict[str, str] = {}

    def findmatches(self, text):
        return [(None, text)]

    def parse(self, fp):
        # pylint: disable=too-many-branches
        # counts = Counter()

        for e, elem in etree.iterparse(fp, events=("start", "end")):
            if e == "start":
                tag = elem.tag
                m = NSRE.match(tag)
                if m:
                    _, tag = m.group(1, 2)
                stag = "start_" + tag.replace("-", "_")

                if hasattr(self, stag):
                    yield getattr(self, stag)(elem)

                else:
                    if tag not in self.TAGS:
                        if tag in HTMLTAGS:
                            etag = tag
                        else:
                            etag = "span"
                            MISSING.add(tag)
                    else:
                        etag = self.TAGS[tag]
                    yield f'<{etag} class="{tag}">'

                if elem.text:
                    for name, match in self.findmatches(elem.text):
                        if name:
                            # counts[name] += 1
                            yield f'<b class="{name}">{match}</b>'
                        else:
                            yield match

            elif e == "end":
                tag = elem.tag
                m = NSRE.match(tag)
                if m:
                    tag = m.group(2)
                stag = "end_" + tag.replace("-", "_")
                if hasattr(self, stag):
                    yield getattr(self, stag)(elem)
                else:
                    if tag not in self.TAGS:
                        if tag in HTMLTAGS:
                            etag = tag
                        else:
                            etag = "span"
                    else:
                        etag = self.TAGS[tag]
                    yield "</%s> " % etag  # [sic!] add space
                if elem.tail:
                    yield elem.tail
                    # for name, match in cvt(elem.tail):
                    #     if name:
                    #         # counts[name] += 1
                    #         yield f'<b class="{name}">{match}</b>'
                    #     else:
                    #         yield match
            else:
                RuntimeError("what event %s?" % e)

        # yield '<ul class="counts">'
        # for name in counts:
        #     yield "<li>%s:%d</li>" % (name, counts[name])
        # yield "</ul>"


class PMCEvents(Events):
    TAGS = PMCTAGS

    def __init__(self):
        self.sec = [0]
        self.pub_loc = None

    # def findmatches(self, text: str) -> Iterator[tuple[str | None, str]]:
    #     yield from cvt(text)

    def start_xref(self, elem: Element) -> str:
        rid = elem.attrib["rid"]
        return '<a class="xref" href="#%s">' % (rid)

    def start_ref(self, elem: Element) -> str:
        rid = elem.attrib["id"]
        return '<li class="ref" id="%s">' % (rid)

    def start_fig(self, elem: Element) -> str:
        rid = elem.attrib["id"]
        return '<div class="fig" id="%s">' % (rid)

    def start_article_id(self, elem: Element) -> str:
        return "<b>article id:</b> " + self._pub_id(elem, "article-id")

    def start_object_id(self, elem: Element) -> str:
        if not elem.text.startswith(("https://", "http://")):
            href = "https://dx.doi.org/" + elem.text
        else:
            href = elem.text
        return '<a target="xref" class="object-id" href="%s">' % href

    def start_pub_id(self, elem: Element) -> str:
        return self._pub_id(elem, "pub-id")

    def _pub_id(self, elem: Element, name: str) -> str:
        # pylint: disable=line-too-long
        pid = elem.attrib.get("pub-id-type")
        if pid == "doi":
            return f'{pid}: <a target="xref" class="{name} {pid}" href="https://dx.doi.org/{elem.text}">'
        if pid == "pmid":
            return f'{pid}: <a target="xref" class="{name} {pid}" href="https://eutils.ncbi.nlm.nih.gov/pubmed/{elem.text}">'

        if pid == "pmcid":
            return f'{pid}: <a target="xref" class="{name} {pid}" href="https://ncbi.nlm.nih.gov/pmc/articles/PMC{elem.text}">'

        return f'{pid}: <a target="xref" class="{name} {pid}" href="#{elem.text}">'

    def start_sec(self, elem: Element) -> str:
        mm = elem.attrib.get("sec-type")
        self.sec[-1] += 1
        sec = ".".join(str(d) for d in self.sec)
        self.sec.append(0)
        mm = " " + mm.replace("|", "-") if mm else ""
        # return f'<hr/>sec: {sec}<div class="sec{mm} sec{len(sec) - 1}">'
        return f'<hr/><div class="sec{mm} sec{len(sec) - 1}">'

    def end_sec(self, elem: Element) -> str:
        self.sec.pop()
        return "</div>"

    def start_aff(self, elem: Element) -> str:
        iid = elem.attrib.get("id")
        return ('<span class="aff" id="%s">' % iid) if iid else '<span class="aff" >'

    def start_abstract(self, elem: Element) -> str:
        return '<hr/><h2>Abstract</h2><div class="abstract">'

    def start_ext_link(self, elem: Element) -> str:
        href = elem.attrib.get("{%s}href" % NS["xlink"])
        if not href:
            return '<a class="ext-link error" href="#">No Link for ext-link! %s' % str(
                elem.attrib,
            )

        return '<a target="ext-link" class="ext-link" href="%s">' % href

    def start_graphic(self, elem: Element) -> str:
        href = elem.attrib.get("{%s}href" % NS["xlink"])
        if not href:
            return '<a class="graphic error" href="#">No Link for graphic! %s' % str(
                elem.attrib,
            )
        if self.pub_loc:
            href = self.pub_loc + "/" + href
        return f'graphic: <a target="ext-link" class="graphic" href="{href}">{href}'

    def start_label(self, elem: Element) -> str:
        return '<span class="label label-default">'

    def start_license(self, elem: Element) -> str:
        href = elem.attrib.get(f"{NS['xlink']}href")
        if not href:
            return (
                '<div class="license error"><a href="#">No Link for license! %s</a>'
                % str(elem.attrib)
            )
        return (
            '<div class="license"><a target="ext-link" class="graphic" href="%s">license</a> '
            % (href)
        )

    def start_media(self, elem: Element) -> str:
        href = elem.attrib.get("{%s}href" % NS["xlink"])
        if not href:
            return (
                'media: <a target="ext-link error" class="media" href="#">no link for media %s'
                % str(elem.attrib)
            )
        if self.pub_loc:
            href = self.pub_loc + "/" + href
        return f'media: <a target="ext-link" class="media" href="{href}">{href}'
