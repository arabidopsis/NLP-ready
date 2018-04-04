import re
from jinja2 import Markup
# [SIC!] unicode dashes utf-8 b'\xe2\x80\x90' 0x2010
PRIMER = re.compile(
    r'''\b((?:5[′'][-‐]?)?[CTAG\s-]{7,}[CTAG](?:[-‐]?3[′'])?)(\b|$|[\s;:)/,\.])''', re.I)
pf = r'[0-9]+(?:\.[0-9]+)?'
number = r'[+-]?' + pf + r'(?:\s*±\s*' + pf + r')?'
pm = r'[0-9]+(?:\s*±\s*[0-9]+)?'
TEMP = re.compile(number + r'\s*°C')
MM = re.compile(number + r'\s*μ[Mm]')
MGL = re.compile(number + r'\s*mg/l')

N = re.compile(number + r'(?:\s|-)?(°C|μM|μl|mg/l|%|mM|nM|rpm|ml|NA|h|K|M|min|g/l|s|kb|μg/μl|μg)\b')
FPCT = re.compile(r'[0-9]+\.[0-9]*%')
PCT = re.compile(pm + '%')
PH = re.compile(r'\bpH\s*' + number)
INT = re.compile(r'\b[0-9]+\b')  # picks up ncb-111 !!!!
FLOAT = re.compile(r'\b[0-9]+\.[0-9]*\b')

INT = re.compile(r'\s[0-9]+(?=\s)')  # [sic] spaces. \b picks up ncb-111 !!!!
FLOAT = re.compile(r'\s[0-9]+\.[0-9]*(?=\s)')
EXP = re.compile(r'\b[0-9]+(?:\.[0-9]*)?\s*×\s*(e|E|10)[+−-]?[0-9]+\b')
EXP2 = re.compile(r'\b[0-9]+\.[0-9]*(?:e|E|10)[+−-]?[0-9]+\b')


def reduce_nums(txt):
    txt = N.sub(r'NUMBER_\1', txt)
    txt = PH.sub(r'NUMBER_pH', txt)
    txt = FPCT.sub(r'NUMBER_%', txt)
    txt = PCT.sub(r'NUMBER_%', txt)
    txt = EXP.sub('EXPNUM', txt)
    txt = EXP2.sub(' EXPNUM', txt)
    txt = FLOAT.sub(' FLOAT ', txt)
    txt = INT.sub(' INT ', txt)
    return txt


def find_primers(txt):
    # txt = reduce_nums(txt)

    return Markup(PRIMER.sub(r'<b class="primer">\1</b>\2', txt))
