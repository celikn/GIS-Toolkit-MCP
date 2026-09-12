import numpy as np
from scipy.spatial import cKDTree

from ._shared import ensure_projected, resolve_path
import geopandas as gpd


def nearest_neighbor_file(input_path: str, target_path: str, output_path: str, k: int = 1) -> dict:
    """For each feature in `input_path`, find its k nearest features in `target_path`
    (by centroid distance in a metric CRS) and add distance + target-index fields.

    Adds near_1_dist, near_1_idx, near_2_dist, near_2_idx, ... (near_i_idx is the row
    position in the target file, useful for joining back to its attributes).
    """
    left = gpd.read_file(resolve_path(input_path))
    right = gpd.read_file(resolve_path(target_path))

    left_projected, original_crs = ensure_projected(left)
    right_projected = right.to_crs(left_projected.crs)

    left_coords = np.array([(geom.centroid.x, geom.centroid.y) for geom in left_projected.geometry])
    right_coords = np.array([(geom.centroid.x, geom.centroid.y) for geom in right_projected.geometry])

    k_eff = min(k, len(right_coords))
    tree = cKDTree(right_coords)
    distances, indices = tree.query(left_coords, k=k_eff)
    if k_eff == 1:
        distances = distances.reshape(-1, 1)
        indices = indices.reshape(-1, 1)

    result = left.copy()
    for i in range(k_eff):
        result[f"near_{i + 1}_dist"] = distances[:, i]
        result[f"near_{i + 1}_idx"] = indices[:, i]

    out_path = resolve_path(output_path)
    result.to_file(out_path)
    return {"output_path": out_path, "feature_count": len(result), "k": k_eff}
