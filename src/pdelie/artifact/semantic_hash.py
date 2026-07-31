"""v0.36 day-zero: the single canonical-JSON hash used across PDELie.

Every ``ArtifactRef`` and every lineage hash routes through :func:`semantic_hash`.
There is deliberately **no** alternative canonical-JSON implementation anywhere
in the codebase: two hash functions that agree today and diverge after a NumPy
or Python release would silently split a lineage graph in half, and nothing
would report it.

The serialization is pinned in four ways, each load-bearing:

``sort_keys=True``
    Dict iteration order must not affect the digest. Without this, a payload
    rebuilt in a different insertion order hashes differently while being the
    same artifact.
``separators=(",", ":")``
    Removes the whitespace ``json.dumps`` inserts by default. Cosmetic
    formatting must not change identity.
``ensure_ascii=True``
    Non-ASCII characters are escaped rather than emitted raw, so the digest
    does not depend on the filesystem or terminal encoding of whoever produced
    the payload.
``allow_nan=False``
    ``NaN``/``Infinity`` are not JSON, and Python emits them as bare literals
    that no strict parser accepts. Raising here is consistent with the
    repo-wide strict-JSON rule: a non-finite value in a payload is a defect at
    its source, not something a hash should paper over.

The digest is SHA-256 over the UTF-8 encoding of that canonical string.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

__all__ = ["semantic_hash"]


def semantic_hash(payload: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 digest of a strict-JSON payload.

    Raises ``ValueError`` (from :func:`json.dumps`) if the payload contains a
    non-finite float, and ``TypeError`` if it contains a value JSON cannot
    represent. Both are deliberate: an unhashable payload is a defect to fix at
    the producer, not to coerce here.
    """
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
