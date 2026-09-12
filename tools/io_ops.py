"""Upload/download bridge for clients that don't share a filesystem with this
server. Every other tool in this package takes file paths on the server's own
disk — fine when the client is deployed alongside it (e.g. a shared Docker
volume), but unusable for a remote client with its own local data. These two
tools let such a client push a file in, get back a path to feed into any other
tool, then pull a result back out.
"""
import base64
import os
from pathlib import Path


def _data_root() -> Path:
    return Path(os.environ.get("GIS_TOOLKIT_DATA_DIR", ".")).resolve()


def _safe_path(path: str) -> Path:
    """Resolve `path` under the data directory and refuse anything that escapes
    it. Unlike the geometry tools (where an unexpected path just fails to parse
    as a GIS file), upload/download move raw bytes directly, so an unrestricted
    path here would be a plain arbitrary file read/write.
    """
    base = _data_root()
    p = Path(path)
    resolved = (base / p).resolve() if not p.is_absolute() else p.resolve()
    if resolved != base and base not in resolved.parents:
        raise ValueError(f"path must stay within the data directory ({base}), got {resolved}")
    return resolved


def upload_file(filename: str, content_base64: str, subdir: str = "uploads") -> dict:
    """Save base64-encoded file content into the server's data directory and
    return the path to use as another tool's input_path (e.g. buffer_file).

    `filename` is reduced to its basename (no directory components) so it can't
    write outside `subdir`. Prefer single-file formats (.geojson, .gpkg) over
    multi-file ones (.shp + sidecars) since download_file below only returns one
    file at a time.
    """
    safe_name = Path(filename).name
    if not safe_name:
        raise ValueError("filename must not be empty")

    target_dir = _safe_path(subdir)
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / safe_name

    data = base64.b64decode(content_base64)
    out_path.write_bytes(data)
    return {"output_path": str(out_path), "size_bytes": len(data)}


def download_file(path: str) -> dict:
    """Read a file from the server's data directory and return it base64-encoded
    — e.g. to retrieve the output_path another tool produced."""
    safe = _safe_path(path)
    if not safe.is_file():
        raise FileNotFoundError(f"no such file: {safe}")

    data = safe.read_bytes()
    return {
        "filename": safe.name,
        "content_base64": base64.b64encode(data).decode("ascii"),
        "size_bytes": len(data),
    }
