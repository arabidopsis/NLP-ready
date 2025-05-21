from __future__ import annotations

import csv
import time
from abc import ABC
from abc import abstractmethod
from itertools import batched
from pathlib import Path
from typing import Iterator
from typing import TYPE_CHECKING

from .utils import read_papers_csv

if TYPE_CHECKING:
    from tqdm import tqdm
    from .types import Paper


class Runner(ABC):
    def __init__(
        self,
        papers_csv: str | Path,
        done_csv: str | Path | None = None,
        batch_size: int = 1,
        sleep=0.0,
        cache_dir: str | Path | None = None,
    ):
        self.papers_csv = Path(papers_csv)
        if done_csv is None:
            done_csv = self.papers_csv.parent / (self.papers_csv.name + ".done")
        self.done_csv = Path(done_csv)
        self.batch_size = batch_size
        self.sleep = sleep
        self.cache_dir = cache_dir

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
                        for paper, status in self.batch_worker(papers, tqdm):
                            W.writerow([paper.pmid, status])
                            fp.flush()
                        pbar.update(len(papers))
                        if self.sleep:
                            time.sleep(self.sleep)
        finally:
            self.end()

    def batch_worker(
        self,
        batch: tuple[Paper, ...],
        tqdm: tqdm,
    ) -> Iterator[tuple[Paper, str]]:
        for paper in batch:
            yield paper, self.work(paper, tqdm)

    @abstractmethod
    def work(self, paper: Paper, tqdm: tqdm) -> str:
        raise NotImplementedError
