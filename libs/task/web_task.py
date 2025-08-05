#! /usr/bin/python3
# -*- coding: utf-8 -*-
# Author: kelvinBen
# Github: https://github.com/kelvinBen/AppInfoScanner
"""Tasks related to scanning web application files.

The original implementation computed file hashes incorrectly and contained a
number of unused class attributes.  This module focuses solely on identifying
files of interest and calculating a stable identifier for each file.
"""

import os
import hashlib
from queue import Queue
from typing import Iterable, List

import config


class WebTask(object):
    """Collect files from a web project that match configured suffixes."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.file_queue: Queue[str] = Queue()
        self.file_identifier: List[str] = []
        self.permissions: List[str] = []

    def start(self) -> dict:
        """Populate ``file_queue`` with files to scan.

        Returns a dictionary with the information expected by the calling task.
        """

        scanner_file_suffix = config.web_file_suffix or ["html", "js", "xml"]

        if os.path.isdir(self.path):
            self.__get_scanner_file__(self.path, scanner_file_suffix)
        else:
            suffix = self.path.rsplit(".", 1)[-1]
            if suffix not in scanner_file_suffix:
                err_info = (
                    "Retrieval of this file type is not supported. Select a file or directory with a suffix of %s"
                    % ",".join(scanner_file_suffix)
                )
                raise Exception(err_info)
            self.__add_file(self.path)

        return {
            "comp_list": [],
            "shell_flag": False,
            "file_queue": self.file_queue,
            "packagename": None,
            "file_identifier": self.file_identifier,
            "permissions": self.permissions,
        }

    def __get_scanner_file__(self, scanner_dir: str, file_suffix: Iterable[str]) -> None:
        for dir_file in os.listdir(scanner_dir):
            dir_file_path = os.path.join(scanner_dir, dir_file)
            if os.path.isdir(dir_file_path):
                self.__get_scanner_file__(dir_file_path, file_suffix)
            else:
                if "." in dir_file:
                    suffix = dir_file.rsplit(".", 1)[-1]
                    if suffix in file_suffix:
                        self.__add_file(dir_file_path)

    def __add_file(self, path: str) -> None:
        """Add ``path`` to ``file_queue`` and record its MD5 identifier."""

        md5_obj = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_obj.update(chunk)
        self.file_identifier.append(md5_obj.hexdigest().upper())
        self.file_queue.put(path)
