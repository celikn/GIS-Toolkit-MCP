# GIS Toolkit MCP

A standalone [Model Context Protocol](https://modelcontextprotocol.io) server exposing common
file-level GIS operations — buffer, clip, reproject, overlay, spatial join, zonal statistics,
nearest neighbor, dissolve, centroid, length/area fields. Built with [FastMCP](https://gofastmcp.com).

This package has no dependency on any other project. Any MCP client can use it as long as it can
reach the server over HTTP and share a filesystem with it (see "Data access" below).

## Why file-level, not geometry-level

Most GIS MCP servers expose single-geometry operations (e.g. `buffer(geometry: str, distance)`).
That's the wrong granularity for "process this whole dataset" tasks — buffering a 1,000-feature
shapefile that way means 1,000 separate tool calls. Every tool here instead takes a file path in,
a file path out, and processes the whole dataset in one call.

## Tools

| Tool | What it does |
|---|---|
| `buffer_file` | Buffer every feature by a distance in meters (auto-projects geographic CRS) |
| `clip_file` | Clip a vector or raster file to a vector mask's boundary |
| `reproject_file` | Reproject a vector or raster file to a target CRS |
| `overlay_file` | Union / intersection / difference / symmetric_difference of two vector files |
| `spatial_join_file` | Spatial join two vector files by a predicate (intersects, contains, ...) |
| `dissolve_file` | Merge features sharing the same value in a field |
| `centroid_file` | Replace geometries with their centroids, keeping attributes |
| `zonal_statistics_file` | Per-zone raster statistic (min/max/mean/sum/std/count/median) as a new field |
| `nearest_neighbor_file` | k-nearest-neighbor distance + index from one file to another |
| `add_length_area_field` | Add a length (lines) or area (polygons) field, computed in meters |
| `select_by_attribute_file` | Keep only features where a field compares true against a value (==, !=, >, <, contains); supports string-encoded dict fields like OSM `tags` via `nested_key` |
| `upload_file` | Save base64-encoded content into the server's data directory, for clients with no shared filesystem access |
| `download_file` | Read back a file's content as base64, e.g. to retrieve another tool's output |

## Running it

```bash
pip install -r requirements.txt
python3 server.py
```

Or via Docker:

```bash
docker build -t gis-toolkit-mcp .
docker run -p 9020:9020 -v /path/to/your/data:/data -e GIS_TOOLKIT_DATA_DIR=/data gis-toolkit-mcp
```

The server listens on `http://0.0.0.0:9020/mcp` by default (Streamable HTTP transport).

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `GIS_TOOLKIT_DATA_DIR` | current working directory | Base directory relative tool paths are resolved against. Absolute paths pass through unchanged. |
| `GIS_TOOLKIT_TRANSPORT` | `streamable-http` | `streamable-http`, `sse`, or `stdio` |
| `GIS_TOOLKIT_PORT` | `9020` | Port for HTTP-based transports |

## Data access

Every tool takes plain file paths (input and output) and reads/writes them directly. If your
client shares a filesystem with the server (e.g. a shared Docker volume, or both running on the
same host), just mount your data directory and point `GIS_TOOLKIT_DATA_DIR` (or pass absolute
paths) accordingly — no code changes needed.

If your client does **not** share a filesystem with the server (e.g. a remote user calling a
publicly hosted instance from their own machine), there are two ways to get data in and out:

- **MCP tools**: `upload_file` takes base64 content and returns a path to use as another tool's
  `input_path`; `download_file` reads a path back out as base64. Good for an MCP client or an
  LLM driving the tools programmatically.
- **Plain HTTP** (for a human, or a chat UI's browser — base64 in a chat message is unwieldy):
  `GET /upload` serves a small HTML form to pick and submit a file directly; `GET
  /files/<path>` streams a file back with `Content-Disposition: attachment`, so pasting that URL
  as a link gives a real, clickable download in any browser.

Both paths are restricted to `GIS_TOOLKIT_DATA_DIR` — they refuse to read/write outside it. Note
the base64 tools return one file at a time, so prefer single-file output formats (`.geojson`,
`.gpkg`) over multi-file ones (`.shp` + its sidecars) when a remote client needs to retrieve the
result.

## Connecting a client

Any MCP client that supports Streamable HTTP can connect directly to `http://<host>:9020/mcp`.
For example, in a `librechat.yaml`:

```yaml
mcpServers:
  gis-toolkit:
    type: streamable-http
    url: http://<host>:9020/mcp
```
