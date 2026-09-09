# Puma 9980 Manual Interaction Acceptance - Final Update 2026-09-09

This checkpoint records source-mode interaction testing against the Chinese chapter summary in `docs/UserManual-9980-zh`, with the source PDF used only where the summary omits a figure or detail. It separates executable simulator behavior from read-only indicators and external equipment boundaries.

## Result

- Isolated full regression: **564 passed, 0 failed** across **29 test files**.
- Operator walkthrough: **88 passed, 0 failed**.
- Operator surface inventory: **204/204 opened**, visible, and no larger than 1920 x 1080.
- Named conditional controls: **132/132 present in test/workflow assertions**, **0 unreferenced**.
- Manual audit suite: **119 cases**, including real Qt mouse/keyboard scenarios and document-range verification.
- Manual section index: **875/875 numbered headings mapped** to final audited ranges, with no `PENDING` or `PARTIAL` software section.
- Primary-entry policy: Tests, Lot Plan, Wafer Post Processing, Setup Run, Run One Wafer, Review, Alarm, Image Display, Snapshot Review, Design Registration, DBC, DBB, Wafer Map actions and Test modules remain clickable; unmet prerequisites are validated when the action is attempted.

## Gray-Control Acceptance Rule

Primary function entries are intentionally excluded from gray-state gating. They remain clickable and explain unmet prerequisites on action. Every remaining conditionally disabled process control must meet all applicable checks:

1. Initial disabled state matches a missing prerequisite.
2. The prerequisite can be produced through valid simulator state or an operator action.
3. Enabling one valid module does not incorrectly disable an unrelated module.
4. The enabled control accepts a real mouse/keyboard action and changes state or opens its target.
5. Removing the prerequisite relocks only the dependent control.
6. Invalid input, Cancel, and failed confirmation do not commit partial state.

The static audit found no named `self.<control>.setEnabled(...)` condition absent from the test/workflow assertions. Always-open entry behavior plus internal lock, unlock, action, cancel, save, and relock coverage is provided by the grouped Qt interaction scenarios below.

## Gate Coverage

| Area | Conditions exercised | Result |
|---|---|---|
| Main navigation | Tests, Lot Plan, WPP and Setup Run remain enabled; missing Alignment/Wafermap/Test/assignment/run prerequisites produce an action-time message without navigation or state mutation | PASS |
| Design features | Design Registration, DBC and DBB remain enabled; Alignment + reticle + Pixel Perfect and registration prerequisites are enforced when clicked | PASS |
| Wafermap image | Entry remains enabled; without an acquired image the toggle immediately resets and reports the requirement | PASS |
| Recipe and results | Selecting a recipe unlocks Delete/Path; saved results unlock Review Wafer; saved Places unlock Remove | PASS |
| Recipe lifecycle | Extract/Insert round trip updates component status; derivative recipes stay blocked until reference reselection; save/reload retains history | PASS |
| Wafer handling | Mapped slot unlocks Load; alignment sites unlock Load & Align; wafer on chuck unlocks Unload and Recovery; return relocks both | PASS |
| Alignment | Image Display is embedded as the resizable right screen; BF Low Mag/High Mag switches change the displayed scale; Standard Dual Magnification persists through BF site selection; stored sites, derivative reference, Site Offset and automatic 10-target score qualification behave as documented | PASS |
| Layer database | Selecting a row unlocks Modify/Delete; a current recipe layer missing from the database unlocks Add Current Recipe's Setting; adding it relocks the action | PASS |
| Inspection setup | Fourier, Care Area order, Sample Plan edge, Segmentation Break, Sensitivity algorithm, secondary-die and channel-fusion dependencies | PASS |
| Multiple orientations | Rotate Wafer stores the previous Alignment/Wafer Map and activates the requested profile; all four profiles are required for a four-Test run and retained in result metadata | PASS |
| DBB | DBG1/DBG2 controls, supergrouping, filter, sampling and clip-transfer gates can reach their valid states without conflict | PASS |
| Run and Review | Snapshot entry remains enabled and reports when no Local run is active; Update Snapshot and complete-data operations, pause, abort, Results Utility, selection and transfer controls follow their documented contexts | PASS |
| Alarm and status | Alarm Alert follows active-event state; Safety/SECS filtering, details and Clear permissions work; Wafer/ISECS/ILink symbols cover every documented simulator state | PASS |
| Sizing and WPP | Lot-result reference, computed-size option, precision, diversity, density, attribute and sampling dependencies | PASS |

## Defects Corrected During Testing

