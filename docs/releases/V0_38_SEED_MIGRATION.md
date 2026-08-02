# v0.38 — Migration: the weak diagnostic's seed is now required

**Breaking.** `inspect_pysindy_weak_pde_library` requires an explicit integer
`seed`. There is no compatibility default.

## Exact before / after

### Omitted seed — the common case

```python
# Before (v0.31b2 – v0.37.1): allowed, emitted a FutureWarning, nondeterministic
report = inspect_pysindy_weak_pde_library(
    field,
    task_name="my_task",
)

# After (v0.38): TypeError. Pass an integer.
report = inspect_pysindy_weak_pde_library(
    field,
    task_name="my_task",
    seed=13,
)
```

### Explicit `None` — the nondeterminism opt-in

```python
# Before: silent, and recorded nondeterministic_requested=True
report = inspect_pysindy_weak_pde_library(
    field,
    task_name="my_task",
    seed=None,
)

# After: ScopeValidationError. There is no nondeterministic mode.
report = inspect_pysindy_weak_pde_library(
    field,
    task_name="my_task",
    seed=13,
)
```

### Already passing a seed

No change. This was already the recommended form and is now the only one.

```python
report = inspect_pysindy_weak_pde_library(
    field,
    task_name="my_task",
    seed=13,
)
```

### Forwarding through `**kwargs`

```python
# Supply a default that a caller can still override.
def run(**kwargs):
    return inspect_pysindy_weak_pde_library(
        field, task_name="my_task", **{"seed": 13, **kwargs}
    )
```

## What to choose for `seed`

Any `int`. It is recorded in
`report["provenance"]["seed_provenance"]["seed"]`, so the value that produced a
number is always recoverable from the payload.

`bool` is refused despite being an `int` subclass — `seed=True` would silently
seed with `1`.

## Why

`pysindy.WeakPDELibrary` draws its domain centers from the global NumPy RNG and
exposes no seed of its own. Without an explicit one, two runs on identical input
produce different conditioning numbers, and a diagnostic whose payload changes
between identical runs cannot be cited.

The transition was announced at **v0.36e** (naming v0.37), deferred at **v0.37**
because an unscoped breaking change during a release close is worse than a
deferred one, re-dated to v0.38, and kept here. Deferring it a second time would
have weakened the forward-promise mechanism at precisely the moment that
mechanism first worked.

## Payload shape

**Unchanged.** The frozen 27/28-key conditional schema is preserved, and
`seed_provenance` keeps all seven keys.

Two of them are now constant:

| key | v0.38 value |
|---|---|
| `seed_was_omitted` | always `False` |
| `nondeterministic_requested` | always `False` |

They are retained rather than dropped because the block sits inside a frozen
schema, and removing keys would change the shape for every existing consumer to
say something the `seed` value already says.

## What this does not change

- No other function gained or lost a required argument.
- No `summary_type` changed.
- The 22-key `discovery_task_result` schema is untouched.
- The diagnostic still makes no noise-robustness claim and is still not WSINDy.
