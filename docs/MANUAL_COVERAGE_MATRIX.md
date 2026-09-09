# Puma 9980 Manual Coverage Matrix

Source: `docs/UserManual-9980-zh`, the Chinese Markdown summary of revision AA, with the PDF retained for omitted figures/details. A checked item means the behavior is implemented, persisted where applicable, and covered by a focused test or UI smoke check. Partial items remain unchecked.

Supplemental cross-check: the supplied Puma 95XX/96XX Version 9.6 SP1 manual was used to clarify Recipe Overview navigation, Inspection Properties, History Log, and valid/nonoptimal/invalid component status indicators. The bundled Puma 9980 Version 9.8.306 manual remains authoritative wherever the manuals differ.

## Chapter 2 - System Overview

- [x] Main UI shell, distinct Home main menu and Setup Recipe Overview, menu bar, standard/setup/optics controls, functional Back/Forward hierarchy navigation, Navigation Bar visibility control, recipe summary, core status display, generic alarm simulation, and simulator boundary notices.
- [x] Chapter 2 error-message Daily Log export, optional E84 display, Alarm tabs/taxonomy, and Wafer/ISECS/ILink status-symbol states are covered; physical signal behavior remains an equipment boundary.
- [ ] Full hardware component diagnostics, physical safety-interlock behavior, and equipment error recovery. These require a separately reviewed hardware adapter and cannot be represented as real tool control in this simulator.

## Chapter 3 - Wafer Setup

- [x] Recipe selection, recent/local views, search, filter, columns, context operations, save, delete, and history (3.4-3.5, 3.10).
- [x] Wafer properties, orientation/type, laser power, dark-wafer controls, and wafer handling (3.6-3.7). Carrier/slot states, single-wafer chuck protection, optional wafer ID read, alignment-site gating, source-slot unload, laser-sensitivity warnings, and automatic recovery are persisted and tested.
- [x] Alignment optics, Image Display, automatic/custom site selection, derivative reselection, qualification, manual alignment/registration, and temporary alignment (3.8). Alignment and Image Display now share a resizable main-workspace dual-screen layout; the Image Display action focuses the persistent right screen instead of opening another dialog. BF exposes Low Mag and High Mag image views with visibly different image scale, and Standard Dual/Single Magnification is retained through site selection. Auto Site Selection acquires a configurable number of deterministic simulator candidates, calculates Correlation/Uniqueness/Sharpness/Feature values for Align/X Reg/Y Reg, applies every applicable target threshold, selects the best candidate, displays PASS/NOT QUALIFIED per item, and persists the selected scores by orientation. Existing-site warnings are conditional, new recipes bypass derivative reference selection, and Align/Qualify/Manual actions follow their documented prerequisites.
- [x] Die values, scribe lines, edit map, reticle size, die-corner adjustment, partial die, inner die, and KLARF coordinate settings (3.9). Zero-scribe and pending-die-corner exit warnings, 1200 um die-pitch floor, site-count gates, reticle axis limits, imported-geometry invalidation, and multi-step Edit Map Undo/Redo are covered.
- [x] Review microscope optics and defect-data attachment/import simulation (3.10-3.11). Review Optics named settings implement 21-character Save/Load/Delete plus Apply/OK/Cancel semantics. Setup-Review is gated by attached data and wafer alignment, distinguishes selected from marked DOI, generates Derived Hot Spots only from marked defects, and automatically detaches data after geometry changes.
- [x] Re-audit warning, configuration-dependent disabled state, and alternate-path behavior against pages 121-217. Hardware movement, camera acquisition, factory-host transfer, and Config.xml timing remain explicit simulator boundaries.

## Chapter 4 - Inspection Setup