- `SegmentationImageGrabDialog` Finish was connected to a missing handler. Finish now validates marked sites and acquired images before accepting.
- `FourierBoxDialog` shadowed QWidget `width()` and `height()` with spin-box attributes. The controls were renamed so the dialog can be measured and displayed normally.
- `GridColumnsDialog` expanded to about 1660 pixels tall. Its column choices now use a scrollable two-column layout within a resizable desktop-sized dialog.
- The Alignment command menu appeared as a narrow floating dialog over the wafer content. It is now a responsive main-workspace page with horizontal operations and persistent alignment status; only confirmations and bounded setup steps remain modal.
- Derivative old-corner and Site Offset controls had no reachable enable path. Stored old-corner availability and selection now drive them.
- Add Current Recipe's Setting in the layer database was permanently disabled. It now enables only when the current recipe layer is absent, adds it once, then relocks.
- Snapshot Review remained selectable outside a run and in SECS Remote mode, while complete-data operations stayed disabled after the snapshot became complete. The menu gate and post-update control refresh now follow sections 9.4.2-9.4.2.0.2.
- Decoupled Channel Fusion parameters were available before Decouple Channel Fusion was selected. They now require HLAT or Secondary HLAT and the enabled checkbox, matching sections 4.12.7-4.12.7.1.
- Four Test orientations shared one Alignment/Wafer Map state, allowing one direction to overwrite another. Each direction now has an independent persisted setup profile, with missing-profile Run gating and per-Test orientation metadata in results.
- Primary function entries used gray-state gating that prevented operators from opening or understanding unavailable modules. Entries now remain enabled and perform explicit prerequisite validation when clicked; internal process controls retain state-dependent behavior.
- Auto Site Selection displayed fixed manual-example Target Quality values without calculating candidate measurements or qualification. It now evaluates Correlation, Uniqueness, Sharpness and Feature scores by direction, selects the best requested candidate, shows per-cell pass/fail state and saves the measured result for the active orientation.
- Alignment's Image Display still behaved as a detached modal and BF had no usable Low Mag/High Mag display switch. Alignment now keeps the complete Image Display beside its operations in a resizable dual-screen workspace, synchronizes DF/BF state, and renders distinct BF Low Mag and High Mag views.
- Legacy recipes loaded from the recipe browser contained metadata but no setup payload, so valid recipes were incorrectly asked to repeat Alignment, Wafer Map, Test, Lot Plan, WPP and Design prerequisites. Missing legacy sections are now hydrated with clearly simulated editable defaults while stored sections are preserved; execution-only safety validation remains active.
- Review could open an empty result selector on a fresh installation. Two deterministic demo wafers plus KLARF, CSV, JSON and RDF support files are now available under `demo_data`, with an explicit Demo Data filter and non-destructive result seeding.
- The View menu omitted Review Toolbar and Review Image Toolbar, and Images duplicated Image Display. Both toolbar groups now have reversible visibility state; Images opens the last Alignment Swath while Image Display remains the acquisition surface.
- SECS exposed only generic configuration/operation dialogs. Its manual commands are now directly selectable and persistent, communication defaults to enabled for new profiles, and Local/Remote selection no longer invents a wafer-loaded interlock.
- File Administration only redirected to recipe/result selectors. It now copies, moves, deletes and converts selected local recipe/result data and writes managed JSON files to the chosen destination.

## Manual Anchors Rechecked

| Manual location | Required operator sequence checked |
|---|---|
| 3.7.1.5-3.7.1.6, pages 128-130 | Laser-sensitive selection enables factor/layer controls; layer Add/Modify/Delete selection rules; Dark/Darkest selection |
| 3.8.3.1, pages 149-154 | Auto Site Selection marks three die-corner/street positions, acquires the requested candidate count, compares 10 applicable quality scores with targets, reports qualification and stores the best candidate |
| 3.8.2-3.8.3, pages 142-160 | Image Display remains visible beside Alignment; BF Standard Dual Magnification provides Low Mag and High Mag image views and retains the selected mode through site selection |
| 3.8.3.3.1-3.8.5.1, pages 161-165 | Settings enables High Precision Alignment; Prev/Next site adjustment; derivative reference defaults to Die Origin and requires reselection |
| 3.5.2-3.5.5, pages 114-123 | Derivative reference gate; Extract/Insert component status; save/reload and Recipe History |
| 4.2.2-4.2.3, pages 226-230 | Rotate/keep/cancel confirmation; independent 0/90/180/270-degree Alignment and Wafer Map setups; all four Tests selected in Run One Wafer |
| 4.5.22.1, page 343 | Always Use Default Order disables manual order; clearing it enables grid and Move Up/Down |
| 4.7.1-4.7.2.1, pages 361-373 | Mark Site precedes Grab Images; Finish follows completed grabs; Break controls require a selected type-compatible break |
| 4.12.7, pages 425-428 | Decoupled Channel Fusion is available only for HLAT/Secondary HLAT and parameters follow checkbox selection |
| 9.4.2-9.4.4, pages 667-670 | Snapshot only during Local-mode run; complete update restores functions; Pause/Continue and scoped Cancel/Abort behavior |

## Intentionally Non-Interactive Gray Items

The following gray items are state displays or context restrictions, not blocked modules waiting for an unlock condition:

- Computed coordinates, registration scores, fixed current-machine pixel/imaging values, and equipment status indicators.
- Job Setup fields in explicit read-only/view mode.
- Analysis, sampling, transfer, and defect-offset actions while reviewing an incomplete run snapshot; the same actions are available for a completed result.
- Run controls after completion or abort, and Update Snapshot after the active inspection is no longer available.
- Hardware/configuration choices represented by one installed simulator option. These are shown as fixed values and are not claimed as production hardware controls.

## External Boundary

This acceptance does not claim physical stage motion, camera acquisition, robot/carrier I/O, laser output, SEM, proprietary RDF/DBC parsing, ISECS/ILink host communication, or factory storage. Those paths use deterministic simulator state or explicit boundary notices and require equipment-integration acceptance on a connected Puma tool.

## Commands

```powershell
.\.venv-build\Scripts\python.exe -m compileall -q puma_ui scripts tests
.\.venv-build\Scripts\python.exe scripts\run_isolated_test_suite.py
.\.venv-build\Scripts\python.exe scripts\operator_workflow_qa.py
.\.venv-build\Scripts\python.exe -m unittest discover -s tests -p "test_manual_surface_inventory.py" -v
```
