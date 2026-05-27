# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Unit tests for `euxis_publisher.tools.overlay`.

Covers the four documented merge rules and the `resolve()` helper:

- dicts merge recursively;
- lists in the overlay replace lists in the base;
- scalars in the overlay replace scalars in the base;
- `None` in the overlay deletes the key from the result.
"""

from __future__ import annotations

import copy

import pytest

from euxis_publisher.tools.overlay import merge, resolve

# ── merge: dicts ────────────────────────────────────────────────────────


def test_merge_dicts_recursive():
    base = {"a": 1, "b": {"x": 1, "y": 2}}
    overlay = {"b": {"y": 20, "z": 30}, "c": 3}
    assert merge(base, overlay) == {
        "a": 1,
        "b": {"x": 1, "y": 20, "z": 30},
        "c": 3,
    }


def test_merge_returns_new_object_does_not_mutate_inputs():
    base = {"a": {"x": 1}}
    overlay = {"a": {"y": 2}}
    base_snapshot = copy.deepcopy(base)
    overlay_snapshot = copy.deepcopy(overlay)

    merge(base, overlay)

    assert base == base_snapshot
    assert overlay == overlay_snapshot


def test_merge_overlay_only_keys_added():
    assert merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_merge_empty_overlay_returns_base_copy():
    base = {"a": [1, 2], "b": {"x": 1}}
    result = merge(base, {})
    assert result == base
    assert result is not base
    assert result["a"] is not base["a"]
    assert result["b"] is not base["b"]


# ── merge: lists ────────────────────────────────────────────────────────


def test_merge_lists_overlay_replaces_base():
    """Lists are replaced wholesale — reordering matters for a CV."""
    assert merge({"items": [1, 2, 3]}, {"items": [4, 5]}) == {"items": [4, 5]}


def test_merge_list_in_overlay_replaces_dict_in_base():
    assert merge({"a": {"x": 1}}, {"a": [1, 2]}) == {"a": [1, 2]}


# ── merge: scalars ──────────────────────────────────────────────────────


def test_merge_scalar_overlay_replaces_scalar_base():
    assert merge({"a": "old"}, {"a": "new"}) == {"a": "new"}


def test_merge_scalar_overlay_replaces_dict_base():
    assert merge({"a": {"x": 1}}, {"a": "scalar"}) == {"a": "scalar"}


# ── merge: deletion via None ────────────────────────────────────────────


def test_merge_none_in_overlay_deletes_key():
    assert merge({"a": 1, "b": 2}, {"a": None}) == {"b": 2}


def test_merge_none_in_overlay_deletes_nested_key():
    assert merge({"a": {"x": 1, "y": 2}}, {"a": {"x": None}}) == {"a": {"y": 2}}


def test_merge_none_in_overlay_does_not_add_missing_key():
    # `None` should be treated as deletion, not as "add the value None".
    assert merge({"a": 1}, {"b": None}) == {"a": 1}


# ── merge: edge types ───────────────────────────────────────────────────


def test_merge_top_level_scalar_overlay_wins():
    assert merge(1, 2) == 2


def test_merge_top_level_list_overlay_wins():
    assert merge([1, 2], [3]) == [3]


def test_merge_dict_into_list_overlay_wins():
    # Type mismatch at the same key: overlay wins, no smart fallback.
    assert merge([1, 2], {"a": 1}) == {"a": 1}


# ── resolve ─────────────────────────────────────────────────────────────


def test_resolve_no_inherits_returns_overlay_unchanged():
    overlay = {"name": "Alice", "title": "CTO"}
    assert resolve(overlay, base_loader=lambda _id: {}) is overlay


def test_resolve_with_inherits_merges_against_loaded_base():
    bases = {
        "cv-base": {"name": "Alice", "title": "Engineer", "skills": ["py"]},
    }
    overlay = {"inherits": "cv-base", "title": "Director", "skills": ["py", "go"]}

    result = resolve(overlay, base_loader=lambda i: bases[i])

    assert result == {
        "name": "Alice",
        "title": "Director",
        "skills": ["py", "go"],
    }
    # The `inherits` key is stripped from the body before merging.
    assert "inherits" not in result


def test_resolve_propagates_loader_keyerror():
    with pytest.raises(KeyError):
        resolve({"inherits": "missing"}, base_loader=lambda i: {}[i])


def test_resolve_with_none_overlay_deletes_inherited_key():
    bases = {"cv-base": {"name": "Alice", "phone": "+44 0000"}}
    overlay = {"inherits": "cv-base", "phone": None}

    result = resolve(overlay, base_loader=lambda i: bases[i])

    assert result == {"name": "Alice"}
