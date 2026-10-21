# Puma 9980 UI Prototype

这是一个基于 Python 和 Qt 的晶圆检测机台模拟软件，用于操作培训、流程演示和界面验证。软件通过本地模拟数据展示配方设置、晶圆操作、检测运行与结果复核，不连接真实检测硬件。

## 功能介绍

- **配方管理**：新建、打开、复制、保存和导入配方，管理组件、历史记录与有效性状态。
- **晶圆设置与搬运**：模拟三组装载端口、25 槽晶圆盒、装卸片、对准、方向设置、晶圆图和 Die 布局。
- **检测测试配置**：配置多测试及三通道光学参数，支持 Fourier Filter、Light Training、Sensitivity 和缺陷过滤。
- **关注区设置**：通过 Die View 编辑 CA、DCA、ACA 与派生区域，设置各区域独立参数，支持 Fill、No Fill、尺寸测量和 MacroView 显示。
- **视野控制**：通过方向按钮控制模拟平台移动，结合缩放查看芯片图像与关注区叠加。
- **采样与分类**：配置晶圆环带、边缘 Die、Die 行采样及阈值模式，使用 NEF 示例分类器和多层分支树演示分类流程。
- **批次与检测运行**：配置 Lot Plan、测试分配和晶圆后处理，模拟单片与队列运行、扫描进度、暂停、继续和终止。
- **结果复核**：在主界面联动显示 Wafer Map、缺陷属性表格、Image Gallery 和 Chart Pane，支持按行选择缺陷、筛选、标记和分类。
- **数据保存与导出**：保存配方、检测结果及配置，支持结果重载、KLARF 导出和本地传输队列模拟。
- **扩展演示**：提供设计分箱、Sizing、离线配方处理和系统维护界面，以及可用于演示的配方、缺陷数据和分类器。
- **离线启动密钥**：采用 6 位数字密钥，每 10 天切换一次；管理员使用独立密钥生成器获取对应日期的密钥。

操作步骤见 [项目操作指南](docs/OPERATOR_GUIDE.md)。本仓库不分发第三方内部手册、翻译副本或手册截图。

## Implemented

- Phase 1 recipe lifecycle and shared state:
  - Recipes, recent-item flags, component bundles, and history are persisted in a local JSON repository.
  - `File > New Inspection`, `Save Inspection`, and `Save Inspection As...` are connected to the active recipe.
  - `Recipe Generation` supports new recipes, copies, derivatives, imports, component extraction/insertion, and history review.
  - Derivative recipes retain source geometry and tests while requiring alignment-origin reselection.
  - `Edit > Extract Component` and `Edit > Insert Component` follow the manual component workflow.
  - Extract Component prompts to save unsaved recipes, offers an editable list of existing component filenames, and the bundled validation recipe includes a ready-to-insert `PUMA_9980_FULL_SETUP` component file.
  - `View > Recipe History` displays saved recipe events.
