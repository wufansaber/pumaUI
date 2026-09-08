# Puma 9980 Implementation Roadmap

Source: `docs/UserManual-9980.pdf`, Puma 9980 v9.8.306 User Manual.

## Phase 1 - Recipe Lifecycle and Shared State

- [x] JSON-backed recipe, component, and history repository.
- [x] Open Inspection Recipe uses the shared repository.
- [x] File > New Inspection and Save Inspection / Save As.
- [x] Create derivative inspection with alignment-origin warning.
- [x] Import Puma or Brightfield recipe components.
- [x] Extract and insert recipe components.
- [x] Recipe History Log.
- [x] Persist recipe delete, recent-item state, and edits.
- [x] Unit tests for persistence, derivatives, components, and delete.

Manual coverage: 3.4, 3.5, 3.10.2, 3.10.3.

## Phase 2 - Complete Wafer Setup

- [x] Manual wafer alignment using stored recipe sites.
- [x] Manual wafer registration after a simulated registration failure.
- [x] Temporary alignment option for subsequent wafers.
- [x] Partial die inspection.
- [x] Inner die definition and KLARF export options.
- [x] Review microscope optics settings.
- [x] Select and import defect data.
- [x] Connect Wafermap and Alignment results to the active recipe.

Manual coverage: 3.7 through 3.11.

## Phase 3 - Inspection Test Setup

- [x] Test selection, orientation, add/copy/delete, and mode selection.
- [x] Inspection and collection optics parameters.
- [x] Fourier filter training and advanced options.
- [x] Care Areas editor and group operations.
- [x] Light training and histogram.
- [x] Segmentation and single-die inspection.
- [x] Sample Plan and swath coverage.
- [x] Sensitivity algorithms, regions, and defect filters.
- [x] Save and validate tests into the active recipe.
- [x] Complete advanced Chapter 4 flows listed in `MANUAL_COVERAGE_MATRIX.md`.

Manual coverage: Chapter 4.

## Phase 4 - Lot Plan and Wafer Post Processing

- [x] Lot Plan, wafer/test assignment, repeats, and result transfer.
- [x] Ordered post-processing operation palette.
- [x] Venn, clustering, DSA, repeater, CAG, population, sampling, limits, and excursion settings.
- [x] Configuration templates and recipe persistence.
- [x] Complete every operation's detailed parameters, advanced sampling, and excursion rule editing.

Manual coverage: Chapters 5 and 6.

## Phase 5 - Setup Run, Inspection Run, and Review

- [x] Setup Run lot and wafer identifiers, snapshot review, pause, and abort.
- [x] Job queue and run log.
- [x] Results selection and recipe matching.
- [x] Review workspace: wafer map, defect grid, image gallery, charts, and summary.
- [x] Filters, analysis operations, image transfer, and result export simulation.
- [x] Complete Chapter 9 alternate paths and the remaining Chapter 10 review tools.

Manual coverage: Chapters 9 and 10.

## Phase 6 - System Utilities Core

- [x] Initialize Subsystems and Preventive Maintenance training workflow.
- [x] Run, Daily, Recipe History, and Flight log views.
- [x] Show Options and persisted SECS Equipment Constants.
- [x] Lot Summary and persisted Data Transfer queue with retry/delete/start/stop.
- [x] Auto Transfer fallback queues completed results when ILink is unavailable.
- [x] Delete Inspections, Send Lots, Rename Lot, and Click and Mark configuration.

Manual coverage: Chapter 12.2.1-12.2.5, 12.3.1, 12.4.10, and existing 12.4.4/12.4.9/12.4.11 simulator portions.

## Phase 7 - Design Based Binning

- [x] DBB server/status model and recipe enablement.
- [x] RDF metadata and registration workflow, including all three A2D paths.
- [x] Core DBC examples/bins, DBC/DBG/design attributes, sampling, deterministic runtime, and Review Design tab.
- [x] Dedicated five-pane DBB View, visual Clip Gallery, classifier/folder/chart panes, and Analysis Toolbox sampling integration.
- [ ] Production RDF/DBC import and Design Services transfer, full registration viewers, and complete POI/classifier library editor.

Manual coverage: Chapter 8.

## Phase 8 - Sizing

- [x] SST setup and sizing result/reference data workflow.
- [x] Maps, scatter plots, histograms, cut lines, and defect sets.
- [x] Sizing recipe export/import and lot-result consolidation.

Completed with a persistent offline SST simulator, tool-side sizing setup, run/review integration, 24 focused tests, and native Windows visual QA. Production SEM/tool acquisition and external overlay services are intentionally outside the simulator.

Manual coverage: Chapter 11.

## Phase 9 - Remaining System Utilities

- [x] ERC Manager and remaining recipe/result cleanup utilities.
- [x] Job/substrate/carrier management and user/security administration.
- [x] Signal Tower, indicator lights, E116 EPT, logging, backup/restore, disk, and tool configuration.

Completed with prerequisite-gated job controls, persisted local administration state, hashed credentials, and safe simulator-only SECS, cleanup, backup, and disk operations. Native Windows visual QA covers the densest administration dialogs.

Manual coverage: remaining Chapter 12 items.

## Phase 10 - XP Offline and GDS2CA

- [x] AutoDerivative, AutoLearn, RDS, and Recipe Comparator.
- [x] GDS2CA converter, registration/rescaling, and CAG output.

Completed as a persistent offline simulator with 28 focused tests and native Windows visual QA. Live factory AutoLearn/RDS services, proprietary CAGDS polygon decoding, camera acquisition, and stage movement remain external integration boundaries.

Manual coverage: Chapters 13 and 14.

## Phase 11 - Productization

- [x] Cross-module validation and state-machine tests for the implemented core flow.
- [x] Keyboard shortcuts, core error states, alarms, and confirmation paths for implemented workflows.
- [x] Native-font visual QA at desktop and minimum supported resolutions for implemented complex surfaces.
- [x] User-data migration and recovery for corrupt JSON.
- [x] PyInstaller Windows EXE build and isolated-user-data smoke test.
- [x] Operator documentation and source-mode acceptance checklist.
- [x] Windows release package and packaged-app functional smoke evidence.
- [ ] Separate clean-machine Windows launch before production distribution.

The prototype simulates equipment behavior. It must not control real wafer handling,
stage motion, optics, or inspection hardware without a separately reviewed hardware
adapter and safety interlock layer.
