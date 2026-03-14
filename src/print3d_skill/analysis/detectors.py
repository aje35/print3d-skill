"""Individual mesh defect detector functions.

Each detector inspects a trimesh.Trimesh object for a specific defect type
and returns a MeshDefect if detected, or None if clean.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import trimesh

from print3d_skill.models.analysis import DefectType, MeshDefect


def detect_non_manifold_edges(mesh: trimesh.Trimesh) -> MeshDefect | None:
    """Detect edges shared by more than 2 faces (non-manifold)."""
    # Build edge-to-face mapping from face adjacency
    edges = mesh.edges_sorted
    edge_face_count: Counter[tuple[int, int]] = Counter()
    for edge in edges:
        edge_face_count[tuple(edge)] += 1

    non_manifold = [e for e, c in edge_face_count.items() if c > 2]
    if not non_manifold:
        return None

    # Collect unique vertex indices involved in non-manifold edges
    affected = sorted({v for edge in non_manifold for v in edge})
    return MeshDefect(
        defect_type=DefectType.non_manifold_edges,
        severity=DefectType.non_manifold_edges.severity,
        count=len(non_manifold),
        affected_indices=affected,
        description=f"{len(non_manifold)} non-manifold edges (shared by >2 faces)",
    )


def detect_non_manifold_vertices(mesh: trimesh.Trimesh) -> MeshDefect | None:
    """Detect vertices where the face fan is disconnected."""
    # A vertex is non-manifold if the faces around it don't form a
    # single connected fan. Use trimesh's adjacency to check.
    faces = mesh.faces
    num_vertices = len(mesh.vertices)

    # Build vertex -> faces mapping
    vertex_faces: dict[int, list[int]] = {i: [] for i in range(num_vertices)}
    for fi, face in enumerate(faces):
        for vi in face:
            vertex_faces[vi].append(fi)

    non_manifold_verts: list[int] = []
    for vi, face_list in vertex_faces.items():
        if len(face_list) < 2:
            continue
        # Check connectivity: faces sharing this vertex should form
        # a connected component via shared edges
        adj: dict[int, set[int]] = {f: set() for f in face_list}
        for i, fi in enumerate(face_list):
            fi_verts = set(faces[fi])
            for j in range(i + 1, len(face_list)):
                fj = face_list[j]
                fj_verts = set(faces[fj])
                # Two faces are adjacent if they share an edge
                # (2 vertices in common, including vi)
                shared = fi_verts & fj_verts
                if len(shared) >= 2:
                    adj[fi].add(fj)
                    adj[fj].add(fi)

        # BFS to check connectivity
        visited: set[int] = set()
        stack = [face_list[0]]
        while stack:
            f = stack.pop()
            if f in visited:
                continue
            visited.add(f)
            stack.extend(adj[f] - visited)

        if len(visited) < len(face_list):
            non_manifold_verts.append(vi)

    if not non_manifold_verts:
        return None

    return MeshDefect(
        defect_type=DefectType.non_manifold_vertices,
        severity=DefectType.non_manifold_vertices.severity,
        count=len(non_manifold_verts),
        affected_indices=sorted(non_manifold_verts),
        description=f"{len(non_manifold_verts)} non-manifold vertices (disconnected face fans)",
    )


def detect_boundary_edges(mesh: trimesh.Trimesh) -> MeshDefect | None:
    """Detect edges belonging to only 1 face (holes in the mesh)."""
    edges = mesh.edges_sorted
    edge_count: Counter[tuple[int, int]] = Counter()
    for edge in edges:
        edge_count[tuple(edge)] += 1

    boundary = [e for e, c in edge_count.items() if c == 1]
    if not boundary:
        return None

    affected = sorted({v for edge in boundary for v in edge})
    return MeshDefect(
        defect_type=DefectType.boundary_edges,
        severity=DefectType.boundary_edges.severity,
        count=len(boundary),
        affected_indices=affected,
        description=f"{len(boundary)} boundary edges (holes in mesh)",
    )


def detect_non_watertight(mesh: trimesh.Trimesh) -> MeshDefect | None:
    """Detect whether the mesh is not a closed volume."""
    if mesh.is_watertight:
        return None

    return MeshDefect(
        defect_type=DefectType.non_watertight,
        severity=DefectType.non_watertight.severity,
        count=1,
        affected_indices=[],
        description="Mesh is not watertight (not a closed volume)",
    )


def detect_inconsistent_normals(mesh: trimesh.Trimesh) -> MeshDefect | None:
    """Detect faces with inconsistent normal orientation.

    Checks adjacent face pairs for winding consistency by comparing
    the shared edge direction between neighbors.
    """
    if len(mesh.faces) == 0:
        return None

    face_adjacency = mesh.face_adjacency
    face_adjacency_edges = mesh.face_adjacency_edges

    inconsistent_faces: set[int] = set()
    for (fi, fj), (ei, ej) in zip(face_adjacency, face_adjacency_edges):
        # In a consistently wound mesh, the shared edge should appear
        # in opposite order in adjacent faces
        face_i = mesh.faces[fi]
        face_j = mesh.faces[fj]

        # Find edge order in each face
        def edge_order(face: np.ndarray, e0: int, e1: int) -> tuple[int, int]:
            idx = list(face)
            i0, i1 = idx.index(e0), idx.index(e1)
            return (i0, i1)

        oi = edge_order(face_i, ei, ej)
        oj = edge_order(face_j, ei, ej)

        # If edge goes in same direction in both faces, winding is inconsistent
        # (adjacent faces should traverse shared edge in opposite directions)
        same_direction = (oi[1] - oi[0]) % 3 == 1 and (oj[1] - oj[0]) % 3 == 1
        both_reverse = (oi[0] - oi[1]) % 3 == 1 and (oj[0] - oj[1]) % 3 == 1
        if same_direction or both_reverse:
            inconsistent_faces.add(fi)
            inconsistent_faces.add(fj)

    if not inconsistent_faces:
        return None

    return MeshDefect(
        defect_type=DefectType.inconsistent_normals,
        severity=DefectType.inconsistent_normals.severity,
        count=len(inconsistent_faces),
        affected_indices=sorted(inconsistent_faces),
        description=f"{len(inconsistent_faces)} faces with inconsistent normals",
    )


def detect_degenerate_faces(
    mesh: trimesh.Trimesh, area_threshold: float = 1e-10
) -> MeshDefect | None:
    """Detect zero-area or near-zero-area triangles."""
    areas = mesh.area_faces
    degenerate_mask = areas < area_threshold
    indices = np.where(degenerate_mask)[0].tolist()

    if not indices:
        return None

    return MeshDefect(
        defect_type=DefectType.degenerate_faces,
        severity=DefectType.degenerate_faces.severity,
        count=len(indices),
        affected_indices=indices,
        description=f"{len(indices)} degenerate faces (area < {area_threshold})",
    )


def detect_duplicate_vertices(
    mesh: trimesh.Trimesh, tolerance: float = 1e-8
) -> MeshDefect | None:
    """Detect vertices within merge tolerance of each other."""
    from scipy.spatial import cKDTree

    tree = cKDTree(mesh.vertices)
    pairs = tree.query_pairs(r=tolerance)

    if not pairs:
        return None

    affected = sorted({v for pair in pairs for v in pair})
    return MeshDefect(
        defect_type=DefectType.duplicate_vertices,
        severity=DefectType.duplicate_vertices.severity,
        count=len(pairs),
        affected_indices=affected,
        description=f"{len(pairs)} duplicate vertex pairs (within tolerance {tolerance})",
    )


def detect_duplicate_faces(mesh: trimesh.Trimesh) -> MeshDefect | None:
    """Detect identical face index triples (same vertices, any order)."""
    sorted_faces = np.sort(mesh.faces, axis=1)
    _, unique_idx, counts = np.unique(
        sorted_faces, axis=0, return_index=True, return_counts=True
    )

    duplicate_mask = counts > 1
    if not np.any(duplicate_mask):
        return None

    # Find all face indices that are duplicates
    duplicate_canonical = set(map(tuple, sorted_faces[unique_idx[duplicate_mask]]))
    affected = [
        i
        for i, face in enumerate(sorted_faces)
        if tuple(face) in duplicate_canonical
    ]

    num_duplicates = int(np.sum(counts[duplicate_mask] - 1))
    return MeshDefect(
        defect_type=DefectType.duplicate_faces,
        severity=DefectType.duplicate_faces.severity,
        count=num_duplicates,
        affected_indices=affected,
        description=f"{num_duplicates} duplicate faces",
    )


def detect_excessive_poly_count(
    mesh: trimesh.Trimesh, max_count: int = 1_000_000
) -> MeshDefect | None:
    """Detect face count above configurable threshold."""
    face_count = len(mesh.faces)
    if face_count <= max_count:
        return None

    return MeshDefect(
        defect_type=DefectType.excessive_poly_count,
        severity=DefectType.excessive_poly_count.severity,
        count=face_count,
        affected_indices=[],
        description=f"Excessive polygon count: {face_count:,} faces (threshold: {max_count:,})",
    )


def detect_self_intersecting(
    mesh: trimesh.Trimesh, max_faces_full_check: int = 100_000
) -> MeshDefect | None:
    """Detect self-intersecting faces using spatial index pre-filtering.

    For meshes with >max_faces_full_check faces, samples a subset
    and reports potential intersections.
    """
    triangles = mesh.triangles
    n_faces = len(triangles)

    if n_faces < 2:
        return None

    # For large meshes, sample a subset
    sampled = False
    if n_faces > max_faces_full_check:
        rng = np.random.default_rng(42)
        sample_idx = rng.choice(n_faces, size=max_faces_full_check, replace=False)
        check_triangles = triangles[sample_idx]
        face_index_map = sample_idx
        sampled = True
    else:
        check_triangles = triangles
        face_index_map = np.arange(n_faces)

    # Build bounding boxes for each triangle
    tri_mins = check_triangles.min(axis=1)
    tri_maxs = check_triangles.max(axis=1)

    # Use R-tree-like approach: spatial hashing via grid cells
    # Determine grid cell size from average triangle extent
    extents = tri_maxs - tri_mins
    cell_size = max(float(np.mean(extents)) * 2, 1e-10)

    # Hash each triangle to grid cells it overlaps
    min_cells = np.floor(tri_mins / cell_size).astype(int)
    max_cells = np.floor(tri_maxs / cell_size).astype(int)

    cell_map: dict[tuple[int, int, int], list[int]] = {}
    for i in range(len(check_triangles)):
        for x in range(min_cells[i, 0], max_cells[i, 0] + 1):
            for y in range(min_cells[i, 1], max_cells[i, 1] + 1):
                for z in range(min_cells[i, 2], max_cells[i, 2] + 1):
                    key = (x, y, z)
                    if key not in cell_map:
                        cell_map[key] = []
                    cell_map[key].append(i)

    # Find candidate pairs from cells
    candidate_pairs: set[tuple[int, int]] = set()
    for indices in cell_map.values():
        if len(indices) < 2:
            continue
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                i, j = indices[a], indices[b]
                # Skip face pairs that share vertices (adjacent faces)
                fi = face_index_map[i]
                fj = face_index_map[j]
                shared = set(mesh.faces[fi]) & set(mesh.faces[fj])
                if len(shared) >= 1:
                    continue  # Skip adjacent faces (sharing any vertex)
                candidate_pairs.add((min(i, j), max(i, j)))

    if not candidate_pairs:
        return None

    # Test candidate pairs with triangle-triangle intersection
    intersecting_faces: set[int] = set()
    tested = 0
    max_tests = 50_000  # Cap to keep runtime reasonable

    for i, j in candidate_pairs:
        if tested >= max_tests:
            break
        if _triangles_intersect(check_triangles[i], check_triangles[j]):
            intersecting_faces.add(int(face_index_map[i]))
            intersecting_faces.add(int(face_index_map[j]))
        tested += 1

    if not intersecting_faces:
        return None

    suffix = " (sampled)" if sampled else ""
    return MeshDefect(
        defect_type=DefectType.self_intersecting,
        severity=DefectType.self_intersecting.severity,
        count=len(intersecting_faces),
        affected_indices=sorted(intersecting_faces),
        description=f"{len(intersecting_faces)} self-intersecting faces detected{suffix}",
    )


def _triangles_intersect(tri_a: np.ndarray, tri_b: np.ndarray) -> bool:
    """Test if two triangles intersect using Moller's method.

    Fast rejection via separating axis theorem on triangle planes.
    """
    tol = 1e-8

    # Compute plane of triangle A
    edge1_a = tri_a[1] - tri_a[0]
    edge2_a = tri_a[2] - tri_a[0]
    normal_a = np.cross(edge1_a, edge2_a)
    norm_len_a = np.linalg.norm(normal_a)
    if norm_len_a < tol:
        return False  # Degenerate triangle
    normal_a = normal_a / norm_len_a
    d_a = -np.dot(normal_a, tri_a[0])

    # Signed distances of B's vertices to A's plane
    dist_b = np.dot(tri_b, normal_a) + d_a

    # If all vertices of B are on same side or on the plane, no intersection
    if np.all(dist_b >= -tol) or np.all(dist_b <= tol):
        return False

    # Compute plane of triangle B
    edge1_b = tri_b[1] - tri_b[0]
    edge2_b = tri_b[2] - tri_b[0]
    normal_b = np.cross(edge1_b, edge2_b)
    norm_len_b = np.linalg.norm(normal_b)
    if norm_len_b < tol:
        return False  # Degenerate triangle
    normal_b = normal_b / norm_len_b
    d_b = -np.dot(normal_b, tri_b[0])

    # Signed distances of A's vertices to B's plane
    dist_a = np.dot(tri_a, normal_b) + d_b

    # If all vertices of A are on same side or on the plane, no intersection
    if np.all(dist_a >= -tol) or np.all(dist_a <= tol):
        return False

    # Both triangles have vertices on both sides of each other's plane
    # — genuinely intersecting
    return True


# Registry of all detectors for easy iteration
ALL_DETECTORS = [
    detect_non_manifold_edges,
    detect_non_manifold_vertices,
    detect_boundary_edges,
    detect_non_watertight,
    detect_inconsistent_normals,
    detect_degenerate_faces,
    detect_duplicate_vertices,
    detect_duplicate_faces,
    detect_excessive_poly_count,
    detect_self_intersecting,
]
