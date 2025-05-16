from __future__ import annotations

import re
from typing import IO
from typing import Iterator

from lxml import etree
from lxml.etree import Element

# from xml.etree import ElementTree as etree

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
    "bold": "strong",
    "ref-list": "ol",
    "ref": "li",
    "sec": "section",
    "title": "h2",
    "ext-link": "a",
    "uri": "a",
    "body": "main",
    "abstract": "div",
    "caption": "caption",
    "xref": "a",
    "fig": "figure",
    "pub-id": "a",
    "sup": "sup",
    "sub": "sub",
    "label": "label",
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
    "front": "div",
    "table-wrap": "div",
    "table-wrap-foot": "div",
    "break": "br",
}


class Events:
    TAGS = PMCTAGS

    def __init__(self):
        self.missing = set()

    def parse(self, fp: IO[bytes]) -> Iterator[str]:
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
                            self.missing.add(tag)
                    else:
                        etag = self.TAGS[tag]
                    if etag != tag:
                        yield f'<{etag} class="{tag}">'
                    else:
                        yield f"<{etag}>"

                if elem.text:
                    yield elem.text

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
                    if etag not in {
                        "hr",
                        "br",
                        "img",
                        "col",
                        "base",
                        "area",
                        "embed",
                        "input",
                    }:

                        yield f"</{etag}>"

                if elem.tail:
                    if elem.tail == "\n":
                        yield " "
                    else:
                        yield elem.tail
                elem.clear()
            else:
                RuntimeError(f"what event {e}?")


def gethref(elem: Element) -> str | None:
    # return elem.attrib.get("{%s}href" % NS["xlink"])
    return elem.attrib.get(f"{{{NS["xlink"]}}}href")


class PMCEvents(Events):

    def __init__(self, url: str | None = None):
        super().__init__()
        self.url = url

    def start_xref(self, elem: Element) -> str:
        rid = elem.attrib["rid"]
        return f'<a class="xref" href="#{rid}">'

    def start_ref(self, elem: Element) -> str:
        rid = elem.attrib["id"]
        return f'<li class="ref" id="{rid}">'

    def start_fig(self, elem: Element) -> str:
        rid = elem.attrib["id"]
        return f'<figure class="fig" id="{rid}">'

    def start_article_id(self, elem: Element) -> str:
        return "<b>article id:</b> " + self._pub_id(elem, "article-id")

    def end_article_id(self, elem) -> str:
        return "</a>"

    def start_object_id(self, elem: Element) -> str:
        if not elem.text.startswith(("https://", "http://")):
            href = "https://dx.doi.org/" + elem.text
        else:
            href = elem.text
        return f'<a target="xref" class="object-id" href="{href}">'

    def end_object_id(self, elem) -> str:
        return "</a>"

    def start_pub_id(self, elem: Element) -> str:
        return self._pub_id(elem, "pub-id")

    def end_pub_id(self, elem) -> str:
        return "</a>"

    def _pub_id(self, elem: Element, name: str) -> str:

        pid = elem.attrib.get("pub-id-type")
        if pid == "doi":
            return (
                f'{pid}: <a target="xref" class="{name} {pid}"'
                f' href="https://dx.doi.org/{elem.text}">'
            )

        if pid == "pmid":
            return (
                f'{pid}: <a target="xref" class="{name} {pid}"'
                f' href="https://eutils.ncbi.nlm.nih.gov/pubmed/{elem.text}">'
            )

        if pid == "pmcid":
            return (
                f'{pid}: <a target="xref" class="{name} {pid}"'
                f' href="https://ncbi.nlm.nih.gov/pmc/articles/PMC{elem.text}">'
            )

        return f'{pid}: <a target="xref" class="{name} {pid}" href="#{elem.text}">'

    def start_sec(self, elem: Element) -> str:
        mm = elem.attrib.get("sec-type")
        mm = "-" + mm.strip().replace("|", "-") if mm else ""
        return f'<hr/><section class="sec{mm}">'

    def start_aff(self, elem: Element) -> str:
        iid = elem.attrib.get("id")
        return f'<span class="aff" id="{iid}">' if iid else '<span class="aff" >'

    def end_aff(self, elem) -> str:
        return "</span>"

    def start_ext_link(self, elem: Element) -> str:
        type = elem.attrib.get("ext-link-type", "")
        return self._uri(elem, "ext-link", type=type)

    def start_uri(self, elem: Element) -> str:
        return self._uri(elem, "uri")

    def _uri(self, elem: Element, tag: str, type: str = "") -> str:
        href = gethref(elem)
        if not href:
            return f'<a class="{tag} error" href="#">{type} No Link for {tag}! {elem.attrib}'

        return f'<a target="{tag}" class="{tag}" href="{href}">{type} '

    def start_graphic(self, elem: Element) -> str:
        href = gethref(elem)
        if not href:
            return (
                f'<a class="graphic error" href="#">No Link for graphic! {elem.attrib}'
            )
        if self.url:
            href = self.url + "/" + href
        return f'graphic: <a target="ext-link" class="graphic" href="{href}">{href}'

    def start_license(self, elem: Element) -> str:
        href = gethref(elem)
        if not href:
            return f'<div class="license error"><a href="#">No Link for license! {elem.attrib}</a>'
        return f'<div class="license"><a target="ext-link" class="license" href="{href}">license</a>'

    def start_media(self, elem: Element) -> str:
        href = gethref(elem)
        if not href:
            return f'media: <a target="media" class="media errror" href="#">no link for media {elem.attrib}'
        if self.url:
            href = self.url + "/" + href
        return f'media: <a target="media" class="media" href="{href}">{href}'
