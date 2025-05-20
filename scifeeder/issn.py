from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class Location:
    article_css: str
    remove_css: str = ""
    wait_css: str = ""
    pdf_accessible: bool = False

    def full(self, url: str) -> str:
        return url

    def pdf(self, soup: BeautifulSoup, url: str) -> bytes | None:
        return None


@dataclass
class RNALocation(Location):
    def full(self, url: str) -> str:
        return url + ".full"


@dataclass
class NatureLocation(Location):
    def __post_init__(self):
        self.pdf_accessible = True

    def pdf(self, soup: BeautifulSoup, url: str) -> bytes | None:
        a = soup.select('a[data-article-pdf="true"]')[0]
        href = a.get("href")
        c = urlparse(url)
        u = f"{c.scheme}://{c.netloc}{href}"
        resp = requests.get(u)
        return resp.content


# Generics

WILEY = Location(
    ".article__body",
    "section.article-section__references,section.article-section__citedBy",
)

OUP = Location(
    ".widget-ArticleFulltext.widget-instance-OUP_Article_FullText_Widget",
    ".ref-list",
)
BMC = Location(
    "main > article",
    'section[data-title="References"],.c-article-author-list,.c-article-info-details,.c-article-metrics-bar__wrapper',
)
SPRINGER = Location("article main .c-article-body", 'section[data-title="Reference"]')
SPRINGER2 = Location(
    "article main .c-article-body",
    'section[data-title="References"],section[data-title="REFERENCES"]',
)
PLOSONE = Location(".article-content", "ol.references")
TAYLORFRANCIS = Location("article.article", 'div[id="references-Section"]')
CELL = SCIENCEDIRECT = Location(
    "article .Abstracts,article .Body",
    "",
    "article section.bibliography",
)
NATURE = NatureLocation(
    "article div.c-article-body",
    'section[data-title="References"],section[data-track-component="inline-recommendations"],section[aria-labelledby="content-related-subjects"]',
)

ASMJournals = Location(
    'main article [id="abstracts"], main article section[data-extent="bodymatter"]',
)

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
DevCell = SCIENCEDIRECT
MolCell = SCIENCEDIRECT
JMolBiol = SCIENCEDIRECT
EurJCellBiol = SCIENCEDIRECT
JChromatogrA = SCIENCEDIRECT
CellHostMicrobe = SCIENCEDIRECT
ExpCellRes = SCIENCEDIRECT
FoodMicrobiol = SCIENCEDIRECT
AnalBiochem = SCIENCEDIRECT
CellStressChaperones = SCIENCEDIRECT
DevBiol = SCIENCEDIRECT
TrendsPlantSci = SCIENCEDIRECT
ArchBiochemBiophys = SCIENCEDIRECT
BiophysJ = SCIENCEDIRECT
MolCellBiolResCommun = SCIENCEDIRECT
ProteinExprPurif = SCIENCEDIRECT

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
EurJBiochem = WILEY
CellBiolInt = WILEY
GenesCells = WILEY
CellMotilCytoskeleton = WILEY
Electrophoresis = WILEY
PlantBiotechnolJ = WILEY
IntEndodJ = WILEY
PlantBiol_Stuttg_ = WILEY
JCellBiochem = WILEY
Genesis = WILEY

JProteomics = CELL
PlantSci = CELL
MolPlant = CELL
BiochemBiophysResCommun = CELL
PlantPhysiolBiochem = CELL
Phytochemistry = CELL
CurrBiol = CELL
CurrBiol2 = SCIENCEDIRECT
BiochimBiophysActa = CELL

JExpBot = OUP
PlantCellPhysiol = OUP
BiosciBiotechnolBiochem = OUP
Genetics = OUP
AnnBot = OUP
NucleicAcidsRes = OUP
JBiochem = OUP
Glycobiology = OUP
DNARes = OUP
FEMSYeastRes = OUP
MolBiolEvol = OUP


