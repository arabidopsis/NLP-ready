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
BMC = Location("main > article", 'section[data-title="References"]')
CELL = Location("article .Abstracts,article .Body", "", "article section.bibliography")
SPRINGER = Location("article main .c-article-body", 'section[data-title="Reference"]')
PLoSONE = Location(".article-content", "ol.references")
TAYLORFRANCIS = Location("article.article", 'div[id="references-Section"]')
ScienceDirect = Location(
    "article .Abstracts,article .Body",
    "",
    "article section.bibliography",
)
####
PlantPhysiol = Location(".widget-instance-OUP_Article_FullText_Widget", ".ref-list")
PlantCell = PlantPhysiol
JBioChem = ScienceDirect  # Location("article .Abstracts,article .Body","", "article section.bibliography")
FrontPlantSci = Location(".JournalFullText .JournalFullText", ".References")
SciRep = Location(".main-content")

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
JIntegrPlantBiol = WILEY
PlantCellPhysiol = OUP
NewPhytol = WILEY
Nature = Location("article div.c-article-body", 'section[data-title="References"]')
BMCPlantBiol = BMC
MolPlant = CELL
PlantSignalBehav = TAYLORFRANCIS
Proteomics = WILEY
BiochemBiophysResCommun = CELL
PlantPhysiolBiochem = CELL
Phytochemistry = CELL
PLoSGenet = PLoSONE
CurrBiol = CELL
NatCommun = Nature
Protoplasma = SPRINGER
PLoSBiol = PLoSONE
RNABiol = TAYLORFRANCIS
PlantMolBiol = SPRINGER
BiochimBiophysActa = CELL
JPlantRes = SPRINGER
BiosciBiotechnolBiochem = OUP
FrontCellDevBiol = FrontPlantSci
JProteomeRes = Location(
    "main article .article_abstract,main article .article_content",
    "ol#references,.articleCitedByDropzone .cited-by",
)

JBiolChem = ScienceDirect
MolPlantMicrobeInteract = Location("main article .article__body")
Planta = Location('article section[data-title="Abstract"],article .main-content')
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
    "1744-7909": JIntegrPlantBiol,
    "1471-9053": PlantCellPhysiol,
    "1469-8137": NewPhytol,
    "1476-4687": Nature,
    "1471-2229": BMCPlantBiol,
    "1752-9867": MolPlant,
    "1559-2324": PlantSignalBehav,
    "1615-9861": Proteomics,
    "1090-2104": BiochemBiophysResCommun,
    "1873-2690": PlantPhysiolBiochem,
    "1873-3700": Phytochemistry,
    "1553-7404": PLoSGenet,
    "1879-0445": CurrBiol,
    "2041-1723": NatCommun,
    "1615-6102": Protoplasma,
    "1545-7885": PLoSBiol,
    "1555-8584": RNABiol,
    "1573-5028": PlantMolBiol,
    "0006-3002": BiochimBiophysActa,
    "1618-0860": JPlantRes,
    "1347-6947": BiosciBiotechnolBiochem,
    "2296-634X": FrontCellDevBiol,
    "1535-3907": JProteomeRes,
    "1083-351X": JBiolChem,
    "0894-0282": MolPlantMicrobeInteract,
    "1432-2048": Planta,
}
