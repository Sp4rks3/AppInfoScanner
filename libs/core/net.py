#! /usr/bin/python3
# -*- coding: utf-8 -*-
# Author: kelvinBen
# Github: https://github.com/kelvinBen/AppInfoScanner
"""Networking helpers used to fetch HTTP information for discovered URLs."""

from __future__ import annotations

import re
import time
import threading
from typing import Dict

import requests

import libs.core as cores


class NetThreads(threading.Thread):
    """Thread worker that fetches meta information for URLs."""

    def __init__(self, threadID: int, name: str, domain_queue, worksheet) -> None:
        super().__init__()
        self.name = name
        self.threadID = threadID
        self.lock = threading.Lock()
        self.domain_queue = domain_queue
        self.worksheet = worksheet

    def __get_http_info(self) -> None:
        while True:
            if self.domain_queue.empty():
                break
            domains = self.domain_queue.get(timeout=5)
            domain = domains["domain"]
            url_ip = domains["url_ip"]
            time.sleep(2)
            result = self.__get_request_result(url_ip)
            print("[+] Processing URL address:" + url_ip)
            if result != "error":
                if self.lock.acquire(True):
                    cores.excel_row = cores.excel_row + 1
                    self.worksheet.cell(row=cores.excel_row, column=1, value=cores.excel_row - 1)
                    self.worksheet.cell(row=cores.excel_row, column=2, value=url_ip)
                    self.worksheet.cell(row=cores.excel_row, column=3, value=domain)

                    if result != "timeout":
                        self.worksheet.cell(row=cores.excel_row, column=4, value=result["status"])
                        self.worksheet.cell(row=cores.excel_row, column=5, value=result["des_ip"])
                        self.worksheet.cell(row=cores.excel_row, column=6, value=result["server"])
                        self.worksheet.cell(row=cores.excel_row, column=7, value=result["title"])
                        self.worksheet.cell(row=cores.excel_row, column=8, value=result["cdn"])

                    self.lock.release()

    def __get_request_result(self, url: str) -> Dict[str, str]:
        result: Dict[str, str] = {
            "status": "",
            "server": "",
            "cookie": "",
            "cdn": "",
            "des_ip": "",
            "sou_ip": "",
            "title": "",
        }
        cdn = ""
        try:
            with requests.get(url, timeout=5, stream=True) as rsp:
                result["status"] = rsp.status_code
                headers = rsp.headers
                if "Server" in headers:
                    result["server"] = headers["Server"]
                if "Cookie" in headers:
                    result["cookie"] = headers["Cookie"]
                if "X-Via" in headers:
                    cdn += headers["X-Via"]
                if "Via" in headers:
                    cdn += headers["Via"]
                result["cdn"] = cdn

                connection = getattr(rsp.raw, "connection", None)
                sock = getattr(connection, "sock", None)
                if sock:
                    des_ip, _ = sock.getpeername()
                    sou_ip, _ = sock.getsockname()
                    result["des_ip"] = des_ip
                    result["sou_ip"] = sou_ip

                html = rsp.text
                title = re.findall(r"<title>(.+)</title>", html)
                if title:
                    result["title"] = title[0]
                return result
        except requests.exceptions.InvalidURL:
            return "error"  # type: ignore[return-value]
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            return "timeout"  # type: ignore[return-value]

    def run(self) -> None:  # pragma: no cover - thread wrapper
        self.__get_http_info()
