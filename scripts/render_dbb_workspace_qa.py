from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt": os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.design_based_binning import DBBAnalysisToolboxDialog, DBBViewDialog, DBCBinPropertiesDialog, POIViewDialog, default_dbb_state
from puma_ui.qt_compat import QApplication


def capture(widget, path, width, height, app):
    widget.resize(width,height); widget.show(); app.processEvents()
    if not widget.grab().save(str(path)): raise RuntimeError(f"Unable to save {path}")
    widget.close()


def main():
    app=QApplication.instance() or QApplication([]); output=Path(".artifacts/visual-qa"); output.mkdir(parents=True,exist_ok=True)
    defects=[]
    for index in range(1,25):
        defects.append({"id":index,"x":index*137.5,"y":index*93.2,"design_x":index*117.0,"design_y":index*71.0,"die_x":index%5,"die_y":index%4,"test":"Test 1" if index%2 else "Test 2","dbc_bin":"Contact" if index%3 else "Line Edge","dbg_group":f"DBG-{index%6+1:03d}","dbb_global_bin":1 if index%3 else 2,"dci":round((index%10)/10,2),"pci":round(((index*3)%10)/10,2),"marked":index in {3,8,13}})
    state=default_dbb_state(); state.update({"enabled":True,"registered":True,"rdf_file":"DeviceA.rdf","inspection_layer":"Metal1","dbc_library":"Metal1 Production","dbc_bins":[{"id":"contact","name":"Contact","class_code":120,"examples":[{"id":"example-1","name":"Known Contact"}]},{"id":"line","name":"Line Edge","class_code":121,"examples":[]}]})
    result={"id":"dbb-lot","lot_id":"LOT-DBB-001","wafer_id":"W01","inspection":"Deep","defects":defects,"dbb_recipe":state}
    view=DBBViewDialog(result,state); view.grid.selectRow(2); capture(view,output/"dbb-view-1380x820.png",1380,820,app)
    toolbox=DBBAnalysisToolboxDialog(defects,state); toolbox.scheme.setCurrentText("Prioritized by DCI"); toolbox.limits.setChecked(True); capture(toolbox,output/"dbb-analysis-toolbox-700x520.png",700,520,app)
    properties=DBCBinPropertiesDialog({"name":"Contact","class_code":120,"nuisance":True,"rough_bin_enabled":True,"rough_bin_code":7,"size_sieve_enabled":True,"minimum_area":1,"maximum_area":25,"rotate":True,"examples":[]}); capture(properties,output/"dbc-bin-properties-620x560.png",620,560,app)
    poi=POIViewDialog({"name":"Known Contact","valid":False},["Design","Metal1"]); poi.layer_checks[1].setChecked(True); capture(poi,output/"dbc-poi-view-620x430.png",620,430,app)
    print("Rendered DBB workspace visual QA screenshots to",output.resolve())


if __name__ == "__main__": main()
