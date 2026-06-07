#!/usr/bin/env python3
"""Small caching proxy for GitHub release assets used by local Harbor runs."""

from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_CACHE_DIR = Path.home() / ".cache" / "agon-release-proxy"
ASSET_RE = re.compile(
    r"^/tta-lab/(?P<repo>[^/]+)/releases/(?:(?:latest/download)|(?:download/(?P<tag>[^/]+)))/(?P<asset>[^/]+)$"
)


class ReleaseProxy(http.server.ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, cache_dir: Path):
        super().__init__(server_address, handler_class)
        self.cache_dir = cache_dir
        self.cache_locks: dict[Path, threading.Lock] = {}
        self.cache_locks_guard = threading.Lock()


class Handler(http.server.SimpleHTTPRequestHandler):
    server: ReleaseProxy

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok\n")
            return

        match = ASSET_RE.match(self.path.split("?", 1)[0])
        if not match:
            self.send_error(404, "unsupported release proxy path")
            return

        repo = match.group("repo")
        tag = match.group("tag")
        asset = match.group("asset")

        try:
            if tag is None:
                tag = self._resolve_latest_tag(repo)
            cache_path = self.server.cache_dir / repo / tag / asset
            with self._cache_lock(cache_path):
                self._ensure_cached(repo, tag, asset, cache_path)
            self._send_file(cache_path)
        except urllib.error.HTTPError as exc:
            self.send_error(exc.code, f"upstream returned HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001
            self.send_error(502, str(exc))

    def _cache_lock(self, cache_path: Path) -> threading.Lock:
        with self.server.cache_locks_guard:
            return self.server.cache_locks.setdefault(cache_path, threading.Lock())

    def _resolve_latest_tag(self, repo: str) -> str:
        url = f"https://api.github.com/repos/tta-lab/{repo}/releases/latest"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "agon-release-proxy",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)

        tag = payload.get("tag_name")
        if not tag:
            raise RuntimeError(f"latest release for {repo} has no tag_name")
        return tag

    def _ensure_cached(self, repo: str, tag: str, asset: str, cache_path: Path) -> None:
        if cache_path.exists() and cache_path.stat().st_size > 0:
            return

        url = f"https://github.com/tta-lab/{repo}/releases/download/{tag}/{asset}"

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=cache_path.parent, prefix=f".{asset}.", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
            with urllib.request.urlopen(url, timeout=300) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)

        os.replace(tmp_path, cache_path)

    def _send_file(self, path: Path) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()

        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args()

    server = ReleaseProxy((args.host, args.port), Handler, args.cache_dir)
    print(
        f"serving release cache on http://{args.host}:{args.port} "
        f"from {args.cache_dir}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
