from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Location:
    article_css: str
    remove_css: str = ""
    wait_css: str = ""


WILEY = Location(
    ".article__body",
    "section.article-section__references,section.article-section__citedBy",
)

OUP = Location(
    ".widget-ArticleFulltext.widget-instance-OUP_Article_FullText_Widget",
    ".ref-list",
)

PlantPhysiol = Location(".widget-instance-OUP_Article_FullText_Widget", ".ref-list")
PlantCell = PlantPhysiol
JBioChem = Location(
    "article .Abstracts,article .Body",
    "",
    "article section.bibliography",
)
FrontPlantSci = Location(".JournalFullText .JournalFullText", ".References")
SciRep = Location(".main-content")
PLoSONE = Location(".article-content", "ol.references")
PlantJ = WILEY
FEBSLet = WILEY
PhysiolPlant = WILEY
PlantCellEnviron = WILEY
Cell = JBioChem
EMBOJ = Location("main article", 'section[data-extent="backmatter"],.citations')
GeneDev = Location("div.article.fulltext-view")
ProcNatlAcadSciUSA = Location(
    'main article section[data-extent="frontmatter"], main article section[data-extent="bodymatter"]',
    'section[data-extent="backmatter"],.citations',
)

JCellSci = Location(
    ".widget-ArticleFulltext.widget-instance-ArticleFulltext",
    'h2[data-section-title="References"] ~ div',
)
IntJMolSci = Location("article .html-body section")
JExpBot = OUP
DATA = {
    "1532-2548": PlantPhysiol,
    "1365-313X": PlantJ,
    "1873-3468": FEBSLet,
    "1664-462X": FrontPlantSci,
    "2045-2322": SciRep,
    "1532-298X": PlantCell,
    "1932-6203": PLoSONE,
    "1399-3054": PhysiolPlant,
    "1365-3040": PlantCellEnviron,
    "0021-9258": JBioChem,
    "0960-7412": PlantJ,
    "0032-0889": PlantPhysiol,
    "1040-4651": PlantCell,
    "0092-8674": Cell,
    "0261-4189": EMBOJ,
    "0014-5793": FEBSLet,
    "0890-9369": GeneDev,
    "0027-8424": ProcNatlAcadSciUSA,
    "1477-9137": JCellSci,
    "1422-0067": IntJMolSci,
    "1460-2431": JExpBot,
}
