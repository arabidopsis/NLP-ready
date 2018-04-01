import click
from mlabc import Generate

# add module name to this list...

MODS = [
    "ascb",
    "aspb",
    "bbb",
    "bioj",
    "bmcpb",
    # "cell", # cell needs chromedriver... run python3 cell.py download
    "dev",
    "elsevier",
    "emboj",
    "epmc",
    "fpls",
    "gad",
    "genetics",
    "jbc",
    "jcs",
    "jproteome",
    "mcp",
    "mpmi",
    "nature",
    "oup",
    "plos",
    "pnas",
    "science",
    "springer",
    "wiley",
]


def getmod(mod):
    m = __import__(mod)
    if '.' in mod:
        _, mname = mod.rsplit('.', 1)
        m = getattr(m, mname)
    issn = m.ISSN
    ret = dict(issn=issn)
    for name in dir(m):
        a = getattr(m, name)
        if name.startswith(('download_', 'html_', 'gen_')):
            if name[0] == 'd':
                ret['download'] = a
            if name[0] == 'h':
                ret['html'] = a
            if name[0] == 'g':
                ret['gen'] = a
        elif isinstance(a, type) and Generate in a.__bases__:
            a = getattr(m, name)
            ret['Generate'] = a
    return ret


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


@click.group()
def cli():
    pass


@cli.command()
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


@cli.command()
@click.option('--mod', help='modules to run')
@click.option('--nowrite', is_flag=True, help='don\'t overwrite')
def clean(mod='', nowrite=False):
    if mod:
        mods = [s.strip() for s in mod.split(',')]
    else:
        mods = MODS
    for m in mods:
        d = getmod(m)
        for i in d['issn']:
            print('writing ', m, i)
            g = d['Generate'](i)
            # print('overwrite', not nowrite)
            g.run(overwrite=not nowrite, prefix=m)


@cli.command()
@click.option('--mod', help='modules to run')
@click.option('--sleep', default=10., help='wait sleep seconds between requests', show_default=True)
@click.option('--mx', default=3, help='max documents to download 0=all')
def download(mod='', sleep=10., mx=1):
    """Download html/xml from websites."""
    if mod:
        mods = [s.strip() for s in mod.split(',')]
    else:
        mods = MODS
    for m in mods:
        d = getmod(m)
        for issn in d['issn']:
            print('downloading:', m, issn)
            d['download'](issn, sleep=sleep, mx=mx)


if __name__ == '__main__':
    cli()
