import ast
from typing import Optional, Union

import geopandas as gpd

from ._shared import ensure_projected, is_raster, resolve_path

_OPERATORS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "contains": lambda a, b: isinstance(a, str) and b in a,
}


def _extract_value(cell, nested_key: Optional[str]):
    """If nested_key is given and cell is (or looks like) a stringified dict — common
    in OSM-derived data, e.g. a 'tags' column holding "{'highway': 'residential', ...}"
    — parse it and return that key's value instead of the raw cell."""
    if nested_key is None:
        return cell
    if isinstance(cell, dict):
        return cell.get(nested_key)
    if isinstance(cell, str):
        try:
            parsed = ast.literal_eval(cell)
        except (ValueError, SyntaxError):
            return None
        if isinstance(parsed, dict):
            return parsed.get(nested_key)
    return None


def buffer_file(input_path: str, distance: float, output_path: str, target_crs: Optional[str] = None) -> dict:
    """Buffer every feature in a vector file by `distance` (meters) and save the result.

    Automatically projects to a metric CRS first if the input is in a geographic
    (degree-based) CRS, so `distance` is always meters regardless of the input CRS,
    then reprojects the result back to the input's original CRS (or `target_crs`
    if given).
    """
    gdf = gpd.read_file(resolve_path(input_path))
    projected, original_crs = ensure_projected(gdf)
    projected["geometry"] = projected.buffer(distance)

    result_crs = target_crs or original_crs
    result = projected.to_crs(result_crs) if result_crs is not None else projected
    out_path = resolve_path(output_path)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result), "crs": str(result.crs)}


def clip_file(input_path: str, mask_path: str, output_path: str) -> dict:
    """Clip a vector or raster file to the boundary of a vector mask file.

    Vector inputs are clipped with geopandas.clip; raster inputs are clipped with
    rasterio.mask using the mask file's geometries. Which path to use for `input_path`
    is decided by its file extension (.tif/.tiff/.img/.nc/.vrt = raster).
    """
    mask_gdf = gpd.read_file(resolve_path(mask_path))

    if is_raster(input_path):
        import rasterio
        import rasterio.mask

        in_path = resolve_path(input_path)
        with rasterio.open(in_path) as src:
            mask_geoms = mask_gdf.to_crs(src.crs).geometry
            out_image, out_transform = rasterio.mask.mask(src, mask_geoms, crop=True)
            out_meta = src.meta.copy()
            out_meta.update({"height": out_image.shape[1], "width": out_image.shape[2], "transform": out_transform})

        out_path = resolve_path(output_path)
        with rasterio.open(out_path, "w", **out_meta) as dst:
            dst.write(out_image)
        return {"output_path": out_path, "width": out_meta["width"], "height": out_meta["height"]}

    gdf = gpd.read_file(resolve_path(input_path))
    clipped = gpd.clip(gdf, mask_gdf.to_crs(gdf.crs))
    out_path = resolve_path(output_path)
    clipped.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(clipped)}


def overlay_file(input_a: str, input_b: str, operation: str, output_path: str) -> dict:
    """Overlay two vector files: operation is one of union, intersection, difference,
    symmetric_difference (geopandas.overlay semantics)."""
    valid_ops = {"union", "intersection", "difference", "symmetric_difference"}
    if operation not in valid_ops:
        raise ValueError(f"operation must be one of {sorted(valid_ops)}, got {operation!r}")

    gdf_a = gpd.read_file(resolve_path(input_a))
    gdf_b = gpd.read_file(resolve_path(input_b)).to_crs(gdf_a.crs)
    result = gpd.overlay(gdf_a, gdf_b, how=operation)

    out_path = resolve_path(output_path)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result)}


def dissolve_file(input_path: str, by_field: str, output_path: str) -> dict:
    """Dissolve (merge) features that share the same value in `by_field`."""
    gdf = gpd.read_file(resolve_path(input_path))
    dissolved = gdf.dissolve(by=by_field, as_index=False)
    out_path = resolve_path(output_path)
    dissolved.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(dissolved)}


def centroid_file(input_path: str, output_path: str) -> dict:
    """Replace each feature's geometry with its centroid, keeping all original attributes."""
    gdf = gpd.read_file(resolve_path(input_path))
    projected, original_crs = ensure_projected(gdf)
    projected["geometry"] = projected.centroid
    result = projected.to_crs(original_crs) if original_crs is not None else projected
    out_path = resolve_path(output_path)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result)}


def spatial_join_file(left_path: str, right_path: str, predicate: str, output_path: str, how: str = "inner") -> dict:
    """Spatial join two vector files (geopandas.sjoin semantics).

    predicate: one of intersects, contains, within, crosses, touches, overlaps.
    how: inner, left, or right.
    """
    left = gpd.read_file(resolve_path(left_path))
    right = gpd.read_file(resolve_path(right_path)).to_crs(left.crs)
    result = gpd.sjoin(left, right, how=how, predicate=predicate)
    out_path = resolve_path(output_path)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result)}


def add_length_area_field(input_path: str, output_path: str, field_name: Optional[str] = None) -> dict:
    """Add a length (for line geometries) or area (for polygon geometries) field,
    computed in a metric CRS, in meters (length) or square meters (area)."""
    gdf = gpd.read_file(resolve_path(input_path))
    projected, original_crs = ensure_projected(gdf)

    geom_type = projected.geometry.geom_type.iloc[0]
    is_line = geom_type in ("LineString", "MultiLineString")
    name = field_name or ("length" if is_line else "area")
    projected[name] = projected.length if is_line else projected.area

    result = projected.to_crs(original_crs) if original_crs is not None else projected
    out_path = resolve_path(output_path)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result), "field_name": name}


def select_by_attribute_file(
    input_path: str,
    field: str,
    operator: str,
    value: Union[str, float, int],
    output_path: str,
    nested_key: Optional[str] = None,
) -> dict:
    """Keep only the features where `field` compares true against `value` using
    `operator` (one of ==, !=, >, >=, <, <=, contains).

    Set `nested_key` when `field` holds string-encoded dicts rather than a plain
    value — common in OSM-derived data, e.g. field='tags' containing
    "{'highway': 'residential', 'name': 'Lincoln Street'}" — to compare that key's
    value instead (e.g. nested_key='highway', value='residential').
    """
    if operator not in _OPERATORS:
        raise ValueError(f"operator must be one of {sorted(_OPERATORS)}, got {operator!r}")

    gdf = gpd.read_file(resolve_path(input_path))
    compare_fn = _OPERATORS[operator]
    extracted = gdf[field].apply(lambda cell: _extract_value(cell, nested_key))
    mask = extracted.apply(lambda v: compare_fn(v, value) if v is not None else False)
    result = gdf[mask]

    out_path = resolve_path(output_path)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result)}
