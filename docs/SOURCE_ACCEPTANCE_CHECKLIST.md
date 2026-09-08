# Puma 9980 Source-Mode Acceptance Checklist

Source: `docs/UserManual-9980.pdf`, revision AA. This checklist records simulator acceptance evidence; external hardware and proprietary service boundaries are listed separately in `MANUAL_COVERAGE_MATRIX.md`. Passing this checklist proves implemented workflow stability, not page-by-page manual fidelity; that stricter evidence is tracked in `MANUAL_PAGE_AUDIT.md`.

## Automated gate

- [x] `python -m compileall -q puma_ui scripts`
- [x] `python -m unittest discover -s tests -q` (425 tests)
- [x] `python scripts/operator_workflow_qa.py` (71 operator actions, 0 failures, including Home/Setup navigation, inline Wafer drawer, stored-site Alignment adjustment, partial-die map behavior, and Test classifier/grouping controls)
- [x] `git diff --check` (line-ending notices only)
- [x] Corrupt JSON recovery and schema migration tests
- [x] Shared RecipeStore round trips for recipes, preferences, jobs, results, transfer queue, and utility events

## Operator workflow gate

- [x] Recipe lifecycle: New/Open/Save/Save As/Derivative/Import/Extract/Insert/History/Delete/Search/Recent
- [x] Navigation: central workspace pages for primary workflows, modal selectors for short actions, Wafer/Test context switching, Home/Setup hierarchy, Back/Forward history, direct Navigate menu, and Recipe Overview deep links
- [x] Wafer setup: properties, handling, alignment, wafermap, reticle, scribe, edit, registration, defect data
- [x] Test setup: optics, Fourier, Care Areas, NanoPoint marked-defect/SEM/POI workflow, light, segmentation, sample plan, sensitivity, filters, iDO/NEF
- [x] Lot Plan: 25 slots, assignment, repeats, protection, backup, transfer, queue integration
- [x] Wafer Post Processing: every Chapter 6 operation, ordering, validation, templates, deterministic execution
- [x] Run: one wafer, queue wizard, pause/continue, snapshot, abort/recovery, overwrite, status, logs
- [x] Review: synchronized panes, filter/analysis, charts, images, classification, import/export/transfer
- [x] DBB: registration/setup, DBC/DBG attributes, five-pane view, clips/folders/classifier, analysis sampling
- [x] Sizing: setup, SST maps/scatter/histograms, references, defect sets, XML, consolidation
- [x] System Utilities: Chapter 12 local administration and SECS/equipment simulation surfaces
- [x] XP Offline/GDS2CA: generation, AutoLearn/assist, RDS, comparator, conversion, registration, CAG assignment

## Visual gate

- [x] Main shell and Recipe/Wafer/Test overview alignment
- [x] Wafermap, Edit Map, and three-port Wafer Handling
- [x] NanoPoint Image Templates, NPCA selection, Apply Offset, Light Training, Segmentation, SDI, Sample Plan, Row Pattern, Sensitivity Parameters and Lot Plan at native Windows DPI
- [x] Review, Advanced Classify, Multi-Test duplicate filtering, current-wafer transfer options, iDO Rough Class/Group filtering, Optics Selector, Sensitivity Tuner, and ST-NEF
- [x] iDO legacy FX upgrade control and Run Status Test Information at native Windows DPI
- [x] DBB registration/setup/review, four-page setup, four-image Review Gallery, Library/Bin/POI workflow, five-pane DBB View, and Analysis Toolbox
- [x] Inspection Run at native Windows DPI: Run One Wafer, multi-Test Run Status, Open Lot Result wildcard search, ready/material queue states, and Snapshot Review
- [x] Sizing/SST, System Administration, XP Offline, RDS, Comparator, GDS2CA, and CAG Editor
- [x] Native Windows fonts and minimum supported 1180 x 760 main-window layout

## Release gate

- [x] Rebuild `dist\Puma9980UI\Puma9980UI.exe` and `release\Puma9980UI-Windows.zip` after the current manual-audit changes.
- [x] Start the rebuilt GUI for 10 seconds with an isolated `%LOCALAPPDATA%` directory and close the test process.
- [x] Run the rebuilt package's `--smoke-test` path for recipe save/reload, valid run setup, one-wafer run, result save/reload, and result review.
- [ ] Repeat the package launch on a separate clean Windows machine before production distribution.
