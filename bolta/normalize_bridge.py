"""Small helpers bridging DB rows and normalized alias lookup."""

from __future__ import annotations

from noiselab.normalize import normalize_text


def alias_set(row) -> set[str]:
    """All normalized names/aliases for a product or customer row."""
    keys = row.keys()
    names = [row["name_en"] if "name_en" in keys else row["name"]]
    if "name_hi" in keys and row["name_hi"]:
        names.append(row["name_hi"])
    names += [a.strip() for a in (row["aliases"] or "").split(",")
              if a.strip()]
    return {normalize_text(n) for n in names if n}