- Classic Windows-style main window, menu bar, toolbar, navigation strip, left setup menu, and status bar.
- Main toolbar button groups from the user manual: Standard toolbar, Optics toolbar, and Setup toolbar buttons with hover descriptions.
- 1920x1080-friendly sizing: the main window opens around 1600x900 and the recipe dialog around 1180x800, while still adapting to smaller screens.
- Compact 10px UI font with taller 24px input and combo-box controls to prevent clipped text.
- Setup menu entries: Select Inspection, Wafer, Tests, Lot Plan, Wafer Post Processing, Setup Run, Save Inspection, Recipe Generation, and End.
- Always-visible Recipe Overview area with Recipe Properties, Wafer Layout, status dots, and a wafer map placeholder.
- Recipe Overview sections use clickable arrow headers to expand or hide details; Recipe Properties and Wafer Layout start collapsed like the manual.
- Underlined Recipe Overview headings open their corresponding setup view, while component status icons distinguish valid, nonoptimal, and invalid data.
- The Navigation bar records visited setup views, supports Back/Forward, shows the current hierarchy, and provides a Navigate menu for direct access to common setup pages.
- Test overview headings route to the documented destination: Fourier Filter, Light Level, Sensitivity/Defect Filters, Care Areas, and Sample Plan open their corresponding editor rather than only the Tests summary.
- `File > Inspection Properties...` and the Recipe Overview heading open the editable recipe identity/status dialog; its History Log action opens the recipe event history.
- Recipe Properties expands into Inspection Properties, Creation Properties, and Load/Save Status columns matching the manual layout.
- Expanded Wafer Layout content with Wafer Properties, Alignment scores, Registration Sites, Die Layout, Die Corner preview, Wafer Map preview, and Design Files.
- In Wafer Layout, click the Die Corner zoom icon to open Low Mag / High Mag enlarged die-corner image preview.
- In Wafer Layout, click the Wafer Map zoom icon to open an enlarged high-resolution wafer map preview.
- Added the Test 1 overview section with Test Properties, Inspection Optics, Collection Optics, Illumination Level Optimization, Fourier Filter, Light Level, Sensitivity, Defect Filters, Care Areas, and Sample Plan modules.
- Care Area and Sample Plan preview images can be clicked to open enlarged views.
- Recipe Overview is scrollable so Recipe Properties, Wafer Layout, and Test 1 can be expanded without losing lower content.
- First operation step: Selecting an Inspection Recipe.
  - Click `Select Inspection` on the left setup menu.
  - The `Open Inspection Recipe` dialog appears.
  - Click `Search` to display the `Find` box; typing filters recipes by name, device, step, or path, and `Clear` restores the current recipe list.
  - Switch between `Local Recipes` and `Recent Items`.
  - `Local Recipes` shows all local recipes, while `Recent Items` shows only recently used recipes.
  - Select a Device and Step to refresh the inspection table with matching recipes.
  - Select Device `_180` or `9.4.102`, Step `Deep`, then select a recipe from the inspection table.
  - Click `Add` to create a new place shortcut for the selected Device/Step folder, rename it in `Add New Place`, and use the new folder button for quick access.
  - Click `Remove` to delete the selected place shortcut.
  - The bottom fields show and allow editing of Inspection, Device ID, Step ID, State, Path, Recipe Filter, and Recipe Type.
  - For invalid recipes such as `Incomplete` or `Non Optimal`, click `More` beside State to view the full recipe status, attributes, and path.
  - Click the magnifying-glass button beside `Path` to display/open the selected recipe folder path.
  - Use the `Recipe Filter` drop-down to show `All Recipes`, `Valid Recipes`, or `Invalid Recipes`.
  - Click `Add` to save the current bottom-field values into the `Inspections` table.
  - Click `Open` to load the selected or edited recipe back into the main status bar and main-window Recipe Properties.
  - Click the top `Delete` button, then choose `Delete Now` in the `Delete Confirmation` dialog to move the selected recipe to the trash, or `Cancel` to keep it.
  - Right-click a recipe row to open Recipe Operations: Open Recipe, Open in Explorer, Refresh, and Delete; Save Recipe appears only when the selected recipe has unsaved edits, and Clear Recent Items appears only in Recent Items.
  - Click the `Configure header columns` button beside the inspection table header to open the recipe attributes menu; checked attributes are displayed as columns, and `Reset Columns` restores the default column set.
- Open Inspection Recipe wafer display from User Manual page 118.
  - Click `Show Wafer` to expand the right-side wafer operations and load-port area inside the Open Inspection Recipe dialog.
  - Use `Show Load Ports: 1 / 2 / 3` in the expanded Open Inspection Recipe dialog to choose how many load ports are displayed, up to three.
  - Wafer Load and Load & Align run as non-blocking 10-second simulations with countdown, progress, wafer-center/alignment phases, operator abort, timeout, transfer-exception simulation, and retry-safe state recovery.
- Wafer Properties flow from User Manual pages 125-130.
  - Click `Wafer` on the left setup menu to open the Wafer menu.
  - Click `Wafer Properties` to open the Wafer Properties dialog.
  - Edit Orientation, Type, Laser Power Sensitive settings, layer selection, and Dark Wafer Auto Focus settings.
  - Use the Laser Power Factor slider to adjust the current J/cm^2 value, or type the value directly.
  - Use the Wafer Darkness Level slider to choose between Dark and Darkest.
  - Click `Edit Settings...` to open the Edit Layer Database dialog.
  - Click `OK` to update the main-window Wafer Layout summary.
