"""Shared helpers used by every tool: path resolution and CRS projection.

This package has no dependency on any other project — it only knows about its own
GIS_TOOLKIT_DATA_DIR env var and plain file paths passed as tool arguments.
"""
import os
from pathlib import Path

import geopandas as gpd
from pyproj import CRS


def resolve_path(path: str) -> str:
    """Resolve a path: absolute paths pass through unchanged, relative paths are
    resolved against GIS_TOOLKIT_DATA_DIR (default: current working directory)."""
    p = Path(path)
    if p.is_absolute():
        return str(p)
    base = Path(os.environ.get("GIS_TOOLKIT_DATA_DIR", "."))
    return str(base / p)


def ensure_projected(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, CRS]:
    """Project a geographic (degree-based) GeoDataFrame to a suitable metric UTM CRS
    for accurate distance/area operations; a GeoDataFrame already in a projected CRS
    is returned unchanged. Returns (projected_gdf, original_crs) so the caller can
    reproject the result back afterwards.
    """
    original_crs = gdf.crs
    if original_crs is not None and original_crs.is_geographic:
        utm_crs = gdf.estimate_utm_crs()
        return gdf.to_crs(utm_crs), original_crs
    return gdf, original_crs


def is_raster(path: str) -> bool:
    return path.lower().split(".")[-1] in ("tif", "tiff", "img", "nc", "vrt")