- [x] Test selection, orientation, multiple tests, add/copy/delete, and mode selection (4.2).
- [x] NEF classifier selection (4.3.1.2-4.3.1.3). Single-classifier browsing, JSON/XML/text metadata parsing, tree preview, persisted classifier data, up to five ordered ST-NEF/iDO classifiers, per-entry ST-NEF role, saved setup load/delete/clear, Keep Nuisance behavior, and runtime execution reporting are implemented and tested. Pixel/channel/incidence-specific IRIS choices and light/Fourier retraining invalidation remain integrated with the Test matrix; the manual defines IRIS as an option list rather than a separate parameter dialog.
- [x] Fourier sample-plan selection, multi-box create/edit/delete and channel assignment, advanced options, optics/orientation invalidation, training gating, 11 rods per channel, numeric rod adjustment, specular block gating, Analyze scores, and filtered/unfiltered image comparison (4.4).
- [x] Care Areas chapter workflows (4.5). CA/DCA/ACA groups, copy/fill, editing, register/verify states, multi-group offsets, border expansion ordering, ACA Page Break generation/regeneration, manual Page Break move/repeat/orientation sorting, and CAG coverage report are implemented. Derived groups perform signed Grow/Shrink and two-parent Intersection geometry, refresh from nested parents, enforce Intersection operation restrictions and delete recursively with their parents. NanoPoint includes the 30-target limit, real marked-defect and Patch/SEM metadata import, SEM FOV/rotation/overlay and correlation selection, Care Area transfer, POI search, image modes/overlays, Premap/light/stage prerequisites, reference Die, MCA/noise-box limits, image grabbing, combined MDAT/NPI runtime output, per-template counts, and Review NPI attributes. NP Design/Image Care Area import enforces Entire Die, compatible mode, mutual exclusion, real JSON/XML Inspection Step/CAG discovery, registration source, marked-site/two-site registration, corner-by-corner verification, and the NP Image operation/invalidation rules.
- [x] Light Training and retraining decisions (4.6). Active Region is gated by Active Die focus mode and validates nonempty in-die geometry; PILO/Legacy requirements, Extended/Exposure modes, histogram visibility, sample plan, Current/All Tests retraining, skip-valid behavior, Fourier-filtered Care Area containment, Page Break exclusion, actual-die-size `2000 x 2000 um` Noise Box validation, training-gated Finish, and loaded/aligned Retrain gating are implemented and tested.
- [x] Segmentation image grab, site selection, mode-specific editable Breaks, consecutive groups, validated cross-channel sources, and Single Die Inspection core workflow with independent Test Summary enablement (4.7-4.8).
- [x] Sample Plan fidelity (4.9). Wafer modes, overrides, Partial Die 2000 um boundary, shared Inside/Outside edge geometry, die-intersection edge selection, N-of-M/percentage row patterns, one recipe Master Plan, Edit/context-menu cross-Test copy/paste with `Ctrl+Shift+C/V`, legend, custom colors, KLARF SampleTestPlan import, Grid Pitch positioning, and Inner Die capability gating are implemented and tested. System-wide Setup/Run/Review/Alignment color categories support Apply, CPS save/load, Restore All, and category restore.
- [x] Inspection swath coverage control (4.10). The 100/50/25/12 percent and Die/Reticle Based options now persist and deterministically affect simulated inspection results, with execution accounting.
- [x] Specialized sensitivity workflows (4.11-4.13). Per-Test HLAT/FAST/AutoSens exclusion; primary and Enhanced Secondary algorithms; WSP and GAP dependency rules; CF2/CF3 Flavor gating; per-region/channel and whole-Region copy/paste; Remap; CIB/Preconvolver; Post Filter; Dark Defect Factor; Decoupled Channel Fusion; AutoSens Production/Engineering; one/two-region VNC with three-channel MaxBW; executable Process Noise Filter; and RTA+ defaults/range are implemented. Run/Review now expose Region, algorithms and HLAT CF attributes. Sensitivity parameter sets and simulated VNC collection preserve the documented external hardware boundary.
- [x] Inline Defect Organizer setup integration (4.14). iDO classifier browsing and tree preview, Test-orientation and Feature Vector-version validation, automatic Save Feature Vectors coupling, runtime Rough Code assignment, and `FeatureVectors.bin` result state are implemented.
- [x] Test validation and recipe save integration (4.15).

