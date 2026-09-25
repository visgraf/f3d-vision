"""Core spherical partition + primal/dual graph data model.

The model deliberately separates two partitions:

* scene partition: connected object components plus base/complement;
* observation overlay: which spherical territory has been sampled by each eye.

There is no physical ``VOID`` region kind.  A gap may be unobserved, monocular,
missing depth, occluded, or simply unassigned base.  Those are epistemic or
visibility states and should not be conflated with scene identity.

The graph is representation-only.  No controller, ranking rule, segmentation
algorithm, or object-discovery policy is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional
import json

import numpy as np

from .sphere import normalize_rows


class RegionKind(str, Enum):
    OBJECT_COMPONENT = "object_component"
    BASE = "base"


class EyeVisibility(str, Enum):
    UNOBSERVED = "unobserved"
    LEFT_ONLY = "left_only"
    RIGHT_ONLY = "right_only"
    BINOCULAR = "binocular"


class BoundaryKind(str, Enum):
    UNKNOWN = "unknown"
    OBJECT_BASE = "object_base"
    OBJECT_OBJECT = "object_object"
    OCCLUSION = "occlusion"
    DEPTH_DISCONTINUITY = "depth_discontinuity"
    SMOOTH_CONTINUATION = "smooth_continuation"


def _jsonable(v: Any) -> Any:
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


@dataclass(frozen=True)
class PartitionRegion:
    """One connected face of the spherical scene partition.

    Multiple disconnected regions may share the same ``object_id``.  This is a
    first-class feature: an object may disappear behind an occluder and reappear
    elsewhere while remaining one object hypothesis.
    """

    region_id: str
    kind: RegionKind
    object_id: Optional[str] = None
    point_ids: tuple[int, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.region_id:
            raise ValueError("region_id must be non-empty")
        if self.kind is RegionKind.OBJECT_COMPONENT and not self.object_id:
            raise ValueError(f"object component {self.region_id} requires object_id")
        if self.kind is RegionKind.BASE and self.object_id is not None:
            raise ValueError(f"base region {self.region_id} cannot carry object_id")


@dataclass(frozen=True)
class ObjectHypothesis:
    object_id: str
    region_ids: tuple[str, ...]
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.object_id:
            raise ValueError("object_id must be non-empty")
        if not self.region_ids:
            raise ValueError(f"object {self.object_id} has no regions")
        if len(set(self.region_ids)) != len(self.region_ids):
            raise ValueError(f"object {self.object_id} repeats a region")


@dataclass(frozen=True)
class BoundaryChain:
    """One embedded boundary edge.

    ``sphere_xyz`` is always stored as unit directions and is therefore chart
    independent.  ``world_xyz`` and the two normal fields are optional geometric
    attributes that permit the same edge to be reasoned about in 3-D.
    """

    boundary_id: str
    region_a: str
    region_b: str
    sphere_xyz: np.ndarray
    closed: bool = False
    kind: BoundaryKind = BoundaryKind.UNKNOWN
    world_xyz: Optional[np.ndarray] = None
    normal_a: Optional[np.ndarray] = None
    normal_b: Optional[np.ndarray] = None
    depth_a: Optional[np.ndarray] = None
    depth_b: Optional[np.ndarray] = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.boundary_id:
            raise ValueError("boundary_id must be non-empty")
        if self.region_a == self.region_b:
            raise ValueError(f"boundary {self.boundary_id} has identical incident regions")
        s = normalize_rows(self.sphere_xyz)
        if len(s) < 2:
            raise ValueError(f"boundary {self.boundary_id} needs at least two samples")
        for name, arr in (
            ("world_xyz", self.world_xyz),
            ("normal_a", self.normal_a),
            ("normal_b", self.normal_b),
        ):
            if arr is not None:
                a = np.asarray(arr)
                if a.shape != s.shape:
                    raise ValueError(f"{name} shape {a.shape} != sphere_xyz shape {s.shape}")
        for name, arr in (("depth_a", self.depth_a), ("depth_b", self.depth_b)):
            if arr is not None and np.asarray(arr).shape != (len(s),):
                raise ValueError(f"{name} must have shape ({len(s)},)")


@dataclass(frozen=True)
class ObservationFootprint:
    """Projection of one tangent-plane observation onto the viewing sphere."""

    fixation_id: str
    eye: EyeVisibility
    polygon_sphere_xyz: np.ndarray
    gaze_sphere_xyz: np.ndarray
    sequence_index: int
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        p = normalize_rows(self.polygon_sphere_xyz)
        if len(p) < 3:
            raise ValueError(f"footprint {self.fixation_id} needs >=3 polygon vertices")
        g = np.asarray(self.gaze_sphere_xyz, dtype=np.float64).reshape(-1)
        if g.shape != (3,) or np.linalg.norm(g) <= 1e-12:
            raise ValueError(f"footprint {self.fixation_id} has invalid gaze direction")
        if self.sequence_index < 0:
            raise ValueError("sequence_index must be >= 0")


@dataclass
class ObservationOverlay:
    footprints: list[ObservationFootprint] = field(default_factory=list)

    def validate(self) -> None:
        seen: set[tuple[str, str]] = set()
        for fp in self.footprints:
            fp.validate()
            key = (fp.fixation_id, fp.eye.value)
            if key in seen:
                raise ValueError(f"duplicate footprint {key}")
            seen.add(key)

    def append(self, fp: ObservationFootprint) -> None:
        fp.validate()
        self.footprints.append(fp)


@dataclass
class ScenePartitionGraph:
    """Coupled scene partition, object grouping, embedded boundaries and overlay.

    The *primal graph* is represented by the embedded boundary chains.  The
    *dual graph* is derived exactly: each region is a dual node and each boundary
    produces one adjacency edge between its incident regions.  This avoids two
    separately-maintained topologies drifting out of agreement.
    """

    regions: Dict[str, PartitionRegion] = field(default_factory=dict)
    objects: Dict[str, ObjectHypothesis] = field(default_factory=dict)
    boundaries: Dict[str, BoundaryChain] = field(default_factory=dict)
    observations: ObservationOverlay = field(default_factory=ObservationOverlay)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for rid, r in self.regions.items():
            if rid != r.region_id:
                raise ValueError(f"region key {rid} != region_id {r.region_id}")
            r.validate()
        for oid, obj in self.objects.items():
            if oid != obj.object_id:
                raise ValueError(f"object key {oid} != object_id {obj.object_id}")
            obj.validate()
            for rid in obj.region_ids:
                if rid not in self.regions:
                    raise ValueError(f"object {oid} references missing region {rid}")
                rr = self.regions[rid]
                if rr.kind is not RegionKind.OBJECT_COMPONENT or rr.object_id != oid:
                    raise ValueError(f"object {oid} inconsistent with region {rid}")
        for rid, r in self.regions.items():
            if r.kind is RegionKind.OBJECT_COMPONENT:
                if r.object_id not in self.objects or rid not in self.objects[r.object_id].region_ids:
                    raise ValueError(f"region {rid} is not owned by object hypothesis {r.object_id}")
        for bid, b in self.boundaries.items():
            if bid != b.boundary_id:
                raise ValueError(f"boundary key {bid} != boundary_id {b.boundary_id}")
            b.validate()
            if b.region_a not in self.regions or b.region_b not in self.regions:
                raise ValueError(f"boundary {bid} references missing region")
        self.observations.validate()

    def dual_edges(self) -> list[dict[str, Any]]:
        self.validate()
        return [
            {
                "boundary_id": b.boundary_id,
                "region_a": b.region_a,
                "region_b": b.region_b,
                "kind": b.kind.value,
                "attributes": dict(b.attributes),
            }
            for b in self.boundaries.values()
        ]

    def object_components(self, object_id: str) -> tuple[PartitionRegion, ...]:
        obj = self.objects[object_id]
        return tuple(self.regions[rid] for rid in obj.region_ids)

    def summary(self) -> dict[str, Any]:
        self.validate()
        disconnected = sum(1 for o in self.objects.values() if len(o.region_ids) > 1)
        return {
            "regions": len(self.regions),
            "object_hypotheses": len(self.objects),
            "objects_with_multiple_visible_components": disconnected,
            "base_regions": sum(r.kind is RegionKind.BASE for r in self.regions.values()),
            "boundaries": len(self.boundaries),
            "dual_edges": len(self.boundaries),
            "observation_footprints": len(self.observations.footprints),
        }

    def _metadata_dict(self, array_keys: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
        return {
            "format": "f3d-vision-scene-partition-v1",
            "regions": [
                {
                    "region_id": r.region_id,
                    "kind": r.kind.value,
                    "object_id": r.object_id,
                    "point_ids": list(r.point_ids),
                    "attributes": _jsonable(dict(r.attributes)),
                }
                for r in self.regions.values()
            ],
            "objects": [
                {
                    "object_id": o.object_id,
                    "region_ids": list(o.region_ids),
                    "attributes": _jsonable(dict(o.attributes)),
                }
                for o in self.objects.values()
            ],
            "boundaries": [
                {
                    "boundary_id": b.boundary_id,
                    "region_a": b.region_a,
                    "region_b": b.region_b,
                    "closed": bool(b.closed),
                    "kind": b.kind.value,
                    "attributes": _jsonable(dict(b.attributes)),
                    "arrays": dict(array_keys[b.boundary_id]),
                }
                for b in self.boundaries.values()
            ],
            "observations": [
                {
                    "fixation_id": fp.fixation_id,
                    "eye": fp.eye.value,
                    "sequence_index": int(fp.sequence_index),
                    "attributes": _jsonable(dict(fp.attributes)),
                    "arrays": dict(array_keys[f"obs:{i}"]),
                }
                for i, fp in enumerate(self.observations.footprints)
            ],
            "attributes": _jsonable(dict(self.attributes)),
            "summary": self.summary(),
        }

    def save(self, directory: str | Path) -> Path:
        """Write portable metadata JSON + numeric arrays NPZ."""
        self.validate()
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        arrays: dict[str, np.ndarray] = {}
        array_keys: dict[str, dict[str, str]] = {}
        for i, b in enumerate(self.boundaries.values()):
            prefix = f"b{i:04d}"
            keys: dict[str, str] = {}
            fields = {
                "sphere_xyz": normalize_rows(b.sphere_xyz),
                "world_xyz": b.world_xyz,
                "normal_a": b.normal_a,
                "normal_b": b.normal_b,
                "depth_a": b.depth_a,
                "depth_b": b.depth_b,
            }
            for name, value in fields.items():
                if value is not None:
                    k = f"{prefix}_{name}"
                    arrays[k] = np.asarray(value)
                    keys[name] = k
            array_keys[b.boundary_id] = keys
        for i, fp in enumerate(self.observations.footprints):
            prefix = f"o{i:04d}"
            pkey = f"{prefix}_polygon"
            gkey = f"{prefix}_gaze"
            arrays[pkey] = normalize_rows(fp.polygon_sphere_xyz)
            arrays[gkey] = normalize_rows(np.asarray(fp.gaze_sphere_xyz).reshape(1, 3))[0]
            array_keys[f"obs:{i}"] = {"polygon_sphere_xyz": pkey, "gaze_sphere_xyz": gkey}
        np.savez_compressed(out / "arrays.npz", **arrays)
        (out / "graph.json").write_text(
            json.dumps(self._metadata_dict(array_keys), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return out

    @classmethod
    def load(cls, directory: str | Path) -> "ScenePartitionGraph":
        src = Path(directory)
        meta = json.loads((src / "graph.json").read_text(encoding="utf-8"))
        if meta.get("format") != "f3d-vision-scene-partition-v1":
            raise ValueError(f"unsupported format {meta.get('format')!r}")
        with np.load(src / "arrays.npz", allow_pickle=False) as arr:
            regions = {
                r["region_id"]: PartitionRegion(
                    region_id=r["region_id"],
                    kind=RegionKind(r["kind"]),
                    object_id=r.get("object_id"),
                    point_ids=tuple(int(x) for x in r.get("point_ids", [])),
                    attributes=r.get("attributes", {}),
                )
                for r in meta["regions"]
            }
            objects = {
                o["object_id"]: ObjectHypothesis(
                    object_id=o["object_id"],
                    region_ids=tuple(o["region_ids"]),
                    attributes=o.get("attributes", {}),
                )
                for o in meta["objects"]
            }
            boundaries: dict[str, BoundaryChain] = {}
            for b in meta["boundaries"]:
                a = b["arrays"]
                get = lambda name: np.array(arr[a[name]]) if name in a else None
                boundaries[b["boundary_id"]] = BoundaryChain(
                    boundary_id=b["boundary_id"],
                    region_a=b["region_a"],
                    region_b=b["region_b"],
                    sphere_xyz=get("sphere_xyz"),
                    closed=bool(b["closed"]),
                    kind=BoundaryKind(b["kind"]),
                    world_xyz=get("world_xyz"),
                    normal_a=get("normal_a"),
                    normal_b=get("normal_b"),
                    depth_a=get("depth_a"),
                    depth_b=get("depth_b"),
                    attributes=b.get("attributes", {}),
                )
            observations = ObservationOverlay()
            for o in meta["observations"]:
                a = o["arrays"]
                observations.append(
                    ObservationFootprint(
                        fixation_id=o["fixation_id"],
                        eye=EyeVisibility(o["eye"]),
                        polygon_sphere_xyz=np.array(arr[a["polygon_sphere_xyz"]]),
                        gaze_sphere_xyz=np.array(arr[a["gaze_sphere_xyz"]]),
                        sequence_index=int(o["sequence_index"]),
                        attributes=o.get("attributes", {}),
                    )
                )
        g = cls(
            regions=regions,
            objects=objects,
            boundaries=boundaries,
            observations=observations,
            attributes=meta.get("attributes", {}),
        )
        g.validate()
        return g
