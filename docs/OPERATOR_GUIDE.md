# Puma 9980 UI Simulator Operator Guide

This application simulates the Puma 9980 software workflow for training and UI evaluation. It does not communicate with inspection hardware.

## Start the application

Run `Puma9980UI.exe` from the release folder. User recipes, queue entries, and simulated lot results are stored in `%LOCALAPPDATA%\Puma9980UI\recipes.json`.

If the JSON store cannot be read, the application preserves it as `recipes.corrupt-<timestamp>-<id>.json` and starts with a clean store.

## Recipe and wafer setup

1. Open or create an inspection recipe.
2. Configure Wafer Properties, Alignment, and Wafermap.
3. Define and validate at least one inspection test.
4. Assign the test to wafer slots in Lot Plan.
5. Optionally enable and order Wafer Post Processing operations.
6. Save the inspection recipe.

Use `Set Up > Wafer` for Wafer Properties, Alignment, Wafermap, Registration Site, Design Registration, DBC Setup, and defect-data attachment. Wafermap follows the manual order: Die Values, Scribe Lines, Edit Map, Reticle Size, Adjust Die Corner, then Finish. The simulator enforces alignment, die-pattern, reticle, and design-registration prerequisites before dependent pages become available.

Home returns to the Main Menu, whose Set Up Inspection, Run Inspection, Review Results, and Utilities commands match the manual's primary workflows. Setup returns to the active recipe's Recipe Overview and restores the left setup panel. End at the bottom of that panel also returns to the Main Menu; use `File > Exit` to close the application.

The left setup panel opens the primary workflow in the central workspace. Use the top navigation strip to move between major Wafer and Test pages or to return with Back, Forward, Home, and Setup. The Wafer button expands an inline horizontal drawer for Wafer Properties, Alignment, Wafer Map, and Select Defect Data; selecting a destination closes the drawer. Short parameter choices, confirmations, Save, Recipe Generation, warnings, and enlarged previews remain dialogs.

Use the Wafer Handling toolbar button to map a carrier, choose one of 25 slots on up to three displayed load ports, load/unload a wafer, align it, and change orientation. Laser Power Sensitive and Dark Wafer controls are available from Wafer Properties and Wafer Handling.

## Inspection tests

Open `Set Up > Tests`. Add, copy, delete, rename, and orient tests in the test matrix. Configure Inspection Optics, Collection Optics, Fourier Filter, Care Areas, Light Training, Segmentation, Sample Plan, Sensitivity, Defect Filters, iDO/NEF classifiers, and Single Die Inspection from each test row. A test must pass validation before it can be assigned to a Lot Plan.

## Lot Plan and post processing

Open Lot Plan from the left setup panel. Assign tests to any of 25 wafer slots, define test and unload repeats, choose backups/transfers, and protect the plan. A protected repeating plan exposes only Repeat Count while running.

Open Wafer Post Processing to enable and order Venn, Clustering, DSA/DSA+, Repeater, CAG, Spatial Population, Population Arbitration, Precision/Diversity Sampling, Defect Limits, and Excursion Reduction. Save complete schemes or selected operations as templates.

## Run one wafer

1. Select `Set Up > Setup Run > Run One Wafer` or press `F9`.
2. Enter a Lot ID and optional Wafer ID.
3. Select tests and optional repeat, transfer, backup, and Instant Review settings.
4. Click `Run One Wafer`.
5. Use `Pause` / `Continue`, `Snapshot Review`, or `Cancel...` while the simulated run is active.

Completed and aborted run results are saved to the local data store. Instant Review opens the completed result automatically.

## Inspection queue

Open `Run > Inspection Queue` or press `Ctrl+Q`. Add a job, select an inspection, enter cassette/material information, choose slots, and enter a Lot ID. Jobs can be started, cancelled, removed, viewed, or purged. Run logs remain attached to completed queue entries.

## Review results

Open `Run > Review Wafer` or press `F10`, then select a lot result. The Review workspace contains a Wafer Map, Defect Properties Grid, Image Gallery, Chart, and Summary.

- Use Left/Right to navigate defects.
- Press `M` to mark the current defect.
- Press `Ctrl+F` to filter by test, class code, signal, size, mark, or review state.
- Configure analysis operations with `Analysis...`.
- Simulate image or lot transfer with `Send Images` and `Send Lot`.
- Press `Ctrl+E` to export the visible defect set as KLARF text.

Use the synchronized map, grid, gallery, chart, folders, summaries, Filter and Analysis pipeline, classification, image grabbing, transfer, and result export tools. Imported KLARF results can be matched to a recipe and adjusted by defect or die-origin offsets.

## DBB and sizing

After Alignment, Reticle Qualification, and Pixel Perfect are ready, use `Set Up > Wafer > Design Registration`, then DBC Setup and Design Based Binning. Open `Review > DBB View...` for the five-pane Wafer/Design map, visual Clip Gallery, DBC Classifier, Defect Grid, Folder/Chart view, and Analysis Toolbox. Real RDF/DBC servers are not contacted.

Use `Set Up > Sizing...` to configure scale factors and cut lines. Use `Review > Sizing Setup Tool...` for reference-size import, maps, scatter plots, histograms, defect sets, XML recipe exchange, and lot consolidation. SEM acquisition is simulated.

## XP Offline Setup

1. Add at least one Registration Site to a valid Base Recipe.
2. Open `Set Up > Recipe Generation...`.
3. Select Base and optional Source recipes, add layers, choose Production, Hot Scan, or OSTS mode, and generate AutoLearn-Ready recipes.
4. Use `Tools > Manual Assist for AutoDerivative...` to configure or simulate AutoLearn completion/failure.
5. Use `Tools > Recipe Distribution System...` for local version, production-approval, and distribution records.
6. Use `Utilities > Recipe Comparator...` to load, compare, edit, and save Local/RDS recipes.

Use `Utilities > GDS2CA Converter...` to create a local Care Area component from CAGDS metadata plus Mapping/Config CSV files, or select Use Default Data. `Tools > CAG Editor...` assigns fixed or sequential CAG Codes from 1 through 32000. Proprietary binary polygon decoding and physical registration remain external boundaries.

## System utilities

`Utilities` contains subsystem initialization, preventive maintenance, logs, options, Equipment Constants, inspection cleanup, ERC, Send Lots, and Rename Lot. `Tools` contains job/substrate/carrier management, data transfer, SECS simulation, security, preferences, Signal Tower, load-port indicators, E116, logging, backup/archive/restore, Disk Admin, and remote tool configuration. Cleanup, backup, host, and equipment commands only update local simulator state.

## Safety and scope

All wafer motion, optics, inspection, alarms, transfer, and recovery behavior is simulated. Do not connect this application to production equipment without a separately reviewed hardware adapter, equipment-state model, safety interlocks, and factory integration controls.
