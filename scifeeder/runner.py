from __future__ import annotations

import csv
import time
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING

from .cache import Cache
from .issn import ISSN_MAP
from .selenium_cls import Selenium
from .selenium_cls import StealthSelenium
from .types import Paper
from .utils import read_papers_csv

if TYPE_CHECKING:
    from tqdm import tqdm


class Runner:
    def __init__(
        self,
        papers_csv: str | Path,
        done_csv: str | Path | None = None,
        batch_size: int = 1,
        sleep=0.0,
    ):
        self.papers_csv = Path(papers_csv)
        if done_csv is None:
            done_csv = self.papers_csv.parent / (self.papers_csv.name + ".done")
        self.done_csv = Path(done_csv)
        self.batch_size = batch_size
        self.sleep = sleep

    def start(self) -> None:
        pass

    def end(self) -> None:
        pass

    def get_done(self) -> set[str]:
        if self.done_csv.exists():
            with self.done_csv.open("r", encoding="utf8") as fp:
                R = csv.reader(fp)
                done = {row[0] for row in R}
        else:
            done = set()
        return done

    def run(self, notebook: bool = False):
        from .issn import ISSN_MAP

        if notebook:
            from tqdm.notebook import tqdm
        else:
            from tqdm import tqdm

        done = self.get_done()

        todo = [
            paper
            for paper in read_papers_csv(self.papers_csv)
            if paper.pmid not in done
            and paper.doi
            and paper.issn
            and paper.issn in ISSN_MAP
        ]
        self.start()
        try:
            with self.done_csv.open("a", encoding="utf8") as fp:
                W = csv.writer(fp)
                with tqdm(total=len(todo)) as pbar:
                    for papers in batched(todo, self.batch_size):
                        for paper in papers:
                            status = self.work(paper, pbar)
                            W.writerow([paper.pmid, status])
                            fp.flush()
                        pbar.update(len(papers))
                        if self.sleep:
                            time.sleep(self.sleep)
        finally:
            self.end()

    def work(self, paper: Paper, tqdm: tqdm) -> str:
        return "done"


class SeleniumRunner(Runner):
    cache: Cache
    web: Selenium

    def start(self):

        self.cache = Cache("scache")
        self.web = self.create_driver()

    def create_driver(self):
        return StealthSelenium(headless=True)

    def work(self, paper, tqdm):
        tqdm.write(f"working... {paper.pmid}")
        if not paper.doi:
            return "nodoi"
        if paper.issn not in ISSN_MAP:
            return "noissn"

        try:
            html = self.web.fetch_html(paper.doi, ISSN_MAP[paper.issn])
            if html is None:
                self.web = self.create_driver()
                tqdm.write("retry....")
                html = self.web.fetch_html(paper.doi, ISSN_MAP[paper.issn])
            if html is None:
                retval = "cc"
            elif not html:
                retval = "timeout"
            else:
                self.cache.save_html(paper, html)
                retval = "ok"
        except Exception as e:
            tqdm.write(f"failed: {paper.pmid} {e}")
            retval = "failed"
        tqdm.write(retval)
        return retval

    def end(self):
        self.web.close()
