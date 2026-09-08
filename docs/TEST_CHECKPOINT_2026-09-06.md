# PumaUI Test Checkpoint - 2026-09-06

## Scope

- Re-audited the complete Puma 9980 revision AA table of contents instead of treating Chapters 3-10 as the whole product scope.
- Added explicit coverage gaps for Design Based Binning, Sizing, remaining System Utilities, XP Offline Setup, and GDS2CA.
- Corrected native Windows Qt rendering in the visual QA scripts.
- Fixed Wafermap Image enablement, Wafermap/Edit Map readability, three-port Wafer Handling layout, and narrow Review compression.
- Implemented the Chapter 12 System Utilities core described in `MANUAL_COVERAGE_MATRIX.md`.
- Implemented the remaining Chapter 12 administration workflows described in `MANUAL_COVERAGE_MATRIX.md`.
- Implemented the complete Chapter 11 Sizing/SST simulator workflow described in `MANUAL_COVERAGE_MATRIX.md`.
- Implemented the Chapter 13 XP Offline Setup and Chapter 14 GDS2CA simulator workflows described in `MANUAL_COVERAGE_MATRIX.md`.
- Cross-checked the supplied Puma 95XX/96XX Version 9.6 SP1 manual and completed Recipe Overview navigation, Inspection Properties/History Log access, and component status semantics without overriding later 9.8.306 behavior.
- Made the Navigation bar functional and routed Test overview headings and preview images to their documented editors/enlarged views.
- Corrected the Wafer Map site-selection geometry so the die grid is centered, fills the wafer, is clipped at the wafer edge, and uses valid grid intersections for all three sites.

## Verification

- `python -m compileall -q puma_ui`: passed.
- `python -m unittest discover -s tests -q`: 331 tests passed.
- Focused Wafer Setup tests: 46 passed.
- Focused System Utilities tests: 14 passed.
- Focused advanced System Administration tests: 22 passed.
- Focused Design Based Binning tests: 22 passed.
- Focused Sizing tests: 24 passed.
- Focused XP Offline Setup and GDS2CA tests: 29 passed.
- Packaged-smoke tests: 2 passed.
- Native-font screenshots passed for main/wafer/review tools plus Equipment Constants, Data Transfer Queue, Lot Summary, Design Registration, DBB/DBC Setup, Review Design, five-pane DBB View, DBB Analysis Toolbox, SST scatter workspace, Sizing Recipe, Sizing Histogram, Control Job Management, User Administration, Signal Tower, Disk Admin, XP Recipe Generator, Recipe Comparator, RDS Manager, GDS2CA Converter, and CAG Editor.
- PyInstaller Windows build passed after excluding conflicting Poppler ICU DLLs from the Qt bundle.
- Final packaged GUI remained running during a 10-second isolated-profile startup check.
- Packaged functional smoke passed recipe save/reload, valid run setup, one-wafer run, result save/reload, and result review.

## Current Boundaries

- No physical wafer handling, stage, optics, inspection, factory host, DBB server, or Analysis System connection is opened.
- Production DBB file/server tools remain a scheduled implementation phase.
- Factory AutoLearn/RDS services and proprietary binary CAGDS geometry decoding remain external integration boundaries.
- SECS host commands, carrier/substrate handling, security integration, cleanup, backup, restore, and disk maintenance remain deterministic local simulations and never operate real equipment, host services, or system files.
- Sizing acquisition, SEM integration, and production KLARF overlay services are represented by deterministic local simulation only.
- A separate clean Windows machine launch remains a release-environment check; local source and packaged acceptance are complete.
