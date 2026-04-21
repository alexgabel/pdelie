# AGENTS.md

## Repo role
This repo is a reusable library only. No paper-specific hacks.

## Source of truth
Read these before coding:
- docs/specs/SPEC.md
- docs/specs/CONTRACTS_AND_DEFAULTS.md
- docs/specs/ARCHITECTURE.md
- docs/specs/API_STABILITY.md

## Stable scope
V0.x stable scope only:
- uniform rectilinear grids
- synthetic PDE data
- Lie point symmetries
- polynomial generators

## Do not implement unless explicitly asked
- neural generators
- weak-form advanced methods
- operator symmetry
- broad dataset adapters
- paper-specific experiment logic

## Workflow
For nontrivial tasks:
1. plan first
2. implement one milestone only
3. add/update tests
4. run narrowest relevant tests
5. report ambiguities instead of guessing

## Definition of done
A change is done only if:
- contracts are respected
- tests pass
- no stable/experimental boundaries are crossed
- docs are updated if interfaces changed
