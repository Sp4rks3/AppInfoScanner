#! /usr/bin/python3
# -*- coding: utf-8 -*-
# Author: kelvinBen
# Github: https://github.com/kelvinBen/AppInfoScanner
"""Threaded helper used to download remote resources.

The original implementation mixed resource management and lacked a number of
robustness checks which could lead to crashes (for example when the
``Content-Length`` header was missing) and left HTTP sessions open.  The class
below keeps the behaviour but improves reliability and readability.
"""

from __future__ import annotations

import sys
import threading
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages import urllib3

import config
import libs.core as cores


class DownloadThreads(threading.Thread):

    def __init__(self, input_path: str, file_name: str, cache_path: str, types: str) -> None:
        super().__init__()
        self.url = input_path
        self.types = types
        self.cache_path = cache_path
        self.file_name = file_name

    def __request(self) -> None:
        """Perform the HTTP request and save the result to ``cache_path``.

        The method handles both binary (APK/IPA) and text based downloads and
        reports progress for large binary files.  Any network related exception
        is propagated to the caller so that the thread can surface the error.
        """

        urllib3.disable_warnings()

        try:
            with requests.Session() as session:
                adapter = HTTPAdapter(max_retries=3)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                session.keep_alive = False

                if config.method.upper() == "POST":
                    resp = session.post(
                        url=self.url, params=config.data, headers=config.headers, timeout=30
                    )
                else:
                    resp = session.get(
                        url=self.url, data=config.data, headers=config.headers, timeout=30
                    )

                resp.raise_for_status()

                if self.types in {"Android", "iOS"}:
                    length: Optional[float] = None
                    if resp.headers.get("content-length"):
                        try:
                            length = float(resp.headers["content-length"])
                        except ValueError:
                            length = None

                    count = 0
                    progress_tmp = 0
                    with open(self.cache_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if not chunk:
                                continue
                            f.write(chunk)
                            if length:
                                count += len(chunk)
                                progress = int(count / length * 100)
                                if progress != progress_tmp:
                                    progress_tmp = progress
                                    print("\r", end="")
                                    print(
                                        "[*] Download progress: {}%: ".format(progress),
                                        "▋" * (progress // 2),
                                        end="",
                                    )
                                    sys.stdout.flush()
                else:
                    html = resp.text
                    with open(self.cache_path, "w", encoding="utf-8", errors="ignore") as f:
                        f.write(html)

                cores.download_flag = True
        except Exception as e:
            # Re-raise as a generic exception so the caller can decide how to
            # handle it.  The original traceback is preserved.
            raise e

    def run(self) -> None:  # pragma: no cover - simple thread wrapper
        self.__request()
