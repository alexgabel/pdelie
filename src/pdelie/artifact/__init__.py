"""v0.36: artifact identity and lineage primitives.

**Experimental.** This package lands in the v0.36 day-zero polish so that every
later consumer — ``ArtifactRef``, stage bundles, lineage records — shares one
hash function from the start rather than converging on one afterwards.

Submodule-only: nothing here is exported from the root ``pdelie`` namespace.
"""

from __future__ import annotations

from pdelie.artifact.semantic_hash import semantic_hash

__all__ = ["semantic_hash"]
