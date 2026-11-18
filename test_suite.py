import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add project root to path
base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))

import core_downloader as core

def test_period_helpers():
    print("[TEST] Testing Period Calculation Helpers...")
    q1 = core.get_quarter_periods(2025, "Q1")
    assert q1 == ["042025", "052025", "062025"], f"Q1 mismatch: {q1}"

    q4 = core.get_quarter_periods(2025, "Q4")
    assert q4 == ["012026", "022026", "032026"], f"Q4 mismatch: {q4}"

    fy = core.get_fy_periods(2025)
    assert len(fy) == 12, f"FY length should be 12, got {len(fy)}"
    assert fy[0] == "042025" and fy[-1] == "032026", f"FY range mismatch: {fy}"
    print("  --> [PASS] Period helpers verified.")

def test_excel_converter():
    print("[TEST] Testing GSTR-1 Excel Converter & Consolidator...")
    temp_dir = Path(tempfile.mkdtemp(prefix="test_gstr1_"))
    try:
        sample_json_data = {
            "gstin": "27TESTG1234F1Z5",
            "fp": "042025",
            "gt": 500000.0,
            "cur_gt": 150000.0,
            "version": "1.0",
            "b2b": [
                {
                    "ctin": "27CLIENT1234F1Z1",
                    "cfs": "Y",
                    "inv": [
                        {
                            "inum": "INV-001",
                            "idt": "10-04-2025",
                            "val": 11800.0,
                            "pos": "27",
                            "rchrg": "N",
                            "inv_typ": "R",
                            "itms": [
                                {
                                    "num": 1,
                                    "itm_det": {
                                        "rt": 18,
                                        "txval": 10000.0,
                                        "iamt": 0,
                                        "camt": 900.0,
                                        "samt": 900.0,
                                        "csamt": 0
                                    }
                                }
                            ]
                        }
                    ]
                }
            ],
            "b2cs": [
                {
                    "sply_ty": "INTRA",
                    "pos": "27",
                    "typ": "OE",
                    "rt": 18,
                    "txval": 5000.0,
                    "camt": 450.0,
                    "samt": 450.0,
                    "iamt": 0,
                    "csamt": 0
                }
            ],
            "hsn": {
                "data": [
                    {
                        "num": 1,
                        "hsn_sc": "998311",
                        "desc": "IT Consulting Services",
                        "uqc": "OTH",
                        "qty": 1,
                        "val": 11800.0,
                        "rt": 18,
                        "txval": 10000.0,
                        "camt": 900.0,
                        "samt": 900.0,
                        "iamt": 0,
                        "csamt": 0
                    }
                ]
            },
            "doc_issue": {
                "doc_det": [
                    {
                        "doc_num": "DOC01",
                        "docs": [
                            {
                                "num": 1,
                                "from": "INV-001",
                                "to": "INV-001",
                                "totnum": 1,
                                "cancel": 0,
                                "net_issue": 1
                            }
                        ]
                    }
                ]
            }
        }

        # Write 2 sample JSON files
        json_file1 = temp_dir / "GSTR1_27TESTG1234F1Z5_042025.json"
        with open(json_file1, "w", encoding="utf-8") as f:
            json.dump(sample_json_data, f)

        sample_json_data2 = dict(sample_json_data)
        sample_json_data2["fp"] = "052025"
        json_file2 = temp_dir / "GSTR1_27TESTG1234F1Z5_052025.json"
        with open(json_file2, "w", encoding="utf-8") as f:
            json.dump(sample_json_data2, f)

        # Test single conversion
        xlsx1 = core.Gstr1ExcelConverter.convert_json_file(json_file1, log_fn=lambda m: None)
        assert xlsx1 is not None and xlsx1.exists(), "Excel file 1 not generated"

        # Check sheets in generated xlsx
        import pandas as pd
        excel_data = pd.read_excel(xlsx1, sheet_name=None)
        assert "Summary" in excel_data, "Summary sheet missing"
        assert "B2B" in excel_data, "B2B sheet missing"
        assert "B2CS" in excel_data, "B2CS sheet missing"
        assert "HSN" in excel_data, "HSN sheet missing"
        assert "Doc_Issued" in excel_data, "Doc_Issued sheet missing"

        # Test single conversion for file 2
        xlsx2 = core.Gstr1ExcelConverter.convert_json_file(json_file2, log_fn=lambda m: None)
        assert xlsx2 is not None and xlsx2.exists(), "Excel file 2 not generated"

        # Test consolidated workbook
        master_xlsx = core.Gstr1ExcelConverter.build_consolidated_excel(temp_dir, "27TESTG1234F1Z5", log_fn=lambda m: None)
        assert master_xlsx is not None and master_xlsx.exists(), "Master consolidated Excel not generated"

        master_data = pd.read_excel(master_xlsx, sheet_name=None)
        b2b_df = master_data["B2B"]
        assert len(b2b_df) == 2, f"Consolidated B2B should have 2 rows, got {len(b2b_df)}"
        assert "Return_Period" in b2b_df.columns, "Return_Period column missing in consolidated sheet"

        print("  --> [PASS] Excel conversion & consolidation verified with 100% sheet integrity.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_gui_instantiation():
    print("[TEST] Testing PySide6 GUI Launch in Headless Mode...")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    import gui_app

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(gui_app.MODERN_STYLE)
    win = gui_app.MainWindow()
    assert win is not None, "MainWindow failed to initialize"

    # Test period selector controls
    win.portal_period_selector.rad_fy.setChecked(True)
    win.portal_period_selector._on_mode_changed(1)
    fy_periods = win.portal_period_selector.get_selected_periods()
    assert len(fy_periods) == 12, f"Full FY should select 12 periods, got {len(fy_periods)}"

    win.portal_period_selector.rad_quarter.setChecked(True)
    win.portal_period_selector._on_mode_changed(0)
    q_periods = win.portal_period_selector.get_selected_periods()
    assert len(q_periods) == 3, f"Quarter should select 3 periods, got {len(q_periods)}"

    print("  --> [PASS] PySide6 GUI, widgets, styling, and period selection verified.")

if __name__ == "__main__":
    test_period_helpers()
    test_excel_converter()
    test_gui_instantiation()
    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")