- Wafermap setup view.
  - Click `Set Up > Wafer > Wafermap` from the main menu, or click `Wafer` on the left setup menu and then click `Wafer Map`.
  - The Wafermap View opens with the wafer canvas, setup buttons, die pitch, reticle size, wafer statistics, and legend.
  - Click `Die Values` to open `Specify Die Values`; choose `Use Wafer Map` or `Use Die Pitch`, where selecting die pitch enables X/Y pitch fields.
  - The site-selection view draws a die-pitch grid centered on the wafer and clipped to its circular boundary; site 2 is one die diagonally from site 1, while site 3 is a lowermost-right valid grid intersection.
  - `Use Die Pitch` validates that both X and Y are at least 1200 um before continuing.
  - After clicking `OK`, if a die pattern already exists, choose `Yes` in the warning to continue redefining it or `No` to keep it.
  - When `Use Wafer Map` is selected, click `OK` to open the site selection view, then use `Mark Site >>` to select three low-mag sites followed by three high-mag sites.
  - When `Use Die Pitch` is selected, the site selection view requires the first low-mag site and three high-mag sites.
  - Click `Cancel` in the site selection view to confirm discarding new die values, or click `Finish` to save the marked positions.
  - After `Finish`, the Wafermap View is redrawn with a die grid, origin die, reticle outline, die pitch, estimated number of die, and wafer diameter.
  - Click `Scribe Lines` to mark the upper-left corner of the bottom-right die and the lower-right corner of the diagonally opposite upper-left die; when both are marked, `Scribe Lines setup Completed` appears and `Finish` returns to the Wafermap menu.
  - After `Scribe Lines` is completed, the Wafermap View shows the scribe line size and overlays excluded scribe-line areas on the wafermap.
  - Click `Edit Map` to toggle, add, remove, or set origin die on the wafermap, configure edge exclusion, remove outside die, add inside die, and allow partial die.
  - In `Edit Map`, left-click a die to apply the current selection mode; click and drag to apply the selection mode to a rectangular group of die.
  - Click `Finish` in `Edit Map` to redraw the Wafermap View with invalid die, origin die, valid die count, and wafer diameter retained.
  - Click `Reticle Size` to open the Reticle Qualification/Definition view, enable reticle qualification, enter Width x Height die counts, click a wafer die as the reference die, and finish to draw reticle fields on the wafermap.
  - Click `Cancel` in `Reticle Size` to confirm discarding reticle layout changes.
  - Click `Adjust Die Corner` to show the imported-component compatibility alert or die-values alert, choose Shift Die Corner or Change Die Corner, mark a new die corner, and finish to redraw the wafermap with the adjusted corner.
  - After `Finish` in Adjust Die Corner, the test geometry notification appears with `More >>` / `<< Less`, `Write to File`, and `OK`; Change Die Corner then asks for commit confirmation.
  - `Define Inner Die` stores the row/column subdivision used for inner-die inspection.
  - `Advanced...` selects Recipe Die or Inner Die KLARF reporting and transfer orientation.
- Image Display Window from the Wafer Alignment flow.
  - Click `Wafer` on the left setup menu, then click `Alignment`.
  - Click `Image Display` in the Alignment dialog, or click `View > Image Display`, to open the Image Display Window.
  - Use the relative motion buttons to update X/Y stage position, and click `Acquire` to add a current image entry.
  - Click `Advanced Optics...` to open the Advanced Inspection Optics Settings dialog.
  - Use `Current Image` to select images, step through images with previous/next buttons or keyboard left/right, start/stop automatic cycling, and open `Cycle Image Setup` with the `...` button.
- Automatic Alignment Site Selection from User Manual pages 149-150.
  - Click `Wafer` on the left setup menu, then click `Alignment`.
  - Click `Auto Site Selection`; if valid alignment sites are already defined, click `Yes` in `Select Alignment Sites` to proceed.
  - Set Pixel Size, Channel Used for Alignment, optics source, Primary Production Test, and Keep Old Wafer Center in `Alignment Parameters`.
  - Click `Advanced Optics...` to open `Advanced Inspection Optics Settings`, then click `OK` to continue to Select Die Corner View.
  - Click `Settings...` in the Alignment Order area to open `Alignment Settings`, where `High Precision Alignment` can be enabled.
  - Click `Advanced...` in Select Die Corner View to open `Advanced Inspection Optics Settings`.
  - Use `Mark Die Corner >>` to mark the first die corner, mark the street point, and then mark the second die corner.
  - Use `Ctrl+click` in the die-corner view to snap to the nearest point/corner, or `<< Prev` to reselect the previous step.
  - After the second die corner is marked, target quality scores are filled and Auto Site Selection begins.
  - Click `Finish` to close the selection view and return to the Alignment menu.
