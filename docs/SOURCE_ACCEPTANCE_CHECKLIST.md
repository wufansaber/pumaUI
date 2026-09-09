# Puma 9980 Source-Mode Acceptance Checklist

Source: `docs/UserManual-9980-zh`, the Chinese Markdown summary of revision AA; the PDF is used only for omitted figures/details. This checklist records simulator acceptance evidence; external hardware and proprietary service boundaries are listed separately in `MANUAL_COVERAGE_MATRIX.md`.

## Automated gate

- [x] `python -m compileall -q puma_ui scripts`
- [x] `python -m unittest discover -s tests` (564 tests across 29 test files)
- [x] `python scripts/operator_workflow_qa.py` (88 operator actions, 0 failures, including loaded-recipe reuse, Home/Setup navigation, inline Wafer drawer, central-workspace Alignment/Image Display dual screens, BF Low/High Magnification switching, automatic Alignment scoring and adjustment, partial-die map behavior, and Test classifier/grouping controls)
- [x] 204/204 discovered `QDialog`/`QMainWindow` operator surfaces open successfully and fit within a 1920 x 1080 desktop.
- [x] 875/875 numbered headings from the extracted 9980 manual map to a final audited section; no software section remains `PENDING` or `PARTIAL`.
- [x] 119 manual-audit test cases cover primary entries, action-time prerequisites, internal lock/unlock behavior, invalid/cancel/save paths, recipe-component round trips, four-orientation setup/run paths, Chapters 10-14 and Appendices A-C. See `MANUAL_INTERACTION_ACCEPTANCE_2026-09-08.md`.
- [x] `git diff --check` (line-ending notices only)
- [x] Corrupt JSON recovery and schema migration tests
- [x] Shared RecipeStore round trips for recipes, preferences, jobs, results, transfer queue, and utility events

## Operator workflow gate

- [x] Recipe lifecycle: New/Open/Save/Save As/Derivative/Import/Extract/Insert/History/Delete/Search/Recent, including event-driven Extract/Insert and derivative-reselection persistence
- [x] Navigation: all primary function entries remain enabled; unmet prerequisites are explained on click; central workspace pages, bounded modal selectors, Wafer/Test context switching, Home/Setup hierarchy, Back/Forward history, the Recipe Overview Configure action, and overview deep links are covered
- [x] Wafer setup: properties, handling, automatic Alignment candidate scoring/threshold qualification, interactive alignment, wafermap, reticle, scribe, edit, registration, defect data
- [x] Test setup: optics, Fourier, Care Areas, NanoPoint marked-defect/SEM/POI workflow, light, segmentation, sample plan, sensitivity, filters, iDO/NEF, plus independent 0/90/180/270-degree Alignment/Wafer Map profiles and one four-Test run
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
- [x] Alarm Alert tabs/taxonomy/filter/permissions and Wafer/ISECS/ILink status-symbol states
- [x] Wafermap, Edit Map, three-port Wafer Handling, side-by-side Alignment/Image Display with BF Low/High Magnification, and Alignment target/measured quality tables
- [x] NanoPoint Image Templates, NPCA selection, Apply Offset, Light Training, Segmentation, SDI, Sample Plan, Row Pattern, Sensitivity Parameters and Lot Plan at native Windows DPI
- [x] Review, Advanced Classify, Multi-Test duplicate filtering, current-wafer transfer options, iDO Rough Class/Group filtering, Optics Selector, Sensitivity Tuner, and ST-NEF
- [x] iDO legacy FX upgrade control and Run Status Test Information at native Windows DPI
- [x] DBB registration/setup/review, four-page setup, four-image Review Gallery, Library/Bin/POI workflow, five-pane DBB View, and Analysis Toolbox
- [x] Inspection Run at native Windows DPI: Run One Wafer, multi-Test Run Status, Open Lot Result wildcard search, ready/material queue states, and Snapshot Review
- [x] Sizing/SST, System Administration, XP Offline, RDS, Comparator, GDS2CA, and CAG Editor
- [x] Native Windows fonts and minimum supported 1180 x 760 main-window layout

## Release gate

- [x] Rebuild `dist\Puma9980UI\Puma9980UI.exe` and `release\Puma9980UI-Windows.zip` after this manual-interaction audit when packaging is requested.
- [x] Start that rebuilt GUI for 10 seconds with an isolated `%LOCALAPPDATA%` directory and close the test process.
- [x] Run that rebuilt package's `--smoke-test` path for recipe save/reload, valid run setup, one-wafer run, result save/reload, and result review.
- [ ] Repeat the package launch on a separate clean Windows machine before production distribution.