## Chapter 5 - Lot Plan

- [x] Wafer/test assignment, 25 slots, row/column assignment, repeat tests/counts, unload repeat, protection, backup, result cache, transfer host, share, and tool type (5.1-5.3).
- [x] Run-menu editing follows the manual Protect rule: an unprotected plan is editable; a protected repeating plan exposes only Repeat Count during Run (pages 461-466).

## Chapter 6 - Wafer Post Processing

- [x] Ordered operation palette, enable/disable, property editor, validation, whole-scheme and selected-operation templates, and recipe persistence (6.2).
- [x] Venn manual workflow (6.3.1). Default 5 um tolerance, optional Multi-Test groups, Clear Venn IDs, per-group default/custom tolerance, largest/summed inspected-area selection, highest-intensity/prioritized-Test-ID duplicate retention, priority reordering, persisted settings, actual duplicate filtering, runtime reports, and fixed-width visual QA are implemented and tested.
- [x] Clustering, DSA/DSA+, Repeater, CAG, Spatial Population, and Population Arbitration (6.3.2-6.3.7). Parameter pages and range/dependency validation are backed by deterministic runtime processing: auto/manual clustering and second-pass merge, local prior-layer DSA matching and common-defect removal, post-sequence UPLD insertion/image limits, repeater grouping, CAG assignment, scratch signature fields, majority roughbin arbitration, excluded codes, and execution reports. Klarity/UDB, optical camera, and factory transfer remain simulated external boundaries.
- [x] Precision and Diversity sampling workflows (6.3.8-6.3.9). Four independently selected sampling schemes, one-method-per-scheme behavior, ordered Precision rules, per-rule Quick Filter/Rule Editor and sampling settings, saved-rule load/save, overlap/bin settings, Discovery/Production Diversity controls, attribute/bias/density/limit editors, Proportional, Random/Class Code tabs and code rows, Trigger, Smart, validation, persisted state, and deterministic runtime sampling marks are implemented and tested.
- [x] Defect Limits and Excursion Reduction (6.3.10-6.3.11). Defect limits are enforced during run. Excursion Reduction includes ordered Quick Rules, reusable Define Expressions, expandable Expressions Overview, transfer options, persisted state, runtime rule matches, and KLARF inclusion scope that preserves the complete local result.

## Chapter 7 - Inline Defect Organizer

- [x] Attach/browse an iDO classifier, validate recipe orientation and feature-vector version, upgrade legacy FX versions from Sensitivity Parameters, run deterministic Rough Class/Group assignment, expose iDO and FX status during Run, save feature-vector result state, filter Rough Class/Group independently, review selected/displayed scopes, clear codes, refresh maps, and record execution history.
- [ ] IMPACT XP classifier creation, optimization, and production classifier version-control service integration. These remain an explicit external-system boundary.

## Chapter 8 - Design Based Binning

- [x] DBB IMC status simulation exposes Active, Inactive, and Service not Started states; Design Registration remains clickable and enforces Alignment + Reticle + Pixel Perfect prerequisites when invoked.
- [x] RDF metadata selection, inspection/process layers, RDF-before-Sites gating, SemiAutomatic A2D, Manual, and Design Offsets/Scales paths, strategy-specific site counts/distance, Lock + Overlay verification, and geometry-change invalidation.
- [x] DBB recipe settings for DBC/DBG1/DBG2, systematic thresholds, filter-out rule and DCI dependency, Supergrouping, clip size, rotation/flip, throughput, DCI/PCI/design attributes, pattern density/overlap, the fixed 200-clip transfer ceiling, and complete DBB sampling limits/priorities.
- [x] Real HotSpot CSV parsing and size validation, DBC example/bin assignment, corrected 0-4 Global Bin semantics, deterministic DBB execution attributes, DBB sampling marks, expanded Review grid/chart dimensions, four-image Gallery, and marked DBB Clip saving.
- [ ] Real RDF/DBC file parsing and Design Services transfer, full visual RDF/wafer registration viewers with snapping/pan/ruler, production DBC classifier training/library distribution, and proprietary RDF HotSpot extraction.
- [x] Dedicated five-pane DBB View with Wafer/Design tabs, visual Clip Gallery, expanded defect grid, DBC Library lifecycle, ordered Bin properties, invalid/valid POI workflow, Manual Bin assignment, Folder/Chart pane, status summary, defect scopes, grouping, zoom, captions, Magnifier, Histogram, persisted result changes, and DBB Analysis Toolbox execution/sampling with documented priority and limits.

