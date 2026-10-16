#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时收数服务器：接收浏览器页面 POST 过来的大数据，落盘到指定目录。"""
import http.server
import os
import socketserver
import sys

OUT = os.path.expanduser("~/.hermes/cache/scratch/exfil")
os.makedirs(OUT, exist_ok=True)
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899


class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        name = self.path.strip("/").replace("/", "_") or "dump"
        p = os.path.join(OUT, name)
        with open(p, "wb") as f:
            f.write(body)
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok:%d" % len(body))
        print("saved %s (%d bytes)" % (p, len(body)), flush=True)

    def do_GET(self):
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b"alive")

    def log_message(self, *a):
        pass


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


print("listening on 127.0.0.1:%d -> %s" % (PORT, OUT), flush=True)
S(("127.0.0.1", PORT), H).serve_forever()
