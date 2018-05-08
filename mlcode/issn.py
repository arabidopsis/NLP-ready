import click
import os
from pickle import load, dump
from collections import namedtuple

from mlabc import Generate, Config

# add module name to this list...

MODS = [
    "ascb",
    "aspb",
    "bbb",
    "bioj",
    "bmcpb",
    "cell",  # cell needs chromedriver... run python3 cell.py download
    "dev",
    "elife",
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
    "mdpi",
    "mpmi",
    "nature",
    "oup",
    "plos",
    "pnas",
    "science",
    "springer",
    "wiley",
]


KEYMAP = {'url': 0, 'mod': 1, 'issn': 2, 'done': 3, 'journal': 4, 'notok': 5, 'failed': 6}


Journal = namedtuple('Journal', ['url', 'mod', 'issn', 'ndone', 'journal', 'not_ok', 'nfailed'])


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
            # if name[0] == 'h':
            #     ret['html'] = a
            # if name[0] == 'g':
            #     ret['gen'] = a
        elif isinstance(a, type) and Generate in a.__bases__:
            a = getattr(m, name)
            ret['Generate'] = a
    return ret


def issn2mod():
    is2mod = {}
    for mod in MODS:
        m = getmod(mod)
        d = m['issn']
        for issn in d:
            is2mod[issn] = mod
    return is2mod


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
@click.option('--issn', help='journals to run')
@click.option('--sort', default='journal', help='sort on: ' + ','.join(KEYMAP))
@click.option('--num', is_flag=True, help='reduce numbers to NUMBER etc.')
@click.option('--cache', default=Config.PKLFILE, help='cached pickle file', show_default=True)
def tohtml(cache, issn=None, mod='', num=False, sort='journal'):
    """Generate HTML documents from downloads."""
    from mlabc import pmid2doi, make_jinja_env
    # from pickle import load, dump

    env = make_jinja_env()
    jdir = Config.DATADIR + 'html/journals'
    os.makedirs(jdir, exist_ok=True)

    template = env.get_template('index.html')
    if mod:
        mods = [s.strip() for s in mod.split(',')]
    else:
        mods = MODS
    if issn:
        issn = set(s.strip() for s in issn.split(','))
    # journals = []

    total1 = set()
    total2 = set()
    total3 = set()

    p2i = pmid2doi()
    issns = {p.issn: p.name for p in p2i.values() if not issn or p.issn in issn}
    issnmap = {}

    for mod in mods:
        d = getmod(mod)
        for issn in d['issn']:
            if issn not in issns and issn not in {'epmc', 'elsevier'}:  # no paper from this journal
                continue
            journal = issns.get(issn, issn)
            print('writing', mod, issn, journal)
            g = d['Generate'](issn, pmid2doi=p2i)
            # try:
            fname, papers, failed = g.tohtml(save=True, prefix=jdir + '/' + mod + '_',
                                             env=env, verbose=False, num=num)

            not_ok = len([p for p, s in papers if not s.has_all_sections()])
            apmids = [p.pmid for p, s in papers if s.has_all_sections()]
            tpmids = [p.pmid for p, s in papers]
            ndone = len(tpmids)
            i = fname.find('journals/')
            url = fname[i:]
            t = Journal(url=url, mod=mod, issn=issn, ndone=ndone,
                        journal=journal, not_ok=not_ok, nfailed=len(failed))
            # journals.append(t)
            for p in apmids:
                total1.add(p)
            for p in tpmids:
                total2.add(p)
            for p in tpmids:
                total3.add(p)

            issnmap[issn] = t

            # except Exception as e:
            #     click.secho("failed %s %s %s" % (m, i, str(e)), fg='magenta')
            #     raise e

    if os.path.exists(cache):
        with open(cache, 'rb') as fp:
            issnmap2 = load(fp)
        issnmap2.update(issnmap)  # overwrite
        issnmap = issnmap2

    with open(cache, 'wb') as fp:
        dump(issnmap, fp)

    journals = issnmap.values()

    def sortf():
        s = sort
        if sort[0] == '-':
            s = sort[1:]
        k = KEYMAP[s]
        if s == sort:
            return lambda t: t[k]
        else:
            return lambda t: -t[k]

    journals = sorted(journals, key=sortf())
    t = template.render(journals=journals, name=Config.NAME)

    with open(Config.DATADIR + 'html/index.html', 'w') as fp:
        fp.write(t)
    click.secho("found %d pubmeds. %d unique, %d usable" %
                (len(total3), len(total2), len(total1)), fg='blue')