## Chapter 9 - Inspection Run

- [x] Run One Wafer IDs, test selection, repeats, backup, auto transfer, patches, hi-res, Instant Review, progress, version ID, Snapshot Review, pause/continue, and scoped abort simulation (9.4.1-9.4.4). Patch/Hi-Res options enforce their Test/WPP sampling prerequisites; per-Test Feature Vector and classifier Version IDs are retained and compared.
- [x] Overwrite-result confirmation with optional backup, Print on Run preferences/logging, high-defect-count abort, and explicit alignment/registration failure recovery paths (9.3-9.4).
- [x] Persistent queue shell, material/cassette/slots, statuses, add/remove/view/start/cancel/purge, and run log (9.5-9.6). Waiting-for-material Jobs cannot start; starting a ready Job continues through later ready Jobs; failures do not prevent later queue items.
- [x] Multi-inspection Job Setup Wizard and queue operations (9.5-9.6). Cached inspection selection with primary ordering, 25-slot expected cassette map, Bottom Up/Top Down/Random order, per-slot inspection tests/Wafer ID/repeats, per-inspection Lot IDs and result actions, Add Inspection flow, multi-remove, edit/view/context actions, material and queue states, remote/material-associated read-only restrictions, ordered execution plans, persistent queue state, wildcard Lot Result log selection, and printable Current Log export are implemented and tested.
- [x] SECS/ILink simulation boundary (9.2). Tools > SECS provides Local/Remote mode, host/port settings, persistent ISECS/ILink status, status-bar indicators, Remote-mode Setup Run blocking, validation, and an explicit notice that the simulator does not open hardware or factory-host connections.

## Chapter 10 - Inspection Review

