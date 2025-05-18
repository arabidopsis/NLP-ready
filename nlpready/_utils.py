from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass

from . import _config as Config


@dataclass(kw_only=True)
class UserConfig:
    suba_csv: str
    data_dir: str
    cache: str
    name: str
    email: str | None = None
    api_key: str | None = None


_CONF = None


def getconfig() -> UserConfig:

    global _CONF
    if _CONF is not None:
        return _CONF
    default = dict(
        suba_csv=Config.JCSV,
        data_dir=Config.DATADIR,
        cache=Config.PKLFILE,
        name=Config.NAME,
    )
    if not os.path.exists("config.toml"):
        _CONF = UserConfig(**default)
    else:
        with open("config.toml", "rb") as fp:
            _CONF = UserConfig(**{**default, **tomllib.load(fp)})
    return _CONF


def data_dir() -> str:
    return getconfig().data_dir
