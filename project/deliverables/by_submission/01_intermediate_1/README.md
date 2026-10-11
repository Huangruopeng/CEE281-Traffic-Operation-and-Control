# Intermediate 1 - proposal, interfaces, minimum simulation

**Due:** October 14 (after class).

## Submit

| Guide item | File |
|---|---|
| 1. Problem and scope | `design_record_int1.md`, Section 1 |
| 2. Model and source-to-design table | `design_record_int1.md`, Section 2 |
| 3. Interface draft with examples | `design_record_int1.md`, Section 3 |
| 4. Minimum runnable simulation | `bash run_int1.sh` (project root); `run_int1.py`; `configs/scenarios.json` |
| 5. Pre-run prediction and first evidence | `experiment_record.md`; figures in `outputs/int1/` |
| 6. Team evidence and individual check | `contribution_record_int1.md` (each member writes the answers) |
| 7. Reproducibility | project `README.md`, section "Intermediate 1" |
| AI use and verification | `design_record_int1.md`, last section |

## Demonstration

```bash
bash run_int1.sh
python run_live.py
```

Then open <http://127.0.0.1:8765> ("Intermediate 1" scenario). Point to `idm_acceleration()` in
`src/cavsim/core.py` for the model, and to `_time_gap_offset()` for the bottleneck.

## Before submitting

- [ ] Both members agree on the role split and write their own answers in `contribution_record_int1.md`.
- [ ] Replace provisional names/UIDs.
- [ ] Each member can trace their vehicle and explain the partner's test.
