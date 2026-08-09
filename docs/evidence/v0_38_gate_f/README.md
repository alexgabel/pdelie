# Gate F closure evidence — run `31328966332`

The three uploaded artifacts, verbatim, plus the pairwise comparison. GitHub
expires action artifacts; the record that closed the gate should outlive them.

Reproduce the verdict from these files alone:

```sh
python scripts/audit_replay_population.py docs/evidence/v0_38_gate_f/
python scripts/compare_replay.py docs/evidence/v0_38_gate_f/
```

The audit imports neither the generator nor the comparator. See
[Appendix D](../../design/v0_38_platform_replay.md) for the criteria, and §D6 for
the one post-run correction to analysis code.

Appendix C's failing run is **not** archived here — it is described in full in
Appendix C, and keeping only the passing artifacts would make this directory a
selection-effect document. This README says so explicitly for that reason.
