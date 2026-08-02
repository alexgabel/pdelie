# Formatting Policy

**Status:** binding. Decided after a `ruff format` run touched 206 files during
v0.38 day-zero and had to be unwound.

## The rule, through v0.38

**This repository is not formatter-governed.** CI gates on `ruff check` (lint)
and not on `ruff format` (layout).

**Do not run `ruff format` on a feature branch.** The repository does not
currently satisfy it, so running it produces a mechanical diff across most of
the tree, mixed into whatever the branch was actually for. That diff is
unreviewable: a reviewer cannot tell a deliberate change from a re-wrap.

What happened, concretely: a single `ruff format src/ tests/` reformatted 206
files. Reverting it required restoring 203 unrelated files and then hand-undoing
five formatting-only hunks that had mixed into the three files the branch
genuinely changed. The branch's real diff was 46 insertions.

Use `ruff check --fix`, which only makes changes lint requires.

## The rule, after v0.38 ships

Three steps, in order:

1. **One mechanical formatting-only PR.** No behaviour change, no logic change,
   nothing else in it. Its diff is expected to be large and its review is a
   check that it is *only* formatting.
2. **Add `ruff format --check` to CI**, permanently.
3. From then on, `ruff format` is expected on every branch and a branch that
   does not satisfy it fails.

## Why not adopt it now

Because the mechanical PR and the v0.38 feature work would land in the same
window, and every v0.38 review would be reading a diff where formatting and
substance are interleaved. v0.38 carries two declaration/execution defects and a
breaking API change; those reviews need to be legible.

## Why not leave it undecided

The state this replaces — formatter available, unenforced, and satisfied by
nobody — is the worst of the three. It invites exactly the incident above,
because `ruff format` looks like a safe local tidy and is not.

Deciding *that* it will be adopted, and *when*, is what makes the interim rule
enforceable rather than a request.

## Scope

This governs layout only. It says nothing about `ruff check`, which is a CI gate
now and stays one, or about the mypy fingerprint ratchet, which is separate.
