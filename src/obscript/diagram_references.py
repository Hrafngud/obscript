"""Freeze selected public diagram images with provenance; unavailable sources stay optional."""

from __future__ import annotations

import hashlib
import ipaddress
import socket
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .storage import file_sha256


MAX_IMAGE_BYTES = 8 * 1024 * 1024


def public_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("diagram URL must be public HTTP(S) without credentials")
    addresses = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("diagram URL must resolve to public addresses")


class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def image_extension(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("source is not a supported raster image (PNG, JPEG, GIF, WebP)")


def freeze_diagram(reference: dict, directory: Path) -> dict:
    """Download once per URL. Never turn uncertain reuse permission into permission."""
    result = {**reference, "local_path": "", "sha256": "", "error": ""}
    url = reference["figure_url"]
    if not url:
        return result
    try:
        public_url(reference["source_url"])
        public_url(url)
        key = hashlib.sha256(url.encode()).hexdigest()
        for suffix in (".png", ".jpg", ".gif", ".webp"):
            cached = directory / f"{key}{suffix}"
            if cached.is_file() and image_extension(cached.read_bytes()) == suffix:
                return {**result, "local_path": str(cached.resolve()), "sha256": file_sha256(cached)}
        request = Request(url, headers={"User-Agent": "obscript/0.1 (diagram reference)"})
        with build_opener(PublicRedirects()).open(request, timeout=15) as response:
            public_url(response.geturl())
            data = response.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("diagram exceeds 8 MiB")
        suffix = image_extension(data)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{key}{suffix}"
        destination.write_bytes(data)
        result.update(local_path=str(destination.resolve()), sha256=hashlib.sha256(data).hexdigest())
    except (OSError, ValueError, HTTPException) as exc:
        result["error"] = str(exc)
    return result