- Alignment qualification and relearn flow.
  - Click `Qualify with Test Optics` in the Alignment menu to open `Alignment Parameters`.
  - Select the `Re-learn` check box to reteach alignment, then click `OK`.
  - Confirm the follow-up prompt with `Yes` to retain the new alignment data.
  - `Manual Alignment` reuses saved alignment sites, permits site correction, and optionally stores temporary alignment parameters for remaining wafers in the lot.
  - `Align Wafer` includes a simulator-only registration-failure path that opens manual die-origin selection and records successful manual registration.
- Inspection Tests setup.
  - After wafer alignment and wafermap definition, click `Tests` to open the Chapter 4 test matrix.
  - Add up to 50 tests, select Random or Blank-wafer Test mode, rename tests, and change orientation with rotate/keep/cancel confirmation.
  - Right-click the matrix to copy, paste, or delete the current test.
  - Configure focus, coverage, image/feature saving, Inspection Pixel Size, Sample Rate, speed, incident polarization, incidence angle, and laser power density per test.
  - Configure enable, polarization, light level, IRIS, imaging mode, and Fourier Filter use for all three collection channels.
  - Test definitions are stored in the active recipe and persist when the recipe is saved.
  - Configure Fourier Filter training, Care Areas, Illumination Level Optimization, Segmentation, Sample Plan, Sensitivity algorithms, and Defect Filters.
  - Each configured test is validated before it can participate in downstream run setup.
- Lot Plan and Wafer Post Processing.
  - Assign one or more tests to 25 wafer slots, configure repeat counts, protection, backup, result caching, transfer hosts, and load-port behavior.
  - Enable and order Venn, Multi-Test Merge, Clustering, Defect Source Analysis, Repeater Analysis, CAG Code Assignment, Spatial Population, Population Arbitration, Sampling, Defect Limits, and Excursion Reduction.
  - Save whole-scheme or selected-operation WPP templates inside the recipe.
- Design Based Binning core workflow.
  - DBB status, Alignment/Reticle/Pixel Perfect prerequisite gating, RDF metadata, and SemiAutomatic/Manual/Offsets-and-Scales registration are persisted with the recipe.
  - Configure DBC/DBG, DCI/PCI/design attributes, clip transfer, and bounded DBB sampling; simulated runs add deterministic design attributes and Review exposes a Design tab.
  - Open `Review > DBB View...` for the five-pane Wafer/Design, Clip Gallery, DBC Classifier, Defect Grid, and Folder/Chart workspace; run offline DBB analysis and save updated attributes/sampling back to the lot result.
  - RDF/DBC server access and physical W2D registration remain explicit simulator boundaries.
- System Utilities core workflow.
  - Initialize Subsystems, Preventive Maintenance, four log views, Show Options, Equipment Constants, Lot Summary, Delete Inspections, Send/Rename Lot, and Click and Mark configuration are available from the manual menu locations.
  - Data Transfer includes a read-only configuration summary, persistent retry/delete queue, startup/shutdown state, and automatic queuing when simulated ILink is unavailable.
  - ERC cleanup, Control/Process Jobs, Substrate Tracking, Carrier Management, Security users/groups, Signal Tower, load-port indicators, E116 EPT, log settings, Backup/Archive/Restore, Disk Admin, Tools Configuration, and SECS operation surfaces complete the Chapter 12 administration flow.
  - Hardware, host communication, Windows security, and filesystem maintenance actions remain deterministic local simulations.
- Sizing and Sizing Setup Tool workflow.
  - Use `Set Up > Sizing...` to enable sizing and sizing-data collection, edit the six documented scale factors/cut lines, or import an exported sizing XML recipe.
  - Simulated inspection runs store the raw sizing properties only when collection is enabled; Review can filter defects by the applied scale-factor group.
  - Open `Review > Sizing Setup Tool...` or `Tools > Sizing Setup Tool...` to load lot results and KLARF reference sets, edit/import reference sizes, configure maps and overlay radius, and transfer reference sizes.
  - The SST scatter plot supports non-zero filtering, computed-reference comparison, category highlighting, movable legends, coordinate tooltips, and double-click reference-size editing.
  - Special Case, Size, and Planar histograms provide cut-line controls, out-of-graph display, and cumulative density curves.
  - Save active/all defect sets, export/import sizing recipe XML, remove defect sets with associated maps, and consolidate all wafer results from one lot with source tracking.
