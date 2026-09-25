#!/usr/bin/env python3
"""Generate a tiny representation-only Phase-1 demo with no controller execution."""

from __future__ import annotations

from pathlib import Path
import argparse
import html
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.scene.synthetic import build_synthetic_occlusion_case


def svg_text(g) -> str:
    # The drawing is intentionally schematic.  It visualizes the key representational
    # fact: one object hypothesis may own disconnected visible regions.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="560" viewBox="0 0 1280 560">
<rect width="1280" height="560" fill="white"/>
<text x="40" y="45" font-family="sans-serif" font-size="26">Partition-Graph Phase 1 — representation kernel</text>
<text x="40" y="82" font-family="sans-serif" font-size="17">Scene partition and observation overlay are distinct; A-left and A-right share object hypothesis A.</text>
<rect x="60" y="140" width="210" height="120" rx="14" fill="#e8eef8" stroke="#333" stroke-width="2"/>
<text x="120" y="200" font-family="sans-serif" font-size="24">A-left</text>
<rect x="330" y="120" width="180" height="160" rx="14" fill="#f6e6df" stroke="#333" stroke-width="2"/>
<text x="405" y="205" font-family="sans-serif" font-size="24">B</text>
<rect x="570" y="140" width="210" height="120" rx="14" fill="#e8eef8" stroke="#333" stroke-width="2"/>
<text x="625" y="200" font-family="sans-serif" font-size="24">A-right</text>
<rect x="45" y="110" width="750" height="190" rx="20" fill="none" stroke="#777" stroke-dasharray="8,8"/>
<text x="60" y="325" font-family="sans-serif" font-size="18">partition faces on sphere (schematic)</text>
<path d="M270,200 C295,200 305,200 330,200" stroke="#222" stroke-width="4" fill="none"/>
<path d="M510,200 C535,200 545,200 570,200" stroke="#222" stroke-width="4" fill="none"/>
<text x="280" y="185" font-family="sans-serif" font-size="14">occlusion</text>
<text x="515" y="185" font-family="sans-serif" font-size="14">occlusion</text>
<path d="M165,365 C165,410 680,410 680,365" stroke="#275ea8" stroke-width="4" fill="none" stroke-dasharray="10,6"/>
<text x="333" y="445" font-family="sans-serif" font-size="20" fill="#275ea8">one object hypothesis A groups disconnected regions</text>
<rect x="835" y="120" width="390" height="210" rx="16" fill="#fafafa" stroke="#555"/>
<text x="985" y="155" font-family="sans-serif" font-size="20">dual graph</text>
<circle cx="900" cy="215" r="28" fill="#e8eef8" stroke="#333"/>
<text x="891" y="223" font-family="sans-serif" font-size="18">A₁</text>
<circle cx="990" cy="215" r="28" fill="#f6e6df" stroke="#333"/>
<text x="984" y="223" font-family="sans-serif" font-size="18">B</text>
<circle cx="1080" cy="215" r="28" fill="#e8eef8" stroke="#333"/>
<text x="1071" y="223" font-family="sans-serif" font-size="18">A₂</text>
<line x1="928" y1="215" x2="962" y2="215" stroke="#333" stroke-width="3"/>
<line x1="1018" y1="215" x2="1052" y2="215" stroke="#333" stroke-width="3"/>

<circle cx="990" cy="285" r="28" fill="#f2f2f2" stroke="#333"/>
<text x="972" y="292" font-family="sans-serif" font-size="16">base</text>
<line x1="915" y1="238" x2="970" y2="270" stroke="#777" stroke-width="2"/>
<line x1="1065" y1="238" x2="1010" y2="270" stroke="#777" stroke-width="2"/>
<text x="835" y="345" font-family="sans-serif" font-size="15">dual nodes are partition regions; object grouping is separate.</text>

<rect x="835" y="385" width="390" height="100" rx="12" fill="none" stroke="#777" stroke-dasharray="8,6"/>
<text x="875" y="425" font-family="sans-serif" font-size="17">observation footprint</text>
<text x="875" y="453" font-family="sans-serif" font-size="15">overlay, not a scene region</text>
<text x="40" y="535" font-family="monospace" font-size="15">summary: {html.escape(json.dumps(g.summary(), sort_keys=True))}</text>
</svg>'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", nargs="?", default="previews/partition-graph-1-demo")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    g = build_synthetic_occlusion_case()
    g.save(out / "scene-model")
    (out / "partition-graph.svg").write_text(svg_text(g), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(g.summary(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "Demo.md").write_text(
        "# Partition-Graph Phase 1 demo\n\n"
        "This is a representation-only synthetic fixture. It does **not** run Blender, "
        "the stereo matcher, fusion, segmentation, object discovery, or the controller.\n\n"
        "The fixture demonstrates the architectural distinction between a scene partition and "
        "the observation overlay, and demonstrates that one object hypothesis may own multiple "
        "disconnected visible partition regions across an occluder.\n\n"
        "Regenerate with:\n\n```bash\n"
        "./.venv/bin/python tools/partition_graph1_demo.py previews/partition-graph-1-demo\n"
        "```\n",
        encoding="utf-8",
    )
    print(f"[partition-graph1-demo] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
