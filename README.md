
# Scraping Journals

Install required libraries with:

```
pip3 install -r requirements.txt
```

First we must create a CSV file containing the pubmed IDs
that we are interested in. Then we collect some metadata
such as DOI, PMCID, TITLE etc. with:

```
cd mlcode
python3 issn.py journals --out=[metafile] --sleep=20. [csvfile]
```

This will scrape the ncbi website so
the `--sleep=20.` key ensures that it is not hit too rapidly. This will
avoid you being blocked! This will take sometime (e.g. 20 x #papers) so go get a coffee.

This _metafile_ is a CSV file that will form the bases for everything that follows. It
contains the DOIs that will allow us to find the document.

Next edit the `mlcode/config.py` and alter the variables there. Specifically
we need `JCSV` to point to the newly created `metafile`.

We can then download the fulltext with:

```
python3 issn.py download --sleep=100. --mx=0
```

This will also take some time :)


## ScienceDirect

ScienceDirect Journals require the use of selenium and chromedriver.
(Since the content is delivered as a json blob that is used to generate
the final DOM using javascript)

```
pip3 install selenium
```

Download chromedriver from [here](https://sites.google.com/a/chromium.org/chromedriver/)
and place the excutable in your `PATH`.

All chromedriver downloads currently are managed by `cell.py` so we can download
them separately with:

```
python3 cell.py download --sleep=100. --mx=0 --head
```

## Viewing Downloads

You can build a set of html pages that present the Abstract/Results/Methods sections
in a simple manner. This is useful to check the code is actually finding the correct text
from within the downloaded HTML/XML.

```
python3 issn.py tohtml
```

You can then navigate to `DATADIR/html` and click on the `index.html` file to get a summary
of your data.

## Creating "Cleaned" Data files

These are pure textfiles

```
python3 issn.py clean
```

The files are generated in `DATADIR/cleaned`. Each file is named as `cleaned_<ISSN>_<JOURNAL>/<PMID>_cleaned.txt`.
ISSN is a "number" XXXX-XXXX identifying a journal (actually journals can have multiple ISSNs indicating
a dead tree version or a website etc.)
