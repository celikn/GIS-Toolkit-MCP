from typing import Optional

import geopandas as gpd
import rasterio
from rasterio.warp import Resampling, calculate_default_transform, reproject
from rasterstats import zonal_stats

from ._shared import is_raster, resolve_path


def reproject_file(input_path: str, target_crs: str, output_path: str) -> dict:
    """Reproject a vector or raster file to `target_crs` (e.g. 'EPSG:32617').

    Which path to use is decided by `input_path`'s file extension
    (.tif/.tiff/.img/.nc/.vrt = raster, otherwise vector).
    """
    out_path = resolve_path(output_path)

    if is_raster(input_path):
        in_path = resolve_path(input_path)
        with rasterio.open(in_path) as src:
            transform, width, height = calculate_default_transform(src.crs, target_crs, src.width, src.height, *src.bounds)
            out_meta = src.meta.copy()
            out_meta.update({"crs": target_crs, "transform": transform, "width": width, "height": height})

            with rasterio.open(out_path, "w", **out_meta) as dst:
                for band in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, band),
                        destination=rasterio.band(dst, band),
                        src_transform=src.transform, src_crs=src.crs,
                        dst_transform=transform, dst_crs=target_crs,
                        resampling=Resampling.nearest,
                    )
        return {"output_path": out_path, "width": width, "height": height, "crs": target_crs}

    gdf = gpd.read_file(resolve_path(input_path))
    result = gdf.to_crs(target_crs)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result), "crs": target_crs}


def zonal_statistics_file(raster_path: str, zones_path: str, stat: str, output_path: str, field_name: Optional[str] = None) -> dict:
    """Compute a raster statistic (min, max, mean, sum, std, count, median) for each
    zone polygon and add it as a new field on the zones, saved to `output_path`."""
    valid_stats = {"min", "max", "mean", "sum", "std", "count", "median"}
    if stat not in valid_stats:
        raise ValueError(f"stat must be one of {sorted(valid_stats)}, got {stat!r}")

    zones = gpd.read_file(resolve_path(zones_path))
    raster_file = resolve_path(raster_path)

    with rasterio.open(raster_file) as src:
        zones_for_stats = zones.to_crs(src.crs)

    stats = zonal_stats(zones_for_stats, raster_file, stats=[stat])
    name = field_name or stat
    zones[name] = [s[stat] for s in stats]

    out_path = resolve_path(output_path)
    zones.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(zones), "field_name": name}