- [x] Select Lot Results with search, recipe matching, deletion, and persistent results (10.7 core).
- [x] Synchronized Wafer Map, Defect Properties Grid, Image Gallery, class-code chart, summary, status, navigation, marking, and resizable panes (10.1 core).
- [x] Display/context workflows (10.1.2-10.2). Review/Wide Grid/Advanced Classify layouts, class-code and attribute folders, map Defect/Die/Reticle selection, Grid/Wafer Map context operations, Filter In/Out/Reset, configurable columns, manual classification, gallery image modes/zoom/grab/export/ROI/histogram, image availability filters, Bar/Pareto/Stacked/Side-by-Side charts, WPP/CAG/signature dimensions, summaries, Wafer Map display rules, saved grid/chart configurations, and Super Class schemes are implemented and tested. A native-font acceptance walkthrough remains in the final verification gate.
- [x] Filter and Analysis ordered mixed filter/analysis operations, enable/disable and ordering, named templates, General/Venn/Sensitivity/Class/Channel/Advanced filters, Quick Filter/Rule Editor expression handling, recipe WPP property integration, real ordered execution on the active defect scope, execution logging, persistence, and focused tests (10.3-10.5).
- [x] Auto Label with tolerance and preserve/ignore preferences, Merge Result, and Save Filtered Lot As with filtered-image restrictions (10.6).
- [x] Lot-selection operations and defect image workflows (10.7-10.8). Local/Recent views, toggleable search/clear, configurable columns, Info, path display/open, quick-reference folder persistence, delete/refresh context operations, Review Only/Loaded/Inspected selection, parameterized Review/Inspection/Simulated image grab, mark clearing, MiniStrip/reference settings, and separate lot-image/wafer-result/lot-result transfers are implemented and tested.
- [x] KLARF import, offset, and Optics Selector core workflows (10.9-10.11). KLARF parsing, recipe/result match validation, persistent imported results, defect and die-origin offsets, defect/location site marking, optics-mode selection, deterministic grab/analysis scores, image/reference/channel display choices, CSV export, and insertion of selected modes as recipe tests are implemented and tested. Physical stage/camera activity remains explicitly simulated.
- [x] Sensitivity Tuner and ST-NEF workflows (10.12-10.14). Run One Wafer sensitivity-data/OSTS collection, HLAT/FAST OSTS gating, test/region/defect-type/path/algorithm/channel/parameter selection, independent edited/committed state, recipe-value restoration, slider and Catch/Lose tuning, deterministic recalculation, interactive plot controls, combined-result source histograms, multi-region/maximum-limit/advanced-parameter dialogs, Review filters/class-code sorting, and all Finish actions are tested. ST-NEF provides a resizable Hierarchical Classifier/Toolbox/Properties workspace with Starter Tree generation and partitions, NN/NEF nodes, lock/delete/nuisance operations, continuous/discrete attributes, one-dimensional histograms, two-dimensional attribute plots, cut lines, grouping, legends, classifier setup, persisted state, runtime crossover filtering, and fixed-size visual QA. Hardware-derived classifier scoring remains deterministic simulation.

## Chapter 11 - Sizing

- [x] Tool-side Sizing setup with the six documented scale factors and six cut lines, Collect Sizing Data gating, deterministic run-time sizing attributes, and Review filtering by applied scale-factor group.
- [x] SST lot-result and KLARF loading, dSize/Class Code conversion, tab/comma-delimited reference-size import, nonnegative reference-size editing, location-based overlay radius, automatic/manual maps, map selection/removal, and reference-size transfer.
- [x] Scatter plot with reference/computed axes, +/-0.2 um guide lines, non-zero filtering, computed-reference gating, scale-factor colors/highlighting, movable legend, defect coordinate tooltip, double-click editing, and live recipe recalculation.
- [x] Special Case, Size, and Planar histograms, cut-line sliders, out-of-graph display, cumulative density curve, saved defect sets, XML sizing-recipe export/import, and multi-wafer lot-result consolidation with retained source properties and reassigned defect IDs.
- [ ] Direct SEM connection, production KLARF overlay services, and physical tool sizing acquisition. These remain explicit simulator boundaries.

## Chapter 12 - System Utilities and Tools

- [x] Initialize Subsystems simulator with the documented no-wafer safety gate and individual/all subsystem selection.
- [x] Six-week/three-month Preventive Maintenance training checklists with locally persisted completion state and an explicit real-tool training boundary.
- [x] Run, Daily, Recipe History, and Flight log views backed by stored run/history/utility/job data.
- [x] Show Options accurately distinguishes installed, simulated, and not-yet-installed features.
- [x] SECS Equipment Constants tabs cover General, Communications, Material Flow, Carrier/Wafer ID-related choices, Report/Control state, and Remote Mode permissions with documented 15-30 second ranges.
- [x] Lot Summary, Data Transfer read-only configuration, queue retry/delete, service startup/shutdown, and automatic queuing when ILink or the transfer service is unavailable.
- [x] Delete Inspections with current-recipe protection and confirmation, Send Lots with transfer/queue fallback, Rename Lot across stored results/jobs/transfers, and persisted Click and Mark configuration.
- [x] Wafer Handling, alarm center, Print on Run, display colors, and SECS/ILink local/remote status simulation.
- [x] ERC Manager, Control Job Management, Substrate Tracking, and Carrier Management. Control/Process Job commands enforce the documented E87, E40/E94, SECS Remote, and equipment-constant gates; substrate/carrier state is persisted locally.
- [x] System Security and user/group administration, Signal Tower configuration/control, load-port indicator configuration, E116 EPT, log settings, Backup/Archive/Restore, Disk Admin, and Tools Configuration. Passwords are represented by hashes, and cleanup/backup operations update simulator metadata without deleting or restoring real system files.
- [x] SECS operation surfaces for E10 state commands, host messages, clock synchronization, and process-program upload/download are implemented as persisted local events. No real host connection is opened by the simulator.

