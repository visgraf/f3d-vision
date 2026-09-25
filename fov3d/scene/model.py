"""Core spherical partition + primal/dual graph data model.

The model keeps two structures separate:

* scene partition: connected object components plus base/complement;
* observation overlay: tangent-footprint samples contributed by one or both eyes.

There is no physical ``VOID`` region kind.  Unobserved territory is a derived
visibility state of the observation overlay, not a scene identity.

Phase 2 hardens the representation while retaining its Phase-1 intent.  Array
fields are validated explicitly and serialization no longer silently renormalizes
them, so a valid graph round-trips bit-exactly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
import json

import numpy as np


class RegionKind(str, Enum):
    OBJECT_COMPONENT = "object_component"
    BASE = "base"


class FootprintEye(str, Enum):
    """Which sensor view produced an observation footprint.

    ``BINOCULAR`` is allowed for synthetic/aggregated footprints.  ``UNOBSERVED``
    is intentionally absent: unobserved is the complement of all footprints.
    """

    LEFT = "left"
    RIGHT = "right"
    BINOCULAR = "binocular"


class EyeVisibility(str, Enum):
    """Derived visibility state of spherical territory."""

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


UNIT_TOL = 1e-6


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


def _vec3_rows(name: str, value: Any, *, unit: bool = False) -> np.ndarray:
    a = np.asarray(value, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N,3), got {a.shape}")
    if not np.isfinite(a).all():
        raise ValueError(f"{name} contains non-finite values")
    if unit:
        n = np.linalg.norm(a, axis=1)
        if np.any(n <= 1e-12) or np.any(np.abs(n - 1.0) > UNIT_TOL):
            raise ValueError(f"{name} rows must already be unit length within {UNIT_TOL:g}")
    return a


def _unit_vec3(name: str, value: Any) -> np.ndarray:
    a = np.asarray(value, dtype=np.float64).reshape(-1)
    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError(f"{name} must be one finite 3-vector")
    n = float(np.linalg.norm(a))
    if n <= 1e-12 or abs(n - 1.0) > UNIT_TOL:
        raise ValueError(f"{name} must already be unit length within {UNIT_TOL:g}")
    return a


@dataclass(frozen=True, eq=False)
class PartitionRegion:
    """One connected face of the spherical scene partition."""

    __hash__ = None
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
        if len(set(self.point_ids)) != len(self.point_ids):
            raise ValueError(f"region {self.region_id} repeats a point id")


@dataclass(frozen=True, eq=False)
class ObjectHypothesis:
    __hash__ = None
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


@dataclass(frozen=True, eq=False)
class BoundaryChain:
    """One embedded boundary edge.

    ``sphere_xyz`` contains chart-independent unit directions in the coordinate
    frame declared by the enclosing graph.  Optional ``world_xyz``, normals and
    depths couple topology back to geometry.
    """

    __hash__ = None
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
        s = _vec3_rows("sphere_xyz", self.sphere_xyz, unit=True)
        if len(s) < 2:
            raise ValueError(f"boundary {self.boundary_id} needs at least two samples")
        if self.world_xyz is not None:
            a = _vec3_rows("world_xyz", self.world_xyz)
            if a.shape != s.shape:
                raise ValueError(f"world_xyz shape {a.shape} != sphere_xyz shape {s.shape}")
        for name, arr in (("normal_a", self.normal_a), ("normal_b", self.normal_b)):
            if arr is not None:
                a = _vec3_rows(name, arr, unit=True)
                if a.shape != s.shape:
                    raise ValueError(f"{name} shape {a.shape} != sphere_xyz shape {s.shape}")
        for name, arr in (("depth_a", self.depth_a), ("depth_b", self.depth_b)):
            if arr is not None:
                a = np.asarray(arr, dtype=np.float64)
                if a.shape != (len(s),) or not np.isfinite(a).all() or np.any(a <= 0):
                    raise ValueError(f"{name} must be finite positive shape ({len(s)},)")
        if self.kind is BoundaryKind.OCCLUSION:
            front = self.attributes.get("front_region")
            back = self.attributes.get("back_region")
            incident = {self.region_a, self.region_b}
            if front not in incident or back not in incident or front == back:
                raise ValueError(
                    f"occlusion {self.boundary_id} must name its two incident regions as front/back"
                )


@dataclass(frozen=True, eq=False)
class ObservationFootprint:
    """Projection of one tangent-plane observation onto the viewing sphere."""

    __hash__ = None
    fixation_id: str
    eye: FootprintEye
    polygon_sphere_xyz: np.ndarray
    gaze_sphere_xyz: np.ndarray
    sequence_index: int
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        p = _vec3_rows("polygon_sphere_xyz", self.polygon_sphere_xyz, unit=True)
        if len(p) < 3:
            raise ValueError(f"footprint {self.fixation_id} needs >=3 polygon vertices")
        _unit_vec3("gaze_sphere_xyz", self.gaze_sphere_xyz)
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
            # Deliberately DO NOT forbid boundaries between regions of the same object.
            # A self-occlusion, crease, or depth discontinuity can separate two partition
            # faces without implying two physical objects.
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
            "format": "f3d-vision-scene-partition-v2",
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
        """Write portable metadata JSON + numeric arrays NPZ without changing arrays."""
        self.validate()
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        arrays: dict[str, np.ndarray] = {}
        array_keys: dict[str, dict[str, str]] = {}
        for i, b in enumerate(self.boundaries.values()):
            prefix = f"b{i:04d}"
            keys: dict[str, str] = {}
            fields = {
                "sphere_xyz": b.sphere_xyz,
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
            arrays[pkey] = np.asarray(fp.polygon_sphere_xyz)
            arrays[gkey] = np.asarray(fp.gaze_sphere_xyz)
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
        fmt = meta.get("format")
        if fmt not in {"f3d-vision-scene-partition-v1", "f3d-vision-scene-partition-v2"}:
            raise ValueError(f"unsupported format {fmt!r}")
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
                eye_text = str(o["eye"])
                if fmt.endswith("v1"):
                    legacy = {
                        "left_only": FootprintEye.LEFT,
                        "right_only": FootprintEye.RIGHT,
                        "binocular": FootprintEye.BINOCULAR,
                    }
                    if eye_text not in legacy:
                        raise ValueError(f"legacy footprint eye {eye_text!r} is not an observation")
                    eye = legacy[eye_text]
                else:
                    eye = FootprintEye(eye_text)
                observations.append(
                    ObservationFootprint(
                        fixation_id=o["fixation_id"],
                        eye=eye,
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
