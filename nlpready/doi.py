from __future__ import annotations

import webbrowser

import click


# pytlint: disable=redefined-outer-name
@click.command()
@click.argument("doi")
def run(doi: str) -> None:
    """Show a DOI in a browser."""
    webbrowser.open_new_tab("http://doi.org/" + doi)


if __name__ == "__main__":
    run()  # pylint: disable=no-value-for-parameter