PlantReprod = SPRINGER2
PhotosynRes = SPRINGER2
PlantCellRep = SPRINGER2
MolBiolRep = SPRINGER2
Protoplasma = SPRINGER
Protoplasma2 = SPRINGER2
PlantMolBiol = SPRINGER2
PlantMolBiol2 = SPRINGER2
JPlantRes = SPRINGER
JPlantRes2 = SPRINGER2
Springerplus = Location(
    "main article",
    'section[data-title="References"],.c-article-header',
)
FunctIntegrGenomics = SPRINGER2


PLoSONE = PLOSONE
PLoSGenet = PLOSONE
PLoSBiol = PLOSONE
PLoSPathog = PLOSONE


BMCPlantBiol = BMC
BMCResNotes = BMC
GenomeBiol = BMC
BMCGenomics = BMC
BMCBiotechnol = BMC
PlantMethods = BMC
BMCBiochem = BMC

PlantSignalBehav = TAYLORFRANCIS
RNABiol = TAYLORFRANCIS
MolCellBiol = TAYLORFRANCIS
MolMembrBiol = TAYLORFRANCIS


Nature = NATURE
NatCommun = NATURE
CellRes = NATURE
NatCellBiol = NATURE
MolGenetGenomics = NATURE
NatBiotechnol = NATURE
CellMolLifeSci = NATURE
Chromosoma = NATURE
DevGenesEvol = NATURE
CellDeathDiffer = NATURE
ApplMicrobiolBiotechnol = NATURE
TheorApplGenet = NATURE
CurrGenet = NATURE
MolGenGenet = NATURE
JMolEvol = NATURE

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

# 1460-2075
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
JCellBiol2 = Location(
    ".widget-ArticleFulltext.widget-instance-ArticleFulltext_SplitView",
    ".ref-list",
)
IntJMolSci = Location("article .html-body section")


MolPlantMicrobeInteract = Location("main article .article__body")
Planta = Location('article section[data-title="Abstract"],article .main-content')
RNA = RNALocation(
    ".article",
    ".section.ref-list",
)  # full-text is on different page with .full attached to url
GenesDev = RNA

BiochemJ = Location(
    ".widget-ArticleFulltext.widget-instance-ArticleFulltext",
    ".ref-list",
)
BiochemSocTrans = BiochemJ

Elife = Location("main .main-content-grid", 'section[id="references"]')
MolBiolCell = Location("main article .article__body", "ul.references")  # Blocks?
Development = Location(
    ".widget-ArticleMainView.widget-instance-ArticleMainView_Article",
    # SIC!!!!
    'h2[data-section-title="<strong>References</strong>"] ~ div',
)
Development2 = Location(
    ".widget-ArticleMainView.widget-instance-ArticleMainView_Article",
    # SIC!!!!
    'h2[data-section-title="References"] ~ div',
)
MolBiosyst = Location(
    "article.article-control",
    ".ref-list,.article__authors,.drawer-control.fixpadv--m",
)

IntJArtifOrgans = ASMJournals
JBacteriol = ASMJournals


@dataclass
class JStage(Location):
    def full(self, url: str) -> str:
        return url.replace("/_article", "/_html/-char/en?legacy=True")


CellStructFunct = JStage("body", 'a[name="references"] ~ table')
GenesGenetSyst = CellStructFunct

AnnuRevPlantBiol = Location(
    "div#html-body",
    "span.references,div.menuButton,div.dropDownMenu,ul.article-header-metadata,.article-title-and-authors",
)
JGenVirol = AnnuRevPlantBiol

