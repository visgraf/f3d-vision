"""Reusable instance-keyed memory for already measured 3-D samples.

This module owns the representation-level mechanism established by Partition-Graph
Phases 7-8: valid measured geometry is routed by the *observed* instance identity,
independently of which target was active when the measurement was acquired.

It deliberately does not define object association, deduplication, surfel fusion,
confidence weighting, or evaluation semantics.  Samples and their provenance are
retained in deterministic insertion order.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


def valid_patch_measurements(
    patch: Mapping[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return finite, valid, positive-instance measurements from one saved patch.

    The returned XYZ is float64, matching the historical patch helper used by the
    retrospective partition experiments.  The boolean mask is in the original
    patch raster shape so callers that need chart bookkeeping can retain it.
    """
    xyz = np.asarray(patch["xyz_h"], np.float64)
    ids = np.asarray(patch["instance_id"], np.int32)
    valid = np.asarray(patch["valid"], bool)
    if (
        xyz.ndim != 3
        or xyz.shape[2] != 3
        or ids.shape != xyz.shape[:2]
        or valid.shape != ids.shape
    ):
        raise ValueError(
            f"bad saved patch shapes xyz={xyz.shape} ids={ids.shape} valid={valid.shape}"
        )
    mask = valid & (ids > 0) & np.isfinite(xyz).all(axis=-1)
    return xyz[mask], ids[mask], mask


def _finite_xyz(value: np.ndarray) -> np.ndarray:
    xyz = np.asarray(value, np.float64).reshape(-1, 3)
    return xyz[np.isfinite(xyz).all(axis=1)]


def effective_target_geometry(
    historical_map_xyz_h: np.ndarray,
    measured_instance_xyz_h: np.ndarray,
) -> np.ndarray:
    """Return historical finite map XYZ followed by measured instance XYZ.

    Duplicates are intentionally retained.  This is the exact representation-level
    union used by Phase 8: no averaging, deduplication, or new fusion semantics.
    """
    historical = _finite_xyz(historical_map_xyz_h)
    measured = _finite_xyz(measured_instance_xyz_h)
    if not len(historical):
        return measured.copy()
    if not len(measured):
        return historical.copy()
    return np.vstack((historical, measured))


@dataclass(frozen=True)
class MeasurementSnapshot:
    """Read-only aligned measurements and provenance for one observed instance."""

    xyz_h: np.ndarray
    source_global_index: np.ndarray
    source_active_target_id: np.ndarray

    def __post_init__(self) -> None:
        xyz = np.asarray(self.xyz_h, np.float32).reshape(-1, 3).copy()
        global_index = np.asarray(self.source_global_index, np.int32).reshape(-1).copy()
        active_target = np.asarray(self.source_active_target_id, np.int32).reshape(-1).copy()
        n = len(xyz)
        if len(global_index) != n or len(active_target) != n:
            raise ValueError(
                "measurement/provenance length mismatch: "
                f"xyz={n} global={len(global_index)} active_target={len(active_target)}"
            )
        if n and not np.isfinite(xyz).all():
            raise ValueError("measurement snapshot contains non-finite XYZ")
        xyz.setflags(write=False)
        global_index.setflags(write=False)
        active_target.setflags(write=False)
        object.__setattr__(self, "xyz_h", xyz)
        object.__setattr__(self, "source_global_index", global_index)
        object.__setattr__(self, "source_active_target_id", active_target)

    @classmethod
    def empty(cls) -> "MeasurementSnapshot":
        return cls(
            xyz_h=np.empty((0, 3), np.float32),
            source_global_index=np.empty((0,), np.int32),
            source_active_target_id=np.empty((0,), np.int32),
        )

    def cross_target_mask(self, target_id: int) -> np.ndarray:
        return np.asarray(self.source_active_target_id != int(target_id), bool)


class InstanceMeasurementMemory:
    """Append-only measured-geometry memory keyed by observed instance identity."""

    def __init__(self) -> None:
        self._xyz: dict[int, list[np.ndarray]] = {}
        self._global: dict[int, list[np.ndarray]] = {}
        self._active_target: dict[int, list[np.ndarray]] = {}

    def append_patch(
        self,
        patch: Mapping[str, np.ndarray],
        *,
        source_global_index: int,
        source_active_target_id: int,
    ) -> dict[int, int]:
        """Route one patch by observed instance id and retain aligned provenance."""
        global_index = int(source_global_index)
        active_target = int(source_active_target_id)
        if global_index < 0:
            raise ValueError("source_global_index must be >= 0")
        if active_target <= 0:
            raise ValueError("source_active_target_id must be > 0")

        xyz, ids, _mask = valid_patch_measurements(patch)
        counts: dict[int, int] = {}
        for observed in sorted(int(v) for v in np.unique(ids) if int(v) > 0):
            q = xyz[ids == observed].astype(np.float32, copy=True)
            if not len(q):
                continue
            self._xyz.setdefault(observed, []).append(q)
            self._global.setdefault(observed, []).append(
                np.full(len(q), global_index, np.int32)
            )
            self._active_target.setdefault(observed, []).append(
                np.full(len(q), active_target, np.int32)
            )
            counts[observed] = int(len(q))
        return counts

    def instance_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._xyz))

    def snapshot(self, instance_id: int) -> MeasurementSnapshot:
        iid = int(instance_id)
        xyz_chunks = self._xyz.get(iid, [])
        if not xyz_chunks:
            return MeasurementSnapshot.empty()
        xyz = np.vstack(
            [np.asarray(chunk, np.float32).reshape(-1, 3) for chunk in xyz_chunks]
        )
        global_index = np.concatenate(
            [np.asarray(chunk, np.int32).reshape(-1) for chunk in self._global[iid]]
        )
        active_target = np.concatenate(
            [
                np.asarray(chunk, np.int32).reshape(-1)
                for chunk in self._active_target[iid]
            ]
        )
        return MeasurementSnapshot(
            xyz_h=xyz,
            source_global_index=global_index,
            source_active_target_id=active_target,
        )
