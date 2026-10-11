# AI-use and verification disclosure

Generative AI assistance was used to help organize the project, draft original Python code and documentation, locate candidate literature, and prepare the report/presentation. No AI-generated empirical data were used. All quantitative results in the submission were produced by the included simulator and saved to CSV.

Verification performed by the student/project owner:

- Source titles, authors, DOI/official URLs, equations, and units were cross-checked against the original paper or authoritative technical page listed in `references.md`.
- The IDM implementation was checked against free-motion and analytical-equilibrium cases.
- Vehicle conservation includes exited, in-system, queued, residual, and overflow vehicles.
- Detector counts were independently reconstructed from exact crossing events for 10 labeled intervals; every error is zero.
- Forecast methods share the same horizon and held-out evaluation intervals; missing measurements remain explicitly missing.
- Controller inputs were audited in the decision trace to confirm that future trajectories and simulator truth are excluded.
- ACC/CACC comparisons use the same initialization, demand, disturbance, run length, and ramp logic.
- Time-step sensitivity was run at 0.05, 0.10, and 0.20 s.
- Every final scenario was checked against the configured 2.0-m physical net-gap floor; all pass and all record zero final numerical collision-guard activations.
- Final PDF pages and every presentation slide were rendered and visually inspected for clipping, overlap, units, labels, and citation readability.

Remaining responsibility: the submitter should replace the provisional name/UID, review the decision trace and video personally, and be prepared to explain the equations, code locations, negative findings, and next test without relying on the AI-generated wording.

