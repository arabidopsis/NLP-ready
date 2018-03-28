import click
from mlabc import Generate, Clean


MODS = [
    #"ascb",
    #"aspb",
    #"cell",
    #"dev",
    #"elsevier",
    #"emboj",
    #"epmc",
    #"gad",
    #"jbc",
    #"oup",
    #"plos",
    #"pnas",
    #"science",
    #"springer",
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


def tohtml():
    for m in MODS:
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