DATA: dict[str, Location] = {
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
    "2193-1801": Springerplus,
    "1476-4679": NatCellBiol,
    "0950-1991": Development2,
    "0167-4412": PlantMolBiol2,
    "0032-0781": PlantCellPhysiol,
    "0022-0957": JExpBot,
    "0032-0935": Planta,
    "0960-9822": CurrBiol2,
    "1059-1524": MolBiolCell,
    "0021-9533": JCellSci,
    "1535-9476": MolCellProteomics,
    "0028-0836": Nature,
    "1674-2052": MolPlant,
    "1535-3893": JProteomeRes,
    "1742-464X": FEBSJ,
    "0006-291X": BiochemBiophysResCommun,
    "1534-5807": DevCell,
    "1617-4615": MolGenetGenomics,
    "0916-8451": BiosciBiotechnolBiochem,
    "0021-9525": JCellBiol2,
    "0378-1119": Gene,
    "0264-6021": BiochemJ,
    "0036-8075": Science,
    "0981-9428": PlantPhysiolBiochem,
    "0033-183X": Protoplasma2,
    "0918-9440": JPlantRes2,
    "1097-2765": MolCell,
    "0270-7306": MolCellBiol,
    "1469-221X": EMBORep,
    "1465-7392": NatCellBiol,
    "1615-9853": Proteomics,
    "0014-2956": EurJBiochem,
    "1089-8638": JMolBiol,
    "0721-7714": PlantCellRep,
    "0028-646X": NewPhytol,
    "0140-7791": PlantCellEnviron,
    "1355-8382": RNA,
    "0022-2836": JMolBiol,
    "1474-760X": GenomeBiol,
    "0042-6822": Virology,
    "0016-6731": Genetics,
    "1065-6995": CellBiolInt,
    "1098-5549": MolCellBiol,
    "1001-0602": CellRes,
    "1356-9597": GenesCells,
    "1087-0156": NatBiotechnol,
    "1438-793X": FunctIntegrGenomics,
    "0031-9422": Phytochemistry,
    "0886-1544": CellMotilCytoskeleton,
    "0006-2960": Biochemistry,
    "0300-5127": BiochemSocTrans,
    "1420-682X": CellMolLifeSci,
    "0173-0835": Electrophoresis,
    "0171-9335": EurJCellBiol,
    "1756-2651": JBiochem,
    "1467-7652": PlantBiotechnolJ,
    "1724-6040": IntJArtifOrgans,
    "1438-7948": FunctIntegrGenomics,
    "1432-0886": Chromosoma,
    "1873-3778": JChromatogrA,
    "1365-2591": IntEndodJ,
    "1097-4164": MolCell,
    "1460-2423": Glycobiology,
    "1756-1663": DNARes,
    "1522-2683": Electrophoresis,
    "1934-6069": CellHostMicrobe,
    "1559-2316": PlantSignalBehav,
    "1567-1364": FEMSYeastRes,
    "1549-5477": GenesDev,
    "1617-4623": MolGenetGenomics,
    "1347-3700": CellStructFunct,
    "1090-2422": ExpCellRes,
    "1095-9998": FoodMicrobiol,
    "1471-2164": BMCGenomics,
    "1537-1719": MolBiolEvol,
    "1096-0309": AnalBiochem,
    "1466-1268": CellStressChaperones,
    "1095-564X": DevBiol,
    "0949-944X": DevGenesEvol,
    "1472-6750": BMCBiotechnol,
    "0968-7688": MolMembrBiol,
    "1435-8603": PlantBiol_Stuttg_,
    "1746-4811": PlantMethods,
    "1543-5008": AnnuRevPlantBiol,
    "1047-8477": JStructBiol,
    "0305-7364": AnnBot,
    "1360-1385": TrendsPlantSci,
    "0003-9861": ArchBiochemBiophys,
    "1350-9047": CellDeathDiffer,
    "0175-7598": ApplMicrobiolBiotechnol,
    "0022-538X": JVirol,
    "0386-7196": CellStructFunct,
    "0006-3495": BiophysJ,
    "0021-9193": JBacteriol,
    "0040-5752": TheorApplGenet,
    "0009-5915": Chromosoma,
    "0730-2312": JCellBiochem,
    "1471-2091": BMCBiochem,
    "1526-954X": Genesis,
    "1340-2838": DNARes,
    "0172-8083": CurrGenet,
    "0022-1317": JGenVirol,
    "1522-4724": MolCellBiolResCommun,
    "1341-7568": GenesGenetSyst,
    "0026-8925": MolGenGenet,
    "0305-1048": NucleicAcidsRes,
    "1046-5928": ProteinExprPurif,
    "0022-2844": JMolEvol,
}
