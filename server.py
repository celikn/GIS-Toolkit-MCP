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

from fastmcp import FastMCP

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

if __name__ == "__main__":
    transport = os.environ.get("GIS_TOOLKIT_TRANSPORT", "streamable-http")
    port = int(os.environ.get("GIS_TOOLKIT_PORT", "9020"))
    mcp.run(transport=transport, host="0.0.0.0", port=port)
