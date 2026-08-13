# Puma 9980 UI Prototype

This is a Python Qt prototype based on the Puma 9980 user manual Setup menu and the reference screenshots.

## User manual

The Puma 9980 UI operation manual is included here: [UserManual-9980.pdf](docs/UserManual-9980.pdf).

## Implemented

- Classic Windows-style main window, menu bar, toolbar, navigation strip, left setup menu, and status bar.
- Main toolbar button groups from the user manual: Standard toolbar, Optics toolbar, and Setup toolbar buttons with hover descriptions.
- 1920x1080-friendly sizing: the main window opens around 1600x900 and the recipe dialog around 1180x800, while still adapting to smaller screens.
- Compact 10px UI font with taller 24px input and combo-box controls to prevent clipped text.
- Setup menu entries: Select Inspection, Wafer, Tests, Lot Plan, Wafer Post Processing, Setup Run, Save Inspection, Recipe Generation, and End.
- Always-visible Recipe Overview area with Recipe Properties, Wafer Layout, status dots, and a wafer map placeholder.
- Recipe Overview sections use clickable arrow headers to expand or hide details; Recipe Properties and Wafer Layout start collapsed like the manual.
- Recipe Properties expands into Inspection Properties, Creation Properties, and Load/Save Status columns matching the manual layout.
- Expanded Wafer Layout content with Wafer Properties, Alignment scores, Registration Sites, Die Layout, Die Corner preview, Wafer Map preview, and Design Files.
- In Wafer Layout, click the Die Corner zoom icon to open Low Mag / High Mag enlarged die-corner image preview.
- In Wafer Layout, click the Wafer Map zoom icon to open an enlarged high-resolution wafer map preview.
- Added the Test 1 overview section with Test Properties, Inspection Optics, Collection Optics, Illumination Level Optimization, Fourier Filter, Light Level, Sensitivity, Defect Filters, Care Areas, and Sample Plan modules.
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
  - Use `Show Load Port: 1 / 2 / All` in the expanded Open Inspection Recipe dialog to choose how many load ports are displayed: one, two, or all available ports up to three.
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
- Future buttons such as Wafer, Tests, Lot Plan, Setup Run, and Save Inspection should each get their own folder under `puma_ui/modules/`.

## Suggested Next Steps

1. Update the Recipe Overview content after a recipe is opened.
2. Build the Wafer setup page.
3. Persist recipe and wafer settings to local project data files.
