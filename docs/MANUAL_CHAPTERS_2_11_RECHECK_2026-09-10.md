# Puma 9980 Manual Chapters 2-11 Recheck

Date: 2026-09-10

Historical simulator recheck record. Third-party reference documents and their translated copies have been removed from the repository.

## Method

- Read and indexed all 10 chapter files from Chapter 2 through Chapter 11: 11,384 lines and 319 numbered section/subsection headings.
- Checked each numbered heading against the implemented entry point, visible controls, action-time prerequisites, state persistence, and focused Qt tests.
- Ran the operator workflow with real Qt mouse and keyboard events from application startup through recipe save.
- Rendered the main Chapter 3-6 and Chapter 9-11 workspaces at fixed desktop sizes and visually checked clipping, panel proportions, and control visibility.
- Kept physical stage/camera/handler behavior, factory-host communication, proprietary classifiers, and Design Services outside the simulator compliance claim.

## Result By Chapter

| Chapter | Result | Recheck conclusion |
|---|---|---|
| 2 System Overview | PASS in simulator scope | Startup opens Home; Home, Setup, Run, Review and Utilities routes are distinct; navigation, toolbar visibility, alarms, E84, status symbols and Daily Log paths are present. Physical safety circuits and equipment diagnostics remain hardware boundaries. |
| 3 Wafer Setup | PASS in simulator scope | Existing recipes reuse stored Alignment/Wafer Map/Test data; new-recipe wafer properties, three-port handling, loaded-wafer Alignment, dual-screen Image Display, centered/clipped die map and defect-data paths are exercised. Physical motion and camera acquisition remain simulated. |
| 4 Inspection Setup | PASS in simulator scope | Tests, Fourier, Care Areas, Active Region, Light Training, Segmentation, SDI, Sample Plan and Sensitivity workflows are present. Fourier training is required before Light Training only when an enabled channel selects `Use Fourier Filter`. |
| 5 Lot Plan | PASS after correction | The 25-slot matrix, row/column assignment, Repeat Count, Protect, backup and cache transfer persist. `Unload Wafer in Repeat Mode` was moved from the main panel into the manual-defined `Advanced...` dialog. |
| 6 Wafer Post Processing | PASS in simulator scope | Ordered operations, property pages, templates, Venn, clustering, DSA, repeater, CAG, spatial population, arbitration, sampling, defect limits and excursion reduction are executable against deterministic local results. External databases and optical acquisition remain boundaries. |
| 7 Inline Defect Organizer | PASS for Puma-side functions | Feature-vector collection, classifier attachment/version checks, rough code assignment and Review filtering/rerun are present. IMPACT XP classifier creation and optimization are external-system functions and are not claimed as Puma simulator functions. |
| 8 Design Based Binning | PASS for local simulator workflow; external boundary remains | RDF metadata, registration strategies, DBC/DBG setup, sampling and five-pane DBB Review are present. Proprietary RDF/DBC decoding, Design Services transfer and production classifier distribution require external services. |
| 9 Inspection Run | PASS in simulator scope | Run One Wafer, repeat, transfer prerequisites, sensitivity collection, live status, Snapshot Review, pause/abort, queue, job setup and logs persist and execute. SECS/ILink and equipment motion remain simulated. |
| 10 Inspection Review | PASS in simulator scope | The four resizable panes, compact toolbar, filtering, marking, image gallery, charts, result utilities, KLARF, offsets, optics, DBB, OSTS and Sensitivity Tuner routes are exercised. Physical review optics and network transfer remain boundaries. |
| 11 Defect Sizing | PASS after correction | Lot Result follows Select Result -> Choose Wafer -> Choose Test; KLARF supports Source -> Lot -> Wafer -> Test -> Size Field, with Back/Next/Finished and direct Finished from the source page. SST exposes the documented common toolbar actions. `View > Properties`, toolbar `Properties`, and `Mappings > Properties` open Target/Reference/Overlay pages with editable reference sizes and overlay radius. SEM connectivity remains external. |

## Corrections Found By This Recheck

1. The operator walkthrough still assumed Recipe Overview was the startup page. It now verifies `Home -> Setup -> Recipe Overview` before selecting a recipe.
2. Lot Plan lacked the Chapter 5 `Advanced...` interaction. It now owns the Repeat Mode unload setting in a separate Advanced Options dialog.
3. Chapter 11 lacked the documented MapDlg Properties entry and three-page workflow. All three entry paths and Target/Reference/Overlay pages are now implemented.
4. Chapter 11 Lot Result selection was functionally compressed into one page. It now follows the manual's wafer/test selection order.
5. Chapter 11 KLARF options were functionally compressed into one page. The optional Lot/Wafer/Test association and Size Field pages now follow the manual sequence.

## Verification

- 585 automated tests passed across 28 isolated test files; 0 failed.
- All 207 discovered operator dialogs/main windows opened and fit within 1920 x 1080.
- The event-driven operator walkthrough completed 90 mouse/keyboard checkpoints; 0 failed.
- Chapter 5 and Chapter 11 correction screenshots rendered successfully, including Lot Plan Advanced Options and MapDlg Overlay Properties.

## Acceptance Rule

`PASS in simulator scope` means the operator-visible workflow, validation, local persistence and deterministic result behavior match the manual. It does not mean that this desktop simulator controls Puma hardware or replaces the named external KLA services.