@cli.command()
@click.option('--mod', help='modules to run')
def tokenize(mod=''):
    # from nltk import word_tokenize, PorterStemmer
    from collections import Counter
    if mod:
        mods = [s.strip() for s in mod.split(',')]
    else:
        mods = MODS
    cc = Counter()
    # porter = PorterStemmer()
    for m in mods:
        d = getmod(m)
        for i in d['issn']:
            print('tokenizing ', m, i)
            g = d['Generate'](i)
            # print('overwrite', not nowrite)
            for s, p in g.tokenize():
                for w in p.split():
                    while w.startswith(('(', '[')):
                        w = w[1:]
                    while w.endswith((')', ';', '.', ':', ',', ']')):
                        w = w[:-1]
                    # w = porter.stem(w)
                    cc[w] += 1

    for c in cc.most_common():
        print(c)


@cli.command()
@click.option('--mod', help='modules to run')
@click.option('--issn', help='journals to run')
@click.option('--nowrite', is_flag=True, help='don\'t overwrite')
@click.option('--num', is_flag=True, help='reduce numbers to NUMBER etc.')
def clean(num=False, issn='', mod='', nowrite=False):
    """Create clean documents."""
    from mlabc import pmid2doi
    if mod:
        mods = [s.strip() for s in mod.split(',')]
    else:
        mods = MODS
    if issn:
        issns = {i.strip() for i in issn.split(',')}
    else:
        issns = None
    p2i = pmid2doi()
    for m in mods:
        d = getmod(m)
        for i in d['issn']:
            if issns and issn not in issns:
                continue
            print('writing ', m, i)
            g = d['Generate'](i, pmid2doi=p2i)
            # print('overwrite', not nowrite)
            g.run(overwrite=not nowrite, prefix=m, num=num)


@cli.command()
@click.option('--d', help='directory to scan', default=Config.DATADIR)
def cleandirs(d):
    """Remove empty directories."""
    d = d or Config.DATADIR
    for f in os.listdir(d):
        d = Config.DATADIR + f
        if os.path.isdir(d):
            n = len(os.listdir(d))
            if n == 0:
                print('removing', f)
                os.removedirs(d)


@cli.command()
@click.option('--mod', help='modules to run use. Prefix with "-" to exclude')
@click.option('--issn', help='journals to run')
@click.option('--sleep', default=10., help='wait sleep seconds between requests', show_default=True)
@click.option('--mx', default=3, help='max documents to download 0=all')
def download(mod='', sleep=10., mx=1, issn=''):
    """Download html/xml from websites."""
    if mod:
        mods = [s.strip() for s in mod.split(',')]
        exclude = {m[1:] for m in mods if m[0] == '-'}
        mods = [m for m in mods if m[0] != '-']
        if not mods:
            mods = MODS
    else:
        mods = MODS
        exclude = set()
    if issn:
        issns = {i.strip() for i in issn.split(',')}
    else:
        issns = None
    for m in mods:
        if m in exclude:
            continue
        d = getmod(m)
        for issn in d['issn']:
            if issns and issn not in issns:
                continue
            print('downloading:', m, issn)
            d['download'](issn, sleep=sleep, mx=mx)


@cli.command()
def summary():
    """Summary of current download status."""
    from download import journal_summary
    journal_summary()


@cli.command()
@click.option('--out', default=Config.JCSV, help="output filename", show_default=True)
@click.option('--col', default=0, help="column that contains pubmed", show_default=True)
@click.option('--sleep', default=1., help='wait sleep seconds between requests', show_default=True)
@click.option('--noheader', is_flag=True, help='csvfile has no header')
@click.argument('csvfile')
def journals(csvfile, out, noheader=False, col=0, sleep=.2):
    """Create a CSV of (pmid, issn, name, year, doi, pmcid, title) from list of SUBA4 pubmed ids."""
    from download import getmeta
    getmeta(csvfile, sleep=sleep, pubmeds=out, header=not noheader, pcol=col)


@cli.command()
def issn():
    """Print all ISSN,journals."""
    for m in MODS:
        if m in {'epmc', 'elsevier'}:
            continue
        mod = getmod(m)
        d = mod['issn']
        for issn in d:
            print('%s,%s' % (issn, d[issn]))


if __name__ == '__main__':
    cli()
