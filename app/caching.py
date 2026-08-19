"""Cache headers and conditional-request handling for the static data endpoints.

Two problems are solved here.

**No freshness information.** FastAPI's FileResponse sends ETag and
Last-Modified but no Cache-Control. With no explicit freshness a browser falls
back to the heuristic in RFC 9111 4.2.2 and treats the response as fresh for
roughly 10% of its age. These files sit unchanged for months, so a client could
serve a stale copy for over a week without ever revalidating -- which is how a
newly deployed field went missing on phones that had visited before while cold
desktops looked fine.

**No conditional handling.** A bare FileResponse only *emits* an ETag; the
comparison against If-None-Match lives in Starlette's StaticFiles, not in the
response class. Adding must-revalidate without this would turn every page load
into a full re-download of the 4.4 MB county TopoJSON, so the helper below does
the comparison itself and answers 304 with no body.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, Response

DATA_CACHE_HEADERS = {"Cache-Control": "public, max-age=0, must-revalidate"}


def _normalize(etag: str) -> str:
    """Strip the weak-comparison prefix and surrounding whitespace.

    Cloudflare rewrites our strong ETag to a weak one when it compresses the
    body, so the value a browser sends back is `W/"abc"` while the origin still
    computes `"abc"`. Comparing them raw would never match and every request
    would return a full body.
    """
    etag = etag.strip()
    return etag[2:] if etag.startswith("W/") else etag


def _matches(request: Request, etag: str | None) -> bool:
    if not etag:
        return False
    header = request.headers.get("if-none-match")
    if not header:
        return False
    if header.strip() == "*":
        return True
    wanted = _normalize(etag)
    return any(_normalize(candidate) == wanted for candidate in header.split(","))


def _not_modified(etag: str | None) -> Response:
    headers = dict(DATA_CACHE_HEADERS)
    if etag:
        headers["ETag"] = etag
    return Response(status_code=304, headers=headers)


def file_response(
    request: Request, filepath: Path, media_type: str = "application/json"
) -> Response:
    """Serve a file, answering 304 when the client's copy is current.

    Passing stat_result matters: without it FileResponse defers the stat until
    it is sent, so the ETag header does not exist yet at construction time and
    the comparison below would silently never match.
    """
    response = FileResponse(
        filepath,
        media_type=media_type,
        headers=DATA_CACHE_HEADERS,
        stat_result=filepath.stat(),
    )
    etag = response.headers.get("etag")
    if _matches(request, etag):
        return _not_modified(etag)
    return response


def json_response(request: Request, content: object, etag: str) -> Response:
    """Serve an in-memory payload, answering 304 when the client's copy is current."""
    if _matches(request, etag):
        return _not_modified(etag)
    return JSONResponse(
        content=content, headers={**DATA_CACHE_HEADERS, "ETag": etag}
    )


def etag_for(payload: bytes) -> str:
    return f'"{hashlib.md5(payload).hexdigest()}"'
