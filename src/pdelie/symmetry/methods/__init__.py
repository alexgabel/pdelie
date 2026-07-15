"""v0.30.1 symmetry-methods package.

Deliberately empty init: adapter modules are imported LAZILY by
:mod:`pdelie.symmetry.registry` on the first
:func:`get_symmetry_method` / :func:`run_symmetry_method` call.
Importing this package must NOT import PyTorch, LieGAN, LaLiGAN, or any
other optional heavy dependency — the registry's list-only path
(:func:`pdelie.symmetry.list_symmetry_methods`) needs to work in a core
install with only ``numpy``.
"""

from __future__ import annotations

# Intentionally empty. Do not import adapter modules here.
