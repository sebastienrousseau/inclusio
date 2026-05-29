# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Deep-merge data + overlay for CV / paper / patent variants.

Content repositories that author with Inclusio (e.g. the
companion `inclusio-private`) tend to grow CV / paper / patent
variants quickly: an author may keep a base CV and tailor it for
JP Morgan, Citi, or a specific job description. Each variant
historically ships as a fully-cloned YAML data file — sustainable
at four variants, painful at ten.

This module supports the "shared template, overlay data" pattern.
A tailored variant declares only the fields that differ from a base
data file (plus `inherits: <base-id>`), and `merge` produces the
effective dataset that the template renders against.

The merge rules are intentionally simple and explicit:

- dicts merge key-by-key (recursive);
- lists in the overlay replace lists in the base — no element-wise
  union, since reordering matters for a CV;
- scalars in the overlay replace scalars in the base;
- `None` in the overlay deletes the key from the result.

This module has no runtime dependencies beyond stdlib. Content repos
import it via `from inclusio.tools.overlay import merge,
resolve` after `pip install inclusio`.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

_SENTINEL = object()


def merge(base: Any, overlay: Any) -> Any:
    """Return base deep-merged with overlay.

    Inputs are not mutated. See module docstring for rules.

    Args:
        base: The base data structure (dict, list, or scalar).
        overlay: The overlay to apply on top of `base`.

    Returns:
        A new structure: `overlay` wins for lists and scalars; dicts
        merge recursively; `None` in `overlay` deletes the key.
    """
    if isinstance(base, dict) and isinstance(overlay, dict):
        out: dict[str, Any] = {}
        for key in base:
            if key in overlay:
                if overlay[key] is None:
                    continue  # deletion
                out[key] = merge(base[key], overlay[key])
            else:
                out[key] = deepcopy(base[key])
        for key, value in overlay.items():
            if key not in base and value is not None:
                out[key] = deepcopy(value)
        return out
    # Lists and scalars: overlay wins (when present). The `_SENTINEL`
    # branch is reserved for a future "no overlay key" call site; not
    # reachable from the current `merge()` entry point and intentionally
    # left as a defensive code path.
    if overlay is _SENTINEL:  # pragma: no cover - reserved for future API
        return deepcopy(base)
    return deepcopy(overlay)


def resolve(
    overlay: dict[str, Any],
    base_loader: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    """Resolve an overlay dict against a base referenced by `inherits:`.

    `base_loader` is a callable taking a base id (the value of
    `inherits:`) and returning the loaded base dict. Kept
    dependency-free so callers wire it to whatever loader fits
    (file path, manifest lookup, fixture).

    Args:
        overlay: The overlay dict, which may carry an `inherits:` key.
        base_loader: Callable that returns the base dict for a given id.

    Returns:
        If `overlay` has no `inherits:`, returns `overlay` unchanged.
        Otherwise returns `merge(base_loader(overlay["inherits"]),
        overlay - inherits)`.
    """
    if "inherits" not in overlay:
        return overlay
    base_id = overlay["inherits"]
    base = base_loader(base_id)
    body = {k: v for k, v in overlay.items() if k != "inherits"}
    return merge(base, body)
