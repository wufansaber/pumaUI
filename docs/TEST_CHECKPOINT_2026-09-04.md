# Test Checkpoint - 2026-09-04 17:50 CST

This checkpoint records the source state before the requested pause. Changes are saved
in the working tree and have not been committed or packaged.

## Verification

- Full unit suite: 109 tests passed.
- Focused Inspection Tests and Run Control suite: 53 tests passed.
- Offscreen UI smoke: Puma main window, Sensitivity, VNC, and display-color dialogs constructed successfully.
- Python bytecode compilation: passed for the complete `puma_ui` package.
- `git diff --check`: passed. Git reported only existing LF-to-CRLF conversion warnings.

## Manual Fidelity Completed In This Session

- Lot Plan runtime Protect and Repeat Count permissions.
- Care Area manual Page Break move, repeat, and orientation-aware sorting.
- NanoPoint SEM overlay, FOV, rotation, correlation selection, POI search, MCA, and noise-box controls.
- System display-color categories with CPS save/load and restore operations.
- Sensitivity parameter-set save/load/delete.
- VNC Collect/Analyze workflow with MaxBW collection defaults, simulated JobDump names,
  Image Packer CSV analysis, missing-value handling, and zero-defect collection results.
- NanoPoint SEM correlation now preserves the selected candidate index and geometry
  when the operator accepts a non-first match.

## Remaining Manual Work

- Complete NEF external classifier tree and classifier metadata simulation.
- Implement Inline Defect Organizer setup and Chapter 7 workflow.
- Finish advanced Wafer Post Processing editors: Venn visual details, Precision/Diversity
  rule editors, and Excursion reusable expressions.
- Finish advanced Inspection Run queue/cassette behavior and explicit SECS/ILink status.
- Finish advanced Review filters, classify folders, result transfer variants, KLARF import,
  Optics Selector, and Sensitivity Tuner.
- Perform desktop visual QA at 1920x1080 and the minimum supported size.
- Replace the remaining Image Display File/Actions/Move Stage/Color/Zoom/Help menu
  placeholder actions with the exact manual commands; the existing image and zoom
  controls are functional.
- Perform the final source-mode chapter walkthrough.
- Repair and smoke-test the Windows package only after functional acceptance. Packaging
  remains intentionally deferred.

## Next Manual Target

The next bounded implementation target is NEF/iDO classifier fidelity from manual pages
238-243 and 549-551:

- Parse classifier metadata into the tree preview instead of showing a filename-only simulation.
- Validate iDO classifier orientation against the Test orientation.
- Validate Feature Vector version compatibility and automatically enable Save Feature Vectors
  when Run iDO is enabled.
- Preserve the existing sequential-classifier behavior: up to five ST-NEF/iDO entries,
  ordered execution, Keep Nuisance, ST-NEF role flags, and named configuration
  save/delete/clear operations.
