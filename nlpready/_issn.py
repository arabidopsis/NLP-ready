from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Location:
    article_css: str
    remove_css: str = ""
    wait_css: str = ""


# Generics

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
SPRINGER2 = Location("article main .c-article-body", 'section[data-title="References"]')
PLOSONE = Location(".article-content", "ol.references")
TAYLORFRANCIS = Location("article.article", 'div[id="references-Section"]')
SCIENCEDIRECT = Location(
    "article .Abstracts,article .Body",
    "",
    "article section.bibliography",
)
NATURE = Location("article div.c-article-body", 'section[data-title="References"]')

####

JBioChem = SCIENCEDIRECT  # Location("article .Abstracts,article .Body","", "article section.bibliography")
JBiolChem = SCIENCEDIRECT
Virology = SCIENCEDIRECT
MolCellProteomics = SCIENCEDIRECT
Mitochondrion = SCIENCEDIRECT
JPlantPhysiol = SCIENCEDIRECT
JStructBiol = SCIENCEDIRECT
MolCells = SCIENCEDIRECT
Gene = SCIENCEDIRECT
Cell = SCIENCEDIRECT


PlantJ = WILEY
FEBSLet = WILEY
PhysiolPlant = WILEY
PlantCellEnviron = WILEY
JIntegrPlantBiol = WILEY
Proteomics = WILEY
NewPhytol = WILEY
MolPlantPathol = WILEY
ScientificWorldJournal = WILEY
FEBSJ = WILEY
Traffic = WILEY

JProteomics = CELL
PlantSci = CELL
MolPlant = CELL
BiochemBiophysResCommun = CELL
PlantPhysiolBiochem = CELL
Phytochemistry = CELL
CurrBiol = CELL
BiochimBiophysActa = CELL

JExpBot = OUP
PlantCellPhysiol = OUP
BiosciBiotechnolBiochem = OUP
Genetics = OUP
AnnBot = OUP
NucleicAcidsRes = OUP

PlantReprod = SPRINGER2
PhotosynRes = SPRINGER2
PlantCellRep = SPRINGER2
MolBiolRep = SPRINGER2
Protoplasma = SPRINGER
PlantMolBiol = SPRINGER
JPlantRes = SPRINGER

PLoSONE = PLOSONE
PLoSGenet = PLOSONE
PLoSBiol = PLOSONE
PLoSPathog = PLOSONE


BMCPlantBiol = BMC
BMCResNotes = BMC

PlantSignalBehav = TAYLORFRANCIS
RNABiol = TAYLORFRANCIS


Nature = NATURE
NatCommun = NATURE
CellRes = NATURE

ProcNatlAcadSciUSA = Location(
    'main article section[data-extent="frontmatter"], main article section[data-extent="bodymatter"]',
    'section[data-extent="backmatter"],.citations',
)
ProcNatlAcadSciUSA2 = Location(
    'main article section[id="abstract"],main article section[id="bodymatter"]',
)
JVirol = ProcNatlAcadSciUSA2

Science = Location(
    'main article section[id="abstract"],main article section[id="bodymatter"]',
)
MolSystBiol = Science

EMBOJ = Location('div[id="abstract"],main article section[data-extent="bodymatter"]')
EMBORep = EMBOJ
# EMBOJ = Location("main article", 'section[data-extent="backmatter"],.citations')

PlantPhysiol = Location(".widget-instance-OUP_Article_FullText_Widget", ".ref-list")
PlantCell = PlantPhysiol

JProteomeRes = Location(
    "main article .article_abstract,main article .article_content",
    "ol#references,.articleCitedByDropzone .cited-by",
)
Biochemistry = JProteomeRes

FrontPlantSci = Location(".JournalFullText .JournalFullText", ".References")
FrontCellDevBiol = FrontPlantSci

SciRep = Location(".main-content")
GeneDev = Location("div.article.fulltext-view")
JCellSci = Location(
    ".widget-ArticleFulltext.widget-instance-ArticleFulltext",
    'h2[data-section-title="References"] ~ div',
)
JCellBiol = Location(
    ".widget-ArticleFulltext.widget-instance-ArticleFulltext_SplitView",
    'h2[data-section-title="References"] ~ div',
)
IntJMolSci = Location("article .html-body section")


MolPlantMicrobeInteract = Location("main article .article__body")
Planta = Location('article section[data-title="Abstract"],article .main-content')
RNA = Location(
    ".article",
    ".section.ref-list",
)  # full-text is on different page with .full attached to url
BiochemJ = Location(
    ".widget-ArticleFulltext.widget-instance-ArticleFulltext",
    ".ref-list",
)
Elife = Location("main .main-content-grid", 'section[id="references"]')
MolBiolCell = Location("main article .article__body", "ul.references")  # Blocks?
Development = Location(
    ".widget-ArticleMainView.widget-instance-ArticleMainView_Article",
    # SIC!!!!
    'h2[data-section-title="<strong>References</strong>"]',
)
MolBiosyst = Location(
    "article.article-control",
    ".ref-list,.article__authors,.drawer-control.fixpadv--m",
)


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
    "1460-2075": EMBOJ,
    "1469-3178": EMBORep,
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
    "1091-6490": ProcNatlAcadSciUSA2,
    "1096-0341": Virology,
    "1756-0500": BMCResNotes,
    "1876-7737": JProteomics,
    "2194-7961": PlantReprod,
    "1535-9484": MolCellProteomics,
    "1873-2259": PlantSci,
    "1573-5079": PhotosynRes,
    "1943-2631": Genetics,
    "1432-203X": PlantCellRep,
    "1469-9001": RNA,
    "1470-8728": BiochemJ,
    "2050-084X": Elife,
    "1540-8140": JCellBiol,
    "1097-4172": Cell,
    "1872-8278": Mitochondrion,
    "1095-8290": AnnBot,
    "1618-1328": JPlantPhysiol,
    "1553-7374": PLoSPathog,
    "1537-744X": ScientificWorldJournal,
    "1095-8657": JStructBiol,
    "1879-0038": Gene,
    "1520-4995": Biochemistry,
    "1098-5514": JVirol,
    "1939-4586": MolBiolCell,  # driver.get BLOCKS!
    "1477-9129": Development,
    "1364-3703": MolPlantPathol,
    "1742-2051": MolBiosyst,
    "1095-9203": Science,
    "1742-4658": FEBSJ,
    "1362-4962": NucleicAcidsRes,
    "1748-7838": CellRes,
    "1600-0854": Traffic,
    "1573-4978": MolBiolRep,
    "1744-4292": MolSystBiol,
    "0219-1032": MolCells,
}