- XP Offline Setup and GDS2CA workflow.
  - Define Registration Sites, validate Base Recipes, generate layered AutoLearn-Ready recipes in Production, Hot Scan, or OSTS mode, and simulate Manual Assist outcomes.
  - Check recipes into the local RDS simulator with version/approval history, distribute them to named tools, and compare/edit multiple Local or RDS recipes in aligned Recipes and Tests grids.
  - Convert CAGDS metadata with Mapping/Config CSV or Default Data, import generated Care Area groups, calculate two-site registration and scaling, prune out-of-die areas, and assign CAG Codes from 1 to 32000.
- Inspection Run and Results Review.
  - `Run One Wafer` supports Lot/Wafer IDs, test selection, repeat runs, backup, auto-transfer, patch/hi-res transfer, and Instant Review.
  - Run Status simulates progress and defect collection, with Pause/Continue, Snapshot Review, and scoped abort options.
  - Inspection Job Queue supports recipe/material/cassette/slot setup, start, cancel, remove, purge, and stored run logs.
  - Results Review provides synchronized Wafer Map, Defect Properties Grid, Image Gallery, class-code chart, and summary panes.
  - Filter by test, class code, signal, size, mark, or review state; apply analysis operations; simulate transfer; export filtered KLARF data.
  - Recipes, job queue entries, and simulated lot results persist in the shared JSON store, with automatic corrupt-file backup and schema migration.
- Select Defect Data flow.
  - Click `Wafer > Select Defect Data` to attach a local Lot Result or import and convert a KLARF file for Setup-Review care-area work.
  - Attached defect metadata is stored with the active recipe and can be detached before saving.
- Alignment Imaging Mode and DF optics selection.
  - Click `Select Sites` in the Alignment dialog to open `Alignment Imaging Mode`.
  - If valid alignment sites already exist, confirm the `Select Alignment Sites` warning to proceed with reselection for the current or derivative inspection.
  - Click `DF` or `BF` to open `Alignment Parameters`.
  - Choose Pixel Size and Channel Used for Alignment, or click `Advanced Optics...` to edit detailed optics settings.
  - `BF` opens `BF Alignment Parameters`, where Standard Dual Magnification or Single Magnification can be selected, and low/high magnification Pixel Size, Focus Offset, Aperture, and Advanced Settings can be configured.
  - Click `OK` to open `Select Alignment Sites`.
  - Click `Settings...` in the Select Alignment Sites Orientation area to open `Alignment Settings` and enable `High Precision Alignment`.
  - Use the mouse, keyboard arrow keys, or `Ctrl+click` snap behavior to drive the stage crosshair inside the blue alignment box.
  - Use the Focus Offset field, `F7`, or `F8` to adjust focus while selecting sites.
  - Click `Image Display...` to view simulated wafer cross-mark images, or click `Acquire Sim Image` to generate a synthetic cross-mark capture at the current stage position.
  - Click `Mark Site >>` to store or reselect the current site, click `Next >>` to keep site #1 and proceed to site #2, and click `<< Prev` to return to a previous site for adjustment.
  - Select the same high-contrast area on an adjacent die at least 200 um to the right for site #2, then click `Mark Site >>`.
  - Click `Align` to scan and record the site coordinates/images, or click `Finish` after site #2 to proceed and return to the Alignment menu.
  - After site selection for a derivative inspection, `Derived Site Selection` appears; click `OK` to select the die origin, then use `Low Mag Die Corner Image` to reselect the old inspection die origin, click `Mark Site`, and click `Finish`.
- Wafer Handling dialog from User Manual pages 131-134.
  - Click the main toolbar `Wafer Handling` button to open it from the main window.
  - Select Port 1 or Port 2, load or unload carriers, select mapped wafer slots, load/unload wafers, load and align, align, change orientation, and adjust laser/dark-wafer settings.
- Recipe Overview Configure dialog.
  - Click `Configure` in the Recipe Overview area to open `Select Visible Recipe Parameters`.
  - Check or uncheck parameters to control which groups and rows are shown in Recipe Overview.
  - Click `OK` to apply, `Cancel` to discard, or `Reset` to restore default visibility.

## Run

Open this folder in VSCode, select the conda environment `pumaui`, then run:

```powershell
conda activate pumaui
pip install PySide6
python main.py
```

If your environment already uses PyQt5, it can run directly as well. The code auto-detects PySide6 first, then PyQt5.

