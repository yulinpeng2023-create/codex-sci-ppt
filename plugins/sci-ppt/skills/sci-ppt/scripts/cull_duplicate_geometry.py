#!/usr/bin/env python3
"""Remove exact duplicate drawing paths from a Sci-PPT geometry cache.

This keeps the same important invariant used by the MIT-licensed Cell_ppt
pipeline: remove exact duplicate new drawing paths only, while retaining every
other path and all text. See THIRD_PARTY_NOTICES.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


def signature(atom):
    payload = {
        "kind": atom.get("kind"),
        "subpaths": atom.get("subpaths"),
        "paintParts": atom.get("paintParts"),
        "text": atom.get("text"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_batches(atoms, size=40):
    return [
        {
            "index": start // size,
            "kind": "normal",
            "group_name": f"SCI_PPT_CACHE_{start // size:04d}",
            "atom_indices": list(range(start, min(start + size, len(atoms)))),
            "atomic_count": min(size, len(atoms) - start),
            "complexity": sum(atom.get("complexity", 1) for atom in atoms[start:start + size]),
        }
        for start in range(0, len(atoms), size)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()

    cache = json.loads(args.cache.read_text(encoding="utf-8"))
    expanded = []
    for atom in cache["atoms"]:
        subpaths = atom.get("subpaths") or []
        if atom.get("kind") == "text" or len(subpaths) <= 1:
            expanded.append(atom)
            continue
        for subpath_index, subpath in enumerate(subpaths):
            unit = copy.deepcopy(atom)
            unit["subpaths"] = [subpath]
            unit["sourceSubpathIndex"] = subpath_index
            unit["objectName"] = f"{unit['objectName']}_SUB_{subpath_index:03d}"
            unit["complexity"] = len(subpath.get("points", []))
            expanded.append(unit)

    seen = set()
    keep = [True] * len(expanded)
    for index in range(len(expanded) - 1, -1, -1):
        atom = expanded[index]
        if atom.get("kind") == "text":
            continue
        digest = signature(atom)
        if digest in seen:
            keep[index] = False
        else:
            seen.add(digest)

    retained = [atom for index, atom in enumerate(expanded) if keep[index]]
    if not retained:
        raise ValueError("duplicate filtering removed every atom")

    cache["source_total_atoms"] = len(cache["atoms"])
    cache["source_total_drawing_paths"] = len(expanded)
    cache["culled_atom_count"] = len(expanded) - len(retained)
    cache["atoms"] = retained
    cache["total_atoms"] = len(retained)
    cache["batches"] = build_batches(retained)
    args.cache.write_text(
        json.dumps(cache, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "kept_atoms": len(retained),
                "culled_atoms": len(expanded) - len(retained),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
