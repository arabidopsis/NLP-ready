import click
from mlabc import Generate


MODS = [
    "ascb",
    "aspb",
    "bioj",
    "cell",
    "dev",
    "elsevier",
    "emboj",
    "epmc",
    "gad",
    "jbc",
    "jcs",
    "mcp",
    "nature",
    "oup",
    "plos",
    "pnas",
    "science",
    "springer",
    "wiley"
]


def getmod(mod):
    m = __import__(mod)
    issn = m.ISSN
    d = dict(issn=issn)
    for x in dir(m):
        a = getattr(m, x)
        if x.startswith(('download_', 'html_', 'gen_')):
            if x[0] == 'd':
                d['download'] = a
            if x[0] == 'h':
                d['html'] = a
            if x[0] == 'g':
                d['gen'] = a
        elif isinstance(a, type) and Generate in a.__bases__:
            a = getattr(m, x)
            d['Generate'] = a
    return d


def doubles():
    from summary import get_done
    from mlabc import read_journals_csv

    pmid2doi = read_journals_csv()
    res = get_done()
    papers = []
    for pmid in res:
        paper = pmid2doi[pmid]
        for issn in res[pmid]:
            d = getmod(issn)
            g = d['Generate'](issn)
            soup = g.get_soup(paper, pmid)
            e = g.create_clean(soup, pmid)
            papers.append((paper, e))


@click.command()
@click.option('--mod', help='modules to run')
def tohtml(mod=''):
    if mod:
        mods = [s.strip() for s in mod.split(',')]
    else:
        mods = MODS
    for m in mods:
        d = getmod(m)
        for i in d['issn']:
            print('writing ', m, i)
            g = d['Generate'](i)
            # try:
            g.tohtml(save=True, prefix='html/' + m + '_')
            # except Exception as e:
            #     click.secho("failed %s %s %s" % (m, i, str(e)), fg='magenta')
            #     raise e


if __name__ == '__main__':
    tohtml()
