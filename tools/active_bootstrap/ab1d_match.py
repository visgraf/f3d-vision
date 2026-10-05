"""Active Bootstrap-1d: the frozen primitive natural matcher (contract sections 6-14).

    direct raw-image spherical epipolar search + 5 x 5 local angular patch + ZNCC + one 1-D parabola

For every left nominal raw-core pixel: its calibrated ray d_L fixes one physical epipolar plane (it contains the +X
baseline).  The ORIGINAL right raw tangent image is searched along the raw epipolar line of that plane,
l = K_R^-T R_hc_R^T n with n = b x d_L, from the infinite-range point q_inf in the direction of increasing theta_R, at
1-pixel Euclidean spacing over the whole physically admissible segment (no depth interval).  Each candidate is scored by
ZNCC between 5 x 5 patches sampled at equal local angular spacing in the (theta, phi) chart; the best discrete peak is
refined once by a 3-point parabola.  The input is exactly the calibration and the RGB observation; the module never sees
Position, Object Index, the oracle or any truth.  Arithmetic on candidates is explicit (no BLAS) and per-pixel, so the
result does not depend on the batch or thread layout.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_geometry as BG  # noqa: E402  (accepted spherical convention, read-only)
import ab1d_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted sensor geometry, read-only)
import fsg_stereo as FS  # noqa: E402  (accepted photometric conversion + constants only; no SGBM call)

BASELINE = np.asarray(SP.BASELINE_AXIS, np.float64)
OBS_KEYS = ("rgb_L", "rgb_R")


@dataclass(frozen=True)
class Params:
    """The frozen matcher constants (contract section 32).  Only the synthetic / mutation tests pass other values."""
    patch_half: int = SP.PATCH_HALF
    spacing: float = SP.SPACING_PX
    min_std: float = SP.MIN_LOCAL_STD_U8
    tie_eps: float = SP.TIE_EPS
    top_k: int = SP.TOP_K
    separation: float = SP.PEAK_SEPARATION_PX
    bound: float = SP.REFINE_BOUND_SAMPLES
    luma: tuple = field(default=SP.LUMA)


FROZEN = Params()


# ------------------------------------------------------------------ photometry (section 7)
def validate_observation(obs: dict, wh: tuple[int, int]) -> None:
    if set(obs) != set(OBS_KEYS):
        raise ValueError(f"the RGB observation must contain exactly {list(OBS_KEYS)}, not {sorted(obs)}")
    w, h = wh
    for k in OBS_KEYS:
        a = np.asarray(obs[k])
        if a.shape != (h, w, 3) or a.dtype.kind != "f" or not np.isfinite(a).all():
            raise ValueError(f"bad {k}")


def gray(rgb: np.ndarray, p: Params = FROZEN) -> np.ndarray:
    u = FS.linear_to_u8(rgb).astype(np.float64)
    return p.luma[0] * u[..., 0] + p.luma[1] * u[..., 1] + p.luma[2] * u[..., 2]


# ------------------------------------------------------------------ cameras and rays (section 6)
class Cam:
    def __init__(self, eye: dict, wh, r_hc=None) -> None:
        self.K = np.asarray(eye["K"], np.float64)
        self.R = np.asarray(eye["R_hc"] if r_hc is None else r_hc, np.float64)
        self.Kinv = np.linalg.inv(self.K)
        self.M = self.K @ self.R.T          # head direction -> homogeneous pixel
        self.A = self.R @ self.Kinv         # l^T = n^T R K^-1
        self.W, self.H = int(wh[0]), int(wh[1])
        self.f = float(self.K[0, 0])


def make_cams(c: dict) -> tuple[Cam, Cam]:
    return Cam(c["eyes"][0], c["image_size_wh"]), Cam(c["eyes"][1], c["image_size_wh"])


def rays(cam: Cam, u, v):
    """fsg_geometry.rays_h, written out: d = unit(R K^-1 (u, v, 1))."""
    ki, r = cam.Kinv, cam.R
    b0 = ki[0, 0] * u + ki[0, 1] * v + ki[0, 2]
    b1 = ki[1, 0] * u + ki[1, 1] * v + ki[1, 2]
    b2 = ki[2, 0] * u + ki[2, 1] * v + ki[2, 2]
    d0 = r[0, 0] * b0 + r[0, 1] * b1 + r[0, 2] * b2
    d1 = r[1, 0] * b0 + r[1, 1] * b1 + r[1, 2] * b2
    d2 = r[2, 0] * b0 + r[2, 1] * b1 + r[2, 2] * b2
    n = np.sqrt(d0 * d0 + d1 * d1 + d2 * d2)
    return d0 / n, d1 / n, d2 / n


def theta_phi(d0, d1, d2):
    """The accepted AB1b convention: theta from +X, phi = atan2(d_y, -d_z)."""
    return np.arctan2(np.hypot(d1, d2), d0), np.arctan2(d1, -d2)


def direction(theta, phi):
    s = np.sin(theta)
    return np.cos(theta), s * np.sin(phi), -(s * np.cos(phi))


def project(cam: Cam, d0, d1, d2):
    m = cam.M
    h0 = m[0, 0] * d0 + m[0, 1] * d1 + m[0, 2] * d2
    h1 = m[1, 0] * d0 + m[1, 1] * d1 + m[1, 2] * d2
    h2 = m[2, 0] * d0 + m[2, 1] * d1 + m[2, 2] * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        return h0 / h2, h1 / h2, h2


# ------------------------------------------------------------------ the angular patch (section 8)
def bilinear(g: np.ndarray, u, v):
    """Bilinear sample at continuous pixel-centre coordinates; inside iff 0 <= u <= W - 1 and 0 <= v <= H - 1."""
    h, w = g.shape
    with np.errstate(invalid="ignore"):
        inside = (u >= 0) & (u <= w - 1) & (v >= 0) & (v <= h - 1)
    uu = np.where(inside, u, 0.0)
    vv = np.where(inside, v, 0.0)
    x0 = np.minimum(np.floor(uu), w - 2)
    y0 = np.minimum(np.floor(vv), h - 2)
    fx, fy = uu - x0, vv - y0
    i = y0.astype(np.int64) * w + x0.astype(np.int64)
    f = g.ravel()
    top = (1.0 - fx) * f[i] + fx * f[i + 1]
    bot = (1.0 - fx) * f[i + w] + fx * f[i + w + 1]
    return np.where(inside, (1.0 - fy) * top + fy * bot, np.nan), inside


def patch(cam: Cam, g: np.ndarray, theta_c, phi_c, dlt: float, p: Params = FROZEN):
    """The 25 (i-major, j-minor) samples at theta_c + i delta, phi_c + j delta / sin(theta_c); NaN rows if not inside."""
    off = np.arange(-p.patch_half, p.patch_half + 1, dtype=np.float64)
    theta_c, phi_c = np.asarray(theta_c, np.float64), np.asarray(phi_c, np.float64)
    th = theta_c[..., None] + off * dlt
    step = dlt / np.sin(theta_c)
    ph = phi_c[..., None] + off * step[..., None]
    st, ct = np.sin(th)[..., :, None], np.cos(th)[..., :, None]
    sp, cp = np.sin(ph)[..., None, :], np.cos(ph)[..., None, :]
    n = off.size
    d0 = np.broadcast_to(ct, ct.shape[:-1] + (n,))
    d1 = st * sp
    d2 = -(st * cp)
    u, v, h2 = project(cam, d0, d1, d2)
    vals, inside = bilinear(g, u, v)
    inside &= h2 > SP.Z_EPS
    shape = theta_c.shape + (n * n,)
    vals, inside = vals.reshape(shape), inside.reshape(shape)
    exists = inside.all(axis=-1)
    vals = np.ascontiguousarray(np.where(exists[..., None], vals, np.nan))
    return vals, exists


def moments(vals):
    """Zero-mean samples and population standard deviation over the 25 samples."""
    m = np.mean(vals, axis=-1, keepdims=True)
    dev = np.ascontiguousarray(vals - m)
    return dev, np.sqrt(np.mean(dev * dev, axis=-1))


def zncc(dev_a, dev_b):
    num = np.sum(dev_a * dev_b, axis=-1)
    den = np.sqrt(np.sum(dev_a * dev_a, axis=-1) * np.sum(dev_b * dev_b, axis=-1))
    with np.errstate(divide="ignore", invalid="ignore"):
        return num / den


# ------------------------------------------------------------------ the search locus (section 9)
def plane_normal(d0, d1, d2):
    b = BASELINE
    n0 = b[1] * d2 - b[2] * d1
    n1 = b[2] * d0 - b[0] * d2
    n2 = b[0] * d1 - b[1] * d0
    nn = np.sqrt(n0 * n0 + n1 * n1 + n2 * n2)
    with np.errstate(divide="ignore", invalid="ignore"):
        return n0 / nn, n1 / nn, n2 / nn


def search_line(cam_r: Cam, d0, d1, d2, th_l, ph_l) -> dict:
    """The raw right epipolar line of each left ray: l, q_inf (theta_R = theta_L) and the unit direction t of +theta_R."""
    n0, n1, n2 = plane_normal(d0, d1, d2)
    a = cam_r.A
    l0 = n0 * a[0, 0] + n1 * a[1, 0] + n2 * a[2, 0]
    l1 = n0 * a[0, 1] + n1 * a[1, 1] + n2 * a[2, 1]
    l2 = n0 * a[0, 2] + n1 * a[1, 2] + n2 * a[2, 2]
    qu, qv, h2 = project(cam_r, d0, d1, d2)
    e0, e1, e2 = -np.sin(th_l), np.cos(th_l) * np.sin(ph_l), -(np.cos(th_l) * np.cos(ph_l))
    m = cam_r.M
    g0 = m[0, 0] * e0 + m[0, 1] * e1 + m[0, 2] * e2
    g1 = m[1, 0] * e0 + m[1, 1] * e1 + m[1, 2] * e2
    g2 = m[2, 0] * e0 + m[2, 1] * e1 + m[2, 2] * e2
    h0, h1 = qu * h2, qv * h2
    with np.errstate(divide="ignore", invalid="ignore"):
        dqu = (g0 * h2 - h0 * g2) / (h2 * h2)
        dqv = (g1 * h2 - h1 * g2) / (h2 * h2)
        ln = np.hypot(l0, l1)
        tu, tv = l1 / ln, -l0 / ln
    sgn = np.sign(tu * dqu + tv * dqv)
    tu, tv = tu * sgn, tv * sgn
    ok = (h2 > SP.Z_EPS) & (sgn != 0) & np.isfinite(qu) & np.isfinite(qv) & np.isfinite(tu) & np.isfinite(tv)
    return {"l": np.stack([l0, l1, l2], -1), "q_inf": np.stack([qu, qv], -1), "t": np.stack([tu, tv], -1), "ok": ok}


def chord(q, t, w, h):
    """Superset bounds [k_lo, k_hi] of the integer samples whose centre q + k t can lie in the raster; k >= 1."""
    lo = np.full(q.shape[0], -np.inf)
    hi = np.full(q.shape[0], np.inf)
    for ax, lim in ((0, w - 1), (1, h - 1)):
        qa, ta = q[:, ax], t[:, ax]
        inr = (qa >= 0) & (qa <= lim)
        with np.errstate(divide="ignore", invalid="ignore"):
            s1, s2 = (0.0 - qa) / ta, (lim - qa) / ta
        a_lo = np.where(ta > 0, s1, np.where(ta < 0, s2, np.where(inr, -np.inf, np.inf)))
        a_hi = np.where(ta > 0, s2, np.where(ta < 0, s1, np.where(inr, np.inf, -np.inf)))
        lo, hi = np.maximum(lo, a_lo), np.minimum(hi, a_hi)
    with np.errstate(invalid="ignore"):
        k_lo = np.maximum(1.0, np.floor(lo))
        k_hi = np.ceil(hi)
    good = np.isfinite(k_lo) & np.isfinite(k_hi) & (k_hi >= k_lo)
    return np.where(good, k_lo, 1.0).astype(np.int64), np.where(good, k_hi, 0.0).astype(np.int64)


# ------------------------------------------------------------------ the decision on one score curve (sections 10-13)
def decide(S: np.ndarray, p: Params = FROZEN) -> dict:
    """Best candidate (tie rule), top-K distinct local peaks and the 3-point parabola, for score rows S (NaN = invalid).

    Column j is the integer sample k_first_chord + j (1-pixel spacing); adjacent columns are adjacent samples.
    """
    S = np.atleast_2d(np.asarray(S, np.float64))
    b, n = S.shape
    rows = np.arange(b)
    valid_s = ~np.isnan(S)
    has = valid_s.any(axis=1)
    smax = np.where(valid_s, S, -np.inf).max(axis=1)
    with np.errstate(invalid="ignore"):
        j_best = np.argmax(valid_s & (S >= (smax - p.tie_eps)[:, None]), axis=1)
    prev = np.full_like(S, np.nan)
    prev[:, 1:] = S[:, :-1]
    nxt = np.full_like(S, np.nan)
    nxt[:, :-1] = S[:, 1:]
    with np.errstate(invalid="ignore"):
        local = valid_s & (np.isnan(prev) | (S >= prev - p.tie_eps)) & (np.isnan(nxt) | (S >= nxt - p.tie_eps))
    rem = local.copy()
    jj = np.arange(n)[None, :]
    peak_j = np.full((b, p.top_k), -1, np.int64)
    for r in range(p.top_k):
        ok = rem.any(axis=1)
        m = np.where(rem, S, -np.inf).max(axis=1)
        with np.errstate(invalid="ignore"):
            j = np.argmax(rem & (S >= (m - p.tie_eps)[:, None]), axis=1)
        peak_j[:, r] = np.where(ok, j, -1)
        far = np.abs(jj - j[:, None]) * p.spacing >= p.separation
        rem &= np.where(ok[:, None], far, True)
    s0 = S[rows, j_best]
    sm = np.where(j_best >= 1, S[rows, np.maximum(j_best - 1, 0)], np.nan)
    sp_ = np.where(j_best + 1 < n, S[rows, np.minimum(j_best + 1, n - 1)], np.nan)
    dd = sm - 2.0 * s0 + sp_
    both = np.isfinite(sm) & np.isfinite(sp_)
    refined = has & both & (dd < 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.clip((sm - sp_) / (2.0 * dd), -p.bound, p.bound)
    return {"has": has, "j_best": j_best, "peak_j": peak_j, "s_minus": sm, "s_plus": sp_, "curvature": dd,
            "both": both, "refined": refined, "offset": np.where(refined, x, 0.0)}


# ------------------------------------------------------------------ one gaze
class Context:
    """Calibration-derived and image-derived state shared by every batch of one gaze."""

    def __init__(self, c: dict, g_l: np.ndarray, g_r: np.ndarray, p: Params = FROZEN) -> None:
        FG.validate_calibration(c)
        self.c, self.p = c, p
        self.cam_l, self.cam_r = make_cams(c)
        self.w, self.h = c["image_size_wh"]
        if not np.isclose(self.cam_l.f, self.cam_r.f, rtol=0, atol=1e-12):
            raise ValueError("the two eyes must share the focal length")
        self.delta = SP.delta(self.cam_l.f)
        self.b = float(c["ipd_m"])
        self.g_l, self.g_r = np.ascontiguousarray(g_l, np.float64), np.ascontiguousarray(g_r, np.float64)
        rows, cols = np.mgrid[:SP.CORE_SIZE, :SP.CORE_SIZE]
        self.row, self.col = rows.ravel().astype(np.int32), cols.ravel().astype(np.int32)
        self.uv_l = np.stack([self.col + SP.CORE_ORIGIN, self.row + SP.CORE_ORIGIN], -1).astype(np.float64)
        d = FG.rays_h(c["eyes"][0], self.uv_l)        # the accepted left rays (identical to AB1b)
        self.d_l = d
        self.th_l, self.ph_l = theta_phi(d[:, 0], d[:, 1], d[:, 2])
        self.lp_vals, self.lp_exists = patch(self.cam_l, self.g_l, self.th_l, self.ph_l, self.delta, p)
        self.lp_dev, self.lp_std = moments(self.lp_vals)
        self.line = search_line(self.cam_r, d[:, 0], d[:, 1], d[:, 2], self.th_l, self.ph_l)
        self.k_lo, self.k_hi = chord(self.line["q_inf"], self.line["t"], self.w, self.h)
        self.k_hi = np.where(self.line["ok"], self.k_hi, 0)

    def candidates(self, idx: np.ndarray) -> dict:
        """Every integer sample of the chord for the left pixels ``idx``: geometry, admissibility, scores."""
        p = self.p
        k_lo, k_hi = self.k_lo[idx], self.k_hi[idx]
        n = int(max(1, (k_hi - k_lo + 1).max(initial=1)))
        kk = k_lo[:, None] + np.arange(n)[None, :]
        in_range = kk <= k_hi[:, None]
        s = kk.astype(np.float64) * p.spacing
        q, t = self.line["q_inf"][idx], self.line["t"][idx]
        qu = q[:, 0:1] + s * t[:, 0:1]
        qv = q[:, 1:2] + s * t[:, 1:2]
        with np.errstate(invalid="ignore"):
            centre = in_range & (qu >= 0) & (qu <= self.w - 1) & (qv >= 0) & (qv <= self.h - 1)
        d0, d1, d2 = rays(self.cam_r, qu, qv)
        th, ph = theta_phi(d0, d1, d2)
        th_l, ph_l = self.th_l[idx][:, None], self.ph_l[idx][:, None]
        with np.errstate(divide="ignore", invalid="ignore"):
            den = np.cos(th_l) / np.sin(th_l) - np.cos(th) / np.sin(th)
            rho = self.b / den
            adm = (centre & np.isfinite(d0) & np.isfinite(d1) & np.isfinite(d2) & (np.cos(ph - ph_l) > 0)
                   & (th > th_l) & (den >= SP.DEN_EPS) & np.isfinite(rho) & (rho > 0))
        vals, exists = patch(self.cam_r, self.g_r, np.where(adm, th, np.pi / 2), np.broadcast_to(ph_l, th.shape),
                             self.delta, p)
        adm &= exists
        dev, std = moments(vals)
        tex = adm & (std >= p.min_std)
        score = np.where(tex, zncc(self.lp_dev[idx][:, None, :], dev), np.nan)
        return {"k": kk, "s": s, "in_range": in_range, "qu": qu, "qv": qv, "theta": th, "phi": ph,
                "admissible": adm, "textured": tex, "std": std, "score": score, "dev": dev}

    def batch(self, idx: np.ndarray) -> dict:
        p = self.p
        cd = self.candidates(idx)
        S, kk, adm, tex = cd["score"], cd["k"], cd["admissible"], cd["textured"]
        b, n = S.shape
        rows = np.arange(b)
        dec = decide(S, p)
        has, j_best, peak_j, sm, sp_, dd, both, refined, off = (dec[k] for k in (
            "has", "j_best", "peak_j", "s_minus", "s_plus", "curvature", "both", "refined", "offset"))
        s0 = S[rows, j_best]
        k_best = kk[rows, j_best]
        s_disc = k_best.astype(np.float64) * p.spacing
        s_est = s_disc + off * p.spacing
        q, t = self.line["q_inf"][idx], self.line["t"][idx]
        uv_disc = q + s_disc[:, None] * t
        uv_est = q + s_est[:, None] * t
        th_disc = theta_phi(*rays(self.cam_r, uv_disc[:, 0], uv_disc[:, 1]))[0]
        th_est = theta_phi(*rays(self.cam_r, uv_est[:, 0], uv_est[:, 1]))[0]
        pk = np.maximum(peak_j, 0)
        pk_ok = peak_j >= 0
        peak_s = np.where(pk_ok, kk[rows[:, None], pk].astype(np.float64) * p.spacing, np.nan)
        peak_uv = np.where(pk_ok[..., None], q[:, None, :] + peak_s[..., None] * t[:, None, :], np.nan)
        peak_th = np.where(pk_ok, cd["theta"][rows[:, None], pk], np.nan)
        peak_z = np.where(pk_ok, S[rows[:, None], pk], np.nan)
        cand_n = adm.sum(axis=1)
        k_first = np.where(adm.any(axis=1), kk[rows, np.argmax(adm, axis=1)], -1)
        k_last = np.where(adm.any(axis=1), kk[rows, n - 1 - np.argmax(adm[:, ::-1], axis=1)], -1)
        lex, ltex = self.lp_exists[idx], self.lp_exists[idx] & (self.lp_std[idx] >= p.min_std)
        valid = ltex & has
        reason = np.where(~lex, 4, np.where(~ltex, 1, np.where(cand_n == 0, 2, np.where(~has, 3, 0)))).astype(np.int8)
        nan = np.nan
        second = np.where(valid & pk_ok[:, 1], peak_z[:, 1], nan)
        v1 = valid[:, None]
        return {
            "valid_left_patch": lex, "valid_left_texture": ltex, "valid_match": valid, "reason": reason,
            "candidate_count": cand_n.astype(np.int32), "textured_candidate_count": tex.sum(axis=1).astype(np.int32),
            "k_first": k_first.astype(np.int32), "k_last": k_last.astype(np.int32),
            "k_best": np.where(valid, k_best, -1).astype(np.int32),
            "uv_R_discrete": np.where(v1, uv_disc, nan), "s_est": np.where(valid, s_est, nan),
            "uv_R_est": np.where(v1, uv_est, nan), "theta_R_discrete": np.where(valid, th_disc, nan),
            "theta_R_est": np.where(valid, th_est, nan), "best_zncc": np.where(valid, s0, nan),
            "second_peak_zncc": second, "peak_margin": np.where(valid, s0 - second, nan),
            "peak_curvature": np.where(valid & both, dd, nan), "refined": valid & refined,
            "refinement_offset_samples": np.where(valid, off, nan),
            "peak_count": np.where(valid, pk_ok.sum(axis=1), 0).astype(np.int32),
            "peak_s": np.where(v1, peak_s, nan), "peak_uv_R": np.where(v1[..., None], peak_uv, nan),
            "peak_theta_R": np.where(v1, peak_th, nan), "peak_zncc": np.where(v1, peak_z, nan),
        }


RECORD_FIXED = ("left_core_row", "left_core_col", "uv_L", "theta_L", "phi_L", "left_patch_std_u8", "q_inf", "line_dir",
                "line_l")


def match(ctx: Context, idx: np.ndarray | None = None, threads: int = SP.THREADS, batch: int = SP.BATCH) -> dict:
    """The full matcher record for the left core indices ``idx`` (default: all 65,536, in core order)."""
    idx = np.arange(ctx.row.size) if idx is None else np.asarray(idx, np.int64)
    parts = [idx[i:i + batch] for i in range(0, idx.size, batch)]
    if threads > 1:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            res = list(ex.map(ctx.batch, parts))
    else:
        res = [ctx.batch(b) for b in parts]
    rec = {k: np.concatenate([r[k] for r in res]) for k in res[0]}
    rec.update({"left_core_row": ctx.row[idx], "left_core_col": ctx.col[idx], "uv_L": ctx.uv_l[idx],
                "theta_L": ctx.th_l[idx], "phi_L": ctx.ph_l[idx], "left_patch_std_u8": ctx.lp_std[idx],
                "q_inf": ctx.line["q_inf"][idx], "line_dir": ctx.line["t"][idx], "line_l": ctx.line["l"][idx]})
    return rec


def product(rec: dict) -> dict:
    """The truth-stripped natural correspondence product (accepted AB1b schema), valid matches only, core order."""
    v = np.asarray(rec["valid_match"], bool)
    prod = {"left_core_row": np.asarray(rec["left_core_row"], np.int32)[v],
            "left_core_col": np.asarray(rec["left_core_col"], np.int32)[v],
            "uv_L": np.ascontiguousarray(np.asarray(rec["uv_L"], np.float64)[v]),
            "uv_R": np.ascontiguousarray(np.asarray(rec["uv_R_est"], np.float64)[v])}
    BG.validate_product(prod)
    return prod


# ------------------------------------------------------------------ post-freeze helpers (same frozen score)
def line_point(ctx: Context, idx, s):
    q, t = ctx.line["q_inf"][idx], ctx.line["t"][idx]
    return q + np.asarray(s, np.float64)[..., None] * t


def line_theta(ctx: Context, idx, s):
    uv = line_point(ctx, idx, s)
    return theta_phi(*rays(ctx.cam_r, uv[..., 0], uv[..., 1]))[0]


def score_at(ctx: Context, idx, theta_c):
    """The frozen ZNCC of the left patch of ``idx`` against the right patch centred at (theta_c, phi_L)."""
    vals, exists = patch(ctx.cam_r, ctx.g_r, theta_c, ctx.ph_l[idx], ctx.delta, ctx.p)
    dev, std = moments(vals)
    tex = exists & (std >= ctx.p.min_std)
    return np.where(tex, zncc(ctx.lp_dev[idx], dev), np.nan), exists, std


def landscape(ctx: Context, i: int) -> dict:
    """The full ZNCC curve of one left pixel over its chord (figures)."""
    cd = ctx.candidates(np.array([i]))
    keep = cd["in_range"][0]
    return {k: cd[k][0][keep] for k in ("k", "s", "qu", "qv", "theta", "admissible", "textured", "score", "std")}
