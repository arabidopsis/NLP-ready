from __future__ import annotations

import warnings

import click

from .utils import getconfig


@click.group()
def cli():
    pass


# @cli.command()
# @click.argument("data_dir", required=False)
# def clean_cache(data_dir: str | None) -> None:
#     """Remove empty directories."""
#     if data_dir is None:
#         data_dir = getconfig().data_dir
#     if not os.path.exists(data_dir):
#         return
#     for f in os.listdir(data_dir):
#         d = os.path.join(data_dir, f)
#         if os.path.isdir(d):
#             n = len(os.listdir(d))
#             if n == 0:
#                 click.secho(f"removing: {f}", fg="yellow")
#                 os.removedirs(d)


@cli.command()
@click.option("--email", help="your email address for NCBI E-Utilities")
@click.option("--api-key", help="your NCBI API_KEY")
@click.option(
    "--out",
    help=f'output CSV filename (will be appended to if exists). Defaults to "{getconfig().papers_csv}"',
    type=click.Path(dir_okay=False, file_okay=True),
)
@click.option(
    "--col",
    default=0,
    help="column in file that contains the pubmed ID",
    show_default=True,
)
@click.option(
    "-b",
    "--batch-size",
    default=10,
    help="batch size to hit NCBI",
    show_default=True,
)
@click.option(
    "--sleep",
    default=3.0,
    help="wait sleep seconds between requests",
    show_default=True,
)
@click.option("--noheader", is_flag=True, help="csvfile has no header")
@click.argument(
    "pubmed_csv",
    type=click.Path(dir_okay=False, exists=True, file_okay=True),
)
def make_papers(
    pubmed_csv: str,
    out: str | None,
    email: str | None,
    api_key: str | None,
    noheader: bool = False,
    col: int = 0,
    sleep: float = 0.37,
    batch_size: int = 10,
) -> None:
    """Create a CSV of (pmid, issn, name, year, doi, pmcid, title) from list of pubmed IDs."""
    # pylint: disable=import-outside-toplevel
    from .ncbi import get_ncbi_metadata

    conf = getconfig()
    if out is None:
        out = conf.papers_csv

    if not email:
        if conf.email:
            email = conf.email
        else:
            warnings.warn(
                """
Email address is not specified.

To make use of NCBI's E-utilities, NCBI requires you to specify your
email address with each request.

In case of excessive usage of the E-utilities, NCBI will attempt to contact
a user at the email address provided before blocking access to the
E-utilities.""",
                UserWarning,
            )
    api_key = api_key or conf.api_key
    if not api_key and sleep < 0.37:
        warnings.warn(
            """
More than 3 hits per second without an --api-key may get you
blocked from the NCBI site.""",
            UserWarning,
        )
    get_ncbi_metadata(
        pubmeds_todo=pubmed_csv,
        papers_csv=out,
        sleep=sleep,
        header=not noheader,
        pcol=col,
        email=email,
        api_key=api_key,
        batch_size=batch_size,
    )


@cli.command()
@click.argument(
    "papers_csv",
    type=click.Path(dir_okay=False, exists=True, file_okay=True),
)
def runner(papers_csv: str) -> None:
    """Grab HTML pages from Journals"""
    import logging
    from .selenium_cls import SeleniumRunner

    logger = logging.getLogger("scifeeder")
    logger.setLevel(logging.WARNING)

    r = SeleniumRunner(papers_csv)
    r.run()


if __name__ == "__main__":
    cli()