The application requires a six-digit offline startup key. Keys change every ten
calendar days. Administrators can open the key generator with:

```powershell
python key_generator.py
```

To print the key for a specific date without opening the GUI:

```powershell
python key_generator.py --date 2026-09-15
```

## Code Layout

```text
main.py
puma_ui/
  app.py
  config.py
  main_window.py
  qt_compat.py
  widgets.py
  modules/
    configure_overview/
      dialog.py
    header_columns/
      dialog.py
    image_display/
      dialog.py
    wafer_alignment/
      dialogs.py
    wafer_map/
      dialog.py
    select_inspection/
      dialog.py
    show_wafer/
      panel.py
    wafer_handling/
      dialog.py
    wafer_properties/
      dialogs.py
    inspection_tests/
    lot_plan/
    wafer_post_processing/
    run_control/
    results_review/
    sizing/
    system_status/
    xp_offline/
```

- `main.py`: small startup entry only.
- `puma_ui/main_window.py`: main Puma 9980 window and left setup-menu wiring.
- `puma_ui/widgets.py`: reusable classic UI widgets, status dots, wafer drawings, and section boxes.
- `puma_ui/modules/configure_overview/dialog.py`: Select Visible Recipe Parameters dialog and default visibility settings.
- `puma_ui/modules/header_columns/dialog.py`: Configure Header Columns dialog for recipe/result tables.
- `puma_ui/modules/image_display/dialog.py`: Image Display Window opened from the Alignment dialog or through `View > Image Display`.
- `puma_ui/modules/wafer_alignment/dialogs.py`: Alignment menu and Automatic Alignment Site Selection / Select Die Corner View flow.
- `puma_ui/modules/wafer_map/dialog.py`: Wafermap setup view opened from `Wafer > Wafer Map`.
- `puma_ui/modules/select_inspection/dialog.py`: Select Inspection button module and Open Inspection Recipe dialog.
- `puma_ui/modules/show_wafer/panel.py`: Embedded Show Wafer panel used inside the Open Inspection Recipe dialog.
- `puma_ui/modules/wafer_handling/dialog.py`: Wafer Handling dialog with carrier, wafer, alignment, orientation, laser, and dark-wafer controls.
- `puma_ui/modules/wafer_properties/dialogs.py`: Wafer menu, Wafer Properties dialog, and Edit Layer Database dialog.
- `puma_ui/modules/run_control/`: Run One Wafer, Run Status, abort handling, Job Setup Wizard, queue, and run logs.
- `puma_ui/modules/results_review/`: lot-result selection, filtering, synchronized Review panes, analysis, transfer, and KLARF export.
- `puma_ui/modules/sizing/`: tool-side Sizing setup plus the persistent offline SST maps, scatter plots, histograms, defect sets, XML recipes, and lot consolidation.
- `puma_ui/modules/system_status/`: Chapter 12 system utilities, equipment constants, transfer queue, job/material/carrier management, security, indicators, logging, and safe administration simulations.
- `puma_ui/modules/xp_offline/`: Chapter 13 AutoDerivative/AutoLearn/RDS/Comparator and Chapter 14 GDS2CA/CAG workflows.

## Windows package

Run `scripts\build_windows.ps1`. The script runs the full unit test suite, builds
`dist\Puma9980UI\Puma9980UI.exe`, and creates `release\Puma9980UI-Windows.zip`.
It separately builds the administrator-only generator at
`dist\Puma9980KeyGenerator\Puma9980KeyGenerator.exe` and packages it as
`release\Puma9980-KeyGenerator-Windows.zip`. Do not distribute the generator
archive with the operator application.

For an isolated packaged functional check, set `LOCALAPPDATA` to a temporary directory and run:

```powershell
dist\Puma9980UI\Puma9980UI.exe --smoke-test --smoke-output package-smoke-report.json
```

Exit code `0` and `"passed": true` confirm recipe persistence, one-wafer result generation, result persistence, and review-summary processing inside the packaged runtime.

## Suggested Next Steps

The staged implementation plan and current completion state are tracked in
[`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md).

Operator procedures are in [`docs/OPERATOR_GUIDE.md`](docs/OPERATOR_GUIDE.md), and the repeatable source acceptance gate is recorded in [`docs/SOURCE_ACCEPTANCE_CHECKLIST.md`](docs/SOURCE_ACCEPTANCE_CHECKLIST.md).
