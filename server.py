"""GIS Toolkit MCP server — a general-purpose, standalone MCP server for common
file-level GIS operations (buffer, clip, reproject, overlay, spatial join, zonal
statistics, nearest neighbor, dissolve, centroid, length/area fields, select by
attribute).

Every tool takes explicit input/output file paths and works over a shared
filesystem — mount the same data directory into whatever client (GeoAgent,
LibreChat, another agent, ...) talks to this server. Not tied to any other
project's conventions.

Env vars:
    GIS_TOOLKIT_DATA_DIR  base directory relative paths are resolved against
                          (default: current working directory)
    GIS_TOOLKIT_TRANSPORT "streamable-http" (default), "sse", or "stdio"
    GIS_TOOLKIT_PORT      port for http-based transports (default: 9020)
"""
import os
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse

from tools import io_ops, nearest, raster_ops, vector_ops

mcp = FastMCP("GISToolkit")

for fn in (
    vector_ops.buffer_file,
    vector_ops.clip_file,
    vector_ops.overlay_file,
    vector_ops.dissolve_file,
    vector_ops.centroid_file,
    vector_ops.spatial_join_file,
    vector_ops.add_length_area_field,
    vector_ops.select_by_attribute_file,
    raster_ops.reproject_file,
    raster_ops.zonal_statistics_file,
    nearest.nearest_neighbor_file,
    io_ops.upload_file,
    io_ops.download_file,
):
    mcp.add_tool(fn)


# Plain HTTP routes alongside the MCP tools, for humans (or a chat UI's browser)
# rather than an MCP client: /upload lets someone drop a file in without base64
# in a chat message, /files/<path> gives a real clickable download link instead
# of raw base64 in a tool response.

_UPLOAD_FORM_HTML = """<!doctype html>
<title>GIS Toolkit MCP — Upload</title>
<h2>Upload a file</h2>
<form method="post" action="/upload" enctype="multipart/form-data">
  <input type="file" name="file" required>
  <button type="submit">Upload</button>
</form>
"""


@mcp.custom_route("/upload", methods=["GET"])
async def upload_form(request: Request) -> HTMLResponse:
    return HTMLResponse(_UPLOAD_FORM_HTML)


@mcp.custom_route("/upload", methods=["POST"])
async def upload_handler(request: Request) -> JSONResponse:
    form = await request.form()
    upload = form.get("file")
    if upload is None:
        return JSONResponse({"error": "missing 'file' field"}, status_code=400)

    safe_name = Path(upload.filename).name
    if not safe_name:
        return JSONResponse({"error": "empty filename"}, status_code=400)

    target_dir = io_ops._safe_path("uploads")
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / safe_name

    content = await upload.read()
    out_path.write_bytes(content)
    return JSONResponse({"output_path": str(out_path), "size_bytes": len(content)})


@mcp.custom_route("/files/{path:path}", methods=["GET"])
async def download_route(request: Request):
    try:
        target = io_ops._safe_path(request.path_params["path"])
    except ValueError:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if not target.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(target, filename=target.name)


if __name__ == "__main__":
    transport = os.environ.get("GIS_TOOLKIT_TRANSPORT", "streamable-http")
    port = int(os.environ.get("GIS_TOOLKIT_PORT", "9020"))
    mcp.run(transport=transport, host="0.0.0.0", port=port)