## Chapter 13 - XP Offline Setup

- [x] Registration Site library with active sites and low/high-magnification optics metadata; Base Recipe validation requires wafer layout, alignment sites, and an active registration site.
- [x] Recipe Generator supports Base/Source selection, add/delete/all layers, naming tokens, Auto Fill, Production/Hot Scan/OSTS modes, optional Fourier/Light retraining metadata, Local/RDS destination, and persisted AutoLearn-Ready recipes with Valid for Run status.
- [x] AutoLearn state transition and Manual Assist configuration cover Fix Errors, Verify Results, timeout, signal-tower gating, success, pause, and abort paths.
- [x] RDS simulation provides central recipe snapshots, incrementing versions, production approval, changed-by history, and multi-tool distribution events. Recipe Comparator provides Local/RDS/All selection, quick filtering, production-only view, reference-recipe differences, editable values, configurable compact visibility, Tests view, and Save All.
- [ ] Live factory AutoLearn execution, production RDS server synchronization, and unattended inspection-tool distribution require external services and remain explicit simulator boundaries.

## Chapter 14 - XP GDS2CA

- [x] Standalone GDS2CA converter workflow with CAGDS, Mapping CSV, Config CSV, Registration Clip metadata, Use Default Data, local/RDS destination selection, generated component status, and recipe Care Area import.
- [x] Two-point registration/re-registration and scaling model, scale-deviation warning result, inspectable-die pruning report, V*R*/V*R/VR*/VR status representation, selected-Test import, and CAG Editor filtering plus fixed/sequential 1-32000 code assignment.
- [ ] Proprietary production CAGDS binary polygon decoding, real registration-image acquisition/stage motion, and external RDS component sharing remain explicit integration boundaries because their specifications/services are not supplied by the manual.

## Verification Gates

- [x] Pure-state unit tests for recipes, Tests, Lot Plan, WPP, Run, Review, recovery, and cross-module flow.
- [x] Offscreen UI smoke tests for the current Wafer Setup, Tests, WPP, and Run/Review core flows.
- [x] Focused tests for every completed manual subsection above. The current source suite contains 564 passing tests across setup, run, review, utilities, DBB, sizing and offline workflows.
- [x] Native-font desktop visual QA for the main shell, Wafermap/Edit Map, three-port Wafer Handling, Review/Advanced Classify, Optics Selector, Sensitivity Tuner, ST-NEF, Equipment Constants, Data Transfer Queue, Lot Summary, Design Registration, DBB/DBC Setup, Review Design, five-pane DBB View, DBB Analysis Toolbox, SST scatter workspace, Sizing Recipe, Sizing histograms, Control Job Management, User Administration, Signal Tower, Disk Admin, XP Recipe Generator, Recipe Comparator, RDS Manager, GDS2CA Converter, and CAG Editor. Narrow Review uses deliberate two-axis scrolling instead of compressing panels into overlap.
- [x] Current source-mode acceptance walkthrough using `SOURCE_ACCEPTANCE_CHECKLIST.md`, the 564-test suite, the 88-step event-driven operator workflow (`scripts/operator_workflow_qa.py`), and native Windows visual QA artifacts.
- [x] Windows package build, isolated-profile GUI startup, and packaged functional smoke test after source acceptance.
