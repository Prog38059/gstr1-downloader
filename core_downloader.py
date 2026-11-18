import os
import sys
import io
import time
import json
import zipfile
import requests
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


# ==============================================================================
# RESILIENT .ENV LOADER (Handles .env, .env.txt, UTF-8 BOM, and UTF-16)
# ==============================================================================
def get_app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def load_environment(base_dir=None):
    if base_dir is None:
        base_dir = get_app_dir()
    base_dir = Path(base_dir)
    candidates = [base_dir / ".env", base_dir / ".env.txt"]
    env_file = next((p for p in candidates if p.exists()), None)
    if not env_file:
        return None

    raw_bytes = env_file.read_bytes()
    decoded = None
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"):
        try:
            decoded = raw_bytes.decode(enc)
            if "=" in decoded:
                break
        except Exception:
            continue

    if decoded:
        load_dotenv(stream=io.StringIO(decoded), override=True)
    return env_file


load_environment()


# ==============================================================================
# GSTR-1 JSON TO EXCEL PARSER & CONSOLIDATOR
# ==============================================================================
class Gstr1ExcelConverter:
    """Converts GSTR-1 JSON payloads into structured multi-sheet Excel workbooks."""

    @staticmethod
    def _extract_tables(data, period_label=""):
        """Parses standard GSTR-1 JSON sections into DataFrames."""
        tables = {}

        def tag_period(df):
            if period_label and not df.empty:
                df.insert(0, "Return_Period", period_label)
            return df

        # 1. Header / Summary Info
        summary_row = {
            "GSTIN": data.get("gstin", ""),
            "Filing_Period": data.get("fp", period_label),
            "Grand_Total": data.get("gt", ""),
            "Cur_Grand_Total": data.get("cur_gt", ""),
            "Version": data.get("version", ""),
        }
        tables["Summary"] = tag_period(pd.DataFrame([summary_row]))

        # 2. B2B Invoices
        b2b_rows = []
        for party in data.get("b2b", []):
            ctin = party.get("ctin", "")
            cfs = party.get("cfs", "")
            for inv in party.get("inv", []):
                base_inv = {
                    "CTIN": ctin,
                    "Counterparty_Filing_Status": cfs,
                    "Invoice_No": inv.get("inum", ""),
                    "Invoice_Date": inv.get("idt", ""),
                    "Invoice_Value": inv.get("val", 0),
                    "Place_Of_Supply": inv.get("pos", ""),
                    "Reverse_Charge": inv.get("rchrg", ""),
                    "Invoice_Type": inv.get("inv_typ", ""),
                    "ECom_GSTIN": inv.get("etin", ""),
                }
                items = inv.get("itms", [])
                if not items:
                    b2b_rows.append(base_inv)
                else:
                    for item in items:
                        det = item.get("itm_det", {})
                        row = dict(base_inv)
                        row.update({
                            "Item_Num": item.get("num", ""),
                            "Tax_Rate": det.get("rt", 0),
                            "Taxable_Value": det.get("txval", 0),
                            "IGST": det.get("iamt", 0),
                            "CGST": det.get("camt", 0),
                            "SGST": det.get("samt", 0),
                            "Cess": det.get("csamt", 0),
                        })
                        b2b_rows.append(row)
        if b2b_rows:
            tables["B2B"] = tag_period(pd.DataFrame(b2b_rows))

        # 3. B2CL (B2C Large)
        b2cl_rows = []
        for entry in data.get("b2cl", []):
            pos = entry.get("pos", "")
            for inv in entry.get("inv", []):
                base_inv = {
                    "Place_Of_Supply": pos,
                    "Invoice_No": inv.get("inum", ""),
                    "Invoice_Date": inv.get("idt", ""),
                    "Invoice_Value": inv.get("val", 0),
                    "ECom_GSTIN": inv.get("etin", ""),
                }
                for item in inv.get("itms", []):
                    det = item.get("itm_det", {})
                    row = dict(base_inv)
                    row.update({
                        "Item_Num": item.get("num", ""),
                        "Tax_Rate": det.get("rt", 0),
                        "Taxable_Value": det.get("txval", 0),
                        "IGST": det.get("iamt", 0),
                        "Cess": det.get("csamt", 0),
                    })
                    b2cl_rows.append(row)
        if b2cl_rows:
            tables["B2CL"] = tag_period(pd.DataFrame(b2cl_rows))

        # 4. B2CS (B2C Small)
        b2cs_rows = []
        for entry in data.get("b2cs", []):
            b2cs_rows.append({
                "Supply_Type": entry.get("sply_ty", ""),
                "Place_Of_Supply": entry.get("pos", ""),
                "Type": entry.get("typ", ""),
                "ECom_GSTIN": entry.get("etin", ""),
                "Tax_Rate": entry.get("rt", 0),
                "Taxable_Value": entry.get("txval", 0),
                "IGST": entry.get("iamt", 0),
                "CGST": entry.get("camt", 0),
                "SGST": entry.get("samt", 0),
                "Cess": entry.get("csamt", 0),
            })
        if b2cs_rows:
            tables["B2CS"] = tag_period(pd.DataFrame(b2cs_rows))

        # 5. CDNR (Credit/Debit Notes Registered)
        cdnr_rows = []
        for party in data.get("cdnr", []):
            ctin = party.get("ctin", "")
            cfs = party.get("cfs", "")
            for note in party.get("nt", []):
                base_note = {
                    "CTIN": ctin,
                    "Counterparty_Filing_Status": cfs,
                    "Note_Type": note.get("ntty", ""),
                    "Note_No": note.get("nt_num", ""),
                    "Note_Date": note.get("nt_dt", ""),
                    "Note_Value": note.get("val", 0),
                    "Place_Of_Supply": note.get("pos", ""),
                    "Reverse_Charge": note.get("rchrg", ""),
                    "Invoice_Type": note.get("inv_typ", ""),
                }
                for item in note.get("itms", []):
                    det = item.get("itm_det", {})
                    row = dict(base_note)
                    row.update({
                        "Item_Num": item.get("num", ""),
                        "Tax_Rate": det.get("rt", 0),
                        "Taxable_Value": det.get("txval", 0),
                        "IGST": det.get("iamt", 0),
                        "CGST": det.get("camt", 0),
                        "SGST": det.get("samt", 0),
                        "Cess": det.get("csamt", 0),
                    })
                    cdnr_rows.append(row)
        if cdnr_rows:
            tables["CDNR"] = tag_period(pd.DataFrame(cdnr_rows))

        # 6. CDNUR (Credit/Debit Notes Unregistered)
        cdnur_rows = []
        for note in data.get("cdnur", []):
            base_note = {
                "Type": note.get("typ", ""),
                "Note_Type": note.get("ntty", ""),
                "Note_No": note.get("nt_num", ""),
                "Note_Date": note.get("nt_dt", ""),
                "Note_Value": note.get("val", 0),
                "Place_Of_Supply": note.get("pos", ""),
            }
            for item in note.get("itms", []):
                det = item.get("itm_det", {})
                row = dict(base_note)
                row.update({
                    "Item_Num": item.get("num", ""),
                    "Tax_Rate": det.get("rt", 0),
                    "Taxable_Value": det.get("txval", 0),
                    "IGST": det.get("iamt", 0),
                    "Cess": det.get("csamt", 0),
                })
                cdnur_rows.append(row)
        if cdnur_rows:
            tables["CDNUR"] = tag_period(pd.DataFrame(cdnur_rows))

        # 7. EXP (Exports)
        exp_rows = []
        for group in data.get("exp", []):
            exp_typ = group.get("exp_typ", "")
            for inv in group.get("inv", []):
                base_inv = {
                    "Export_Type": exp_typ,
                    "Invoice_No": inv.get("inum", ""),
                    "Invoice_Date": inv.get("idt", ""),
                    "Invoice_Value": inv.get("val", 0),
                    "Shipping_Bill_No": inv.get("sbnum", ""),
                    "Shipping_Bill_Date": inv.get("sbdt", ""),
                    "Port_Code": inv.get("sbpcode", ""),
                }
                for item in inv.get("itms", []):
                    row = dict(base_inv)
                    row.update({
                        "Tax_Rate": item.get("rt", 0),
                        "Taxable_Value": item.get("txval", 0),
                        "IGST": item.get("iamt", 0),
                        "Cess": item.get("csamt", 0),
                    })
                    exp_rows.append(row)
        if exp_rows:
            tables["EXP"] = tag_period(pd.DataFrame(exp_rows))

        # 8. NIL / Exempt / Non-GST Supplies
        nil_inv = data.get("nil", {}).get("inv", [])
        if nil_inv:
            nil_rows = []
            for entry in nil_inv:
                nil_rows.append({
                    "Supply_Type": entry.get("sply_ty", ""),
                    "Nil_Rated_Amount": entry.get("nil_amt", 0),
                    "Exempt_Amount": entry.get("expt_amt", 0),
                    "Non_GST_Amount": entry.get("ngsup_amt", 0),
                })
            tables["NIL_Exempt"] = tag_period(pd.DataFrame(nil_rows))

        # 9. HSN Summary
        hsn_data = data.get("hsn", {}).get("data", [])
        if hsn_data:
            hsn_rows = []
            for entry in hsn_data:
                hsn_rows.append({
                    "Sl_No": entry.get("num", ""),
                    "HSN_SAC": entry.get("hsn_sc", ""),
                    "Description": entry.get("desc", ""),
                    "UQC": entry.get("uqc", ""),
                    "Quantity": entry.get("qty", 0),
                    "Total_Value": entry.get("val", 0),
                    "Tax_Rate": entry.get("rt", 0),
                    "Taxable_Value": entry.get("txval", 0),
                    "IGST": entry.get("iamt", 0),
                    "CGST": entry.get("camt", 0),
                    "SGST": entry.get("samt", 0),
                    "Cess": entry.get("csamt", 0),
                })
            tables["HSN"] = tag_period(pd.DataFrame(hsn_rows))

        # 10. Documents Issued
        doc_det = data.get("doc_issue", {}).get("doc_det", [])
        if doc_det:
            doc_rows = []
            for group in doc_det:
                doc_num = group.get("doc_num", "")
                for doc in group.get("docs", []):
                    doc_rows.append({
                        "Doc_Type_Code": doc_num,
                        "Serial_Num": doc.get("num", ""),
                        "From_Serial": doc.get("from", ""),
                        "To_Serial": doc.get("to", ""),
                        "Total_Number": doc.get("totnum", 0),
                        "Cancelled": doc.get("cancel", 0),
                        "Net_Issued": doc.get("net_issue", 0),
                    })
            if doc_rows:
                tables["Doc_Issued"] = tag_period(pd.DataFrame(doc_rows))

        return tables

    @classmethod
    def convert_json_file(cls, json_path, log_fn=print):
        """Converts a single GSTR-1 JSON file into a matching .xlsx file."""
        if not EXCEL_AVAILABLE:
            log_fn("[!] pandas/openpyxl not installed. Run: pip install pandas openpyxl")
            return None

        json_path = Path(json_path)
        if not json_path.exists():
            log_fn(f"[X] JSON file not found: {json_path}")
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            payload = raw.get("data") if isinstance(raw.get("data"), dict) and "gstin" in raw["data"] else raw
            period_label = payload.get("fp", json_path.stem.split("_")[-1])
            tables = cls._extract_tables(payload, period_label=period_label)

            xlsx_path = json_path.with_suffix(".xlsx")
            with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
                for sheet_name, df in tables.items():
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

            log_fn(f"[OK] Converted to Excel: {xlsx_path.name}")
            return xlsx_path
        except Exception as e:
            log_fn(f"[X] Excel conversion failed for {json_path.name}: {e}")
            return None

    @classmethod
    def build_consolidated_excel(cls, gstin_folder, gstin_label, log_fn=print):
        """Merges all GSTR-1 JSON files in the GSTIN folder into one master Excel workbook."""
        if not EXCEL_AVAILABLE:
            log_fn("[!] pandas/openpyxl not installed. Run: pip install pandas openpyxl")
            return None

        folder = Path(gstin_folder)
        json_files = sorted(folder.glob("GSTR1_*.json"))
        if not json_files:
            log_fn(f"[!] No GSTR1_*.json files found in {folder} to consolidate.")
            return None

        merged_tables = {}
        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                payload = raw.get("data") if isinstance(raw.get("data"), dict) and "gstin" in raw["data"] else raw
                period_label = payload.get("fp", jf.stem.split("_")[-1])
                tables = cls._extract_tables(payload, period_label=period_label)

                for sheet_name, df in tables.items():
                    merged_tables.setdefault(sheet_name, []).append(df)
            except Exception as e:
                log_fn(f"[!] Skipping {jf.name} during consolidation: {e}")

        if not merged_tables:
            return None

        master_path = folder / f"GSTR1_{gstin_label}_CONSOLIDATED.xlsx"
        try:
            with pd.ExcelWriter(master_path, engine="openpyxl") as writer:
                for sheet_name, df_list in merged_tables.items():
                    combined_df = pd.concat(df_list, ignore_index=True)
                    combined_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            log_fn(f"[OK] Consolidated Master Excel saved: {master_path.name}")
            return master_path
        except Exception as e:
            log_fn(f"[X] Failed to save consolidated Excel: {e}")
            return None


# ==============================================================================
# MODE 1: DIRECT GOVT GST PORTAL DOWNLOADER (Two-Phase Batch Workflow)
# ==============================================================================
class DirectGstPortalDownloader:
    def __init__(self, base_dir=None, log_fn=print, captcha_fn=None, stop_check_fn=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent
        self.log = log_fn
        self.captcha_fn = captcha_fn
        self.stop_check_fn = stop_check_fn or (lambda: False)

        load_environment(self.base_dir)
        self.username = os.getenv("GOVT_GST_LOGIN_NAME") or os.getenv("GST_USERNAME")
        self.password = os.getenv("GOVT_GST_LOGIN_PASSWORD") or os.getenv("GST_PASSWORD")
        self.gstin = (os.getenv("GSTIN") or "UNKNOWN_GSTIN").strip()
        self.output_dir = self.base_dir / self.gstin
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.auth_token = None
        self.session = requests.Session()

    def validate_credentials(self):
        if not self.username or not self.password:
            self.log("[X] Error: Missing credentials in .env file.")
            self.log("Please ensure GOVT_GST_LOGIN_NAME and GOVT_GST_LOGIN_PASSWORD are set.")
            return False
        return True

    def _launch_browser(self, p):
        # 1. Check local bundled browsers directory
        local_browsers = self.base_dir / "ms-playwright"
        if local_browsers.exists() and "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(local_browsers)

        # 2. Try standard Playwright Chromium
        try:
            return p.chromium.launch(headless=True)
        except Exception as e_std:
            self.log(f"[!] Standard Playwright Chromium note: {e_std}")

        # 3. Fallback: System Google Chrome
        try:
            self.log("[INFO] Attempting to launch via system Google Chrome...")
            return p.chromium.launch(headless=True, channel="chrome")
        except Exception:
            pass

        # 4. Fallback: System Microsoft Edge (Standard on Windows 10/11)
        try:
            self.log("[INFO] Attempting to launch via system Microsoft Edge...")
            return p.chromium.launch(headless=True, channel="msedge")
        except Exception as e_all:
            self.log(f"[X] All browser launch options failed: {e_all}")
            raise e_all

    def login(self):
        """Headless login with captcha callback / terminal prompt."""
        if not self.validate_credentials():
            return False

        self.log("\n--- Starting Direct GST Portal Login ---")
        with Stealth().use_sync(sync_playwright()) as p:
            browser = self._launch_browser(p)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                self.log("Navigating to GST Login page...")
                page.goto(
                    "https://services.gst.gov.in/services/login",
                    wait_until="load",
                    timeout=60000,
                )

                page.fill("#username", self.username)
                page.fill("#user_pass", self.password)

                max_captcha_retries = 3
                logged_in = False

                for attempt in range(max_captcha_retries):
                    if self.stop_check_fn():
                        self.log("[!] Login cancelled by user.")
                        return False

                    self.log("Capturing captcha image...")
                    captcha_img = page.wait_for_selector(
                        "#img_captcha, #imgCaptcha", timeout=60000
                    )
                    captcha_path = self.base_dir / "captcha.png"
                    captcha_img.screenshot(path=str(captcha_path))
                    self.log(f"Captcha captured: {captcha_path}")

                    # Ask for captcha via GUI callback or CLI input
                    if self.captcha_fn:
                        captcha_code = self.captcha_fn(str(captcha_path))
                        if captcha_code == "__REFRESH__":
                            self.log("Refreshing captcha on portal...")
                            refresh_btn = page.query_selector("#img_captcha ~ a, .captcha-refresh, a[ng-click*='captcha']")
                            if refresh_btn:
                                refresh_btn.click()
                            else:
                                page.reload()
                            time.sleep(2)
                            continue
                    else:
                        captcha_code = input("Open captcha.png and enter the captcha code here: ").strip()

                    if not captcha_code:
                        self.log("[X] No captcha entered. Aborting login.")
                        return False

                    page.fill("#captcha", str(captcha_code).strip())
                    page.click("button[type='submit']")

                    try:
                        page.wait_for_url("**/fowelcome", timeout=12000)
                        self.log("[OK] Login successful!")
                        logged_in = True
                        break
                    except Exception:
                        err_elem = page.query_selector(".alert-danger, .err-msg, #error-msg")
                        err_text = err_elem.inner_text().strip() if err_elem else "Captcha or credentials error"
                        self.log(f"[!] Login attempt {attempt + 1} did not succeed: {err_text}")
                        if attempt < max_captcha_retries - 1:
                            self.log("Retrying with fresh captcha...")
                            time.sleep(1)
                        else:
                            self.log("[X] Exceeded maximum login attempts.")
                            return False

                if not logged_in:
                    return False

                self.auth_token = page.evaluate(
                    "() => sessionStorage.getItem('AuthToken')"
                )
                for cookie in page.context.cookies():
                    self.session.cookies.set(
                        cookie["name"],
                        cookie["value"],
                        domain=cookie["domain"],
                        path=cookie["path"],
                    )

                if not self.auth_token:
                    self.auth_token = self.session.cookies.get(
                        "AuthToken", domain=".gst.gov.in"
                    )

                if self.auth_token:
                    self.log(f"[OK] Session AuthToken captured ({self.auth_token[:10]}...)")
                else:
                    self.log("[!] Warning: AuthToken not found; API calls may fail.")

                self.log(f"[OK] Output folder ready: {self.output_dir}")
                return True

            except Exception as e:
                self.log(f"[X] Login failed: {e}")
                err_path = self.base_dir / "error_login.png"
                try:
                    page.screenshot(path=str(err_path))
                    self.log(f"Saved debug screenshot to {err_path}")
                except Exception:
                    pass
                return False
            finally:
                browser.close()

    def _safe_json(self, resp, step_name):
        try:
            return resp.json()
        except Exception as e:
            snippet = resp.text[:200].replace("\n", " ").replace("\r", "")
            self.log(f"[X] JSON parse error in {step_name} (HTTP {resp.status_code}): {e}")
            self.log(f"    Response snippet: {snippet}...")
            return None

    def set_period_context(self, period):
        url = f"https://return.gst.gov.in/returns/auth/api/rolestatus?rtn_prd={period}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "AuthToken": self.auth_token,
            "Referer": "https://return.gst.gov.in/returns/auth/dashboard",
        }
        resp = self.session.get(url, headers=headers)
        return resp.status_code == 200

    def trigger_generation_only(self, period):
        """Triggers or checks generation status for a period without blocking."""
        if not self.set_period_context(period):
            self.log(f"   [{period}] [X] Could not set portal context.")
            return None

        gen_url = (
            f"https://return.gst.gov.in/returns/auth/api/offline/download/generate"
            f"?flag=0&rtn_prd={period}&rtn_typ=GSTR1"
        )
        headers = {
            "Accept": "application/json, text/plain, */*",
            "AuthToken": self.auth_token,
            "Referer": "https://return.gst.gov.in/returns/auth/gstr/offlinedownload",
        }

        resp = self.session.get(gen_url, headers=headers)
        if resp.status_code != 200:
            self.log(f"   [{period}] [X] Generation request failed (HTTP {resp.status_code}).")
            return None

        data = self._safe_json(resp, f"trigger_{period}")
        if data and data.get("status") == 1:
            urls = data.get("data", {}).get("url")
            msg = data.get("data", {}).get("msg", "Triggered")
            if urls:
                self.log(f"   [{period}] [OK] Already ready for download!")
                return urls[0] if isinstance(urls, list) else urls
            else:
                self.log(f"   [{period}] [WAIT] Generation triggered: {msg}")
                return "PENDING"
        else:
            self.log(f"   [{period}] [!] Unexpected response: {data}")
            return None

    def _download_zip_and_convert(self, download_url, period):
        """Downloads ZIP, extracts JSON into GSTIN folder, and converts to Excel."""
        zip_resp = self.session.get(download_url)
        if zip_resp.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                for name in zf.namelist():
                    if name.endswith(".json"):
                        json_name = f"GSTR1_{self.gstin}_{period}.json"
                        json_path = self.output_dir / json_name
                        json_path.write_bytes(zf.read(name))
                        self.log(f"   [{period}] [OK] Saved JSON: {json_path.name}")
                        Gstr1ExcelConverter.convert_json_file(json_path, log_fn=self.log)
                        return True
        self.log(f"   [{period}] [X] Failed to download or extract ZIP.")
        return False

    def batch_trigger_and_collect(self, periods, trigger_first=True, auto_poll=True, progress_fn=None):
        """Phase 1: Trigger all periods upfront. Phase 2: Batch collect all ready files."""
        pending = []

        if trigger_first:
            self.log("\n=== PHASE 1: Triggering Generation for All Selected Periods ===")
            total = len(periods)
            for idx, period in enumerate(periods, 1):
                if self.stop_check_fn():
                    self.log("[!] Stopped by user.")
                    return
                if progress_fn:
                    progress_fn(idx, total, f"Triggering {period} ({idx}/{total})")
                result = self.trigger_generation_only(period)
                if result == "PENDING":
                    pending.append(period)
                elif isinstance(result, str) and result.startswith("http"):
                    self._download_zip_and_convert(result, period)
                time.sleep(1.5)
        else:
            pending = list(periods)

        if not pending:
            self.log("\n[DONE] All selected periods are already downloaded!")
            Gstr1ExcelConverter.build_consolidated_excel(self.output_dir, self.gstin, log_fn=self.log)
            return

        self.log(f"\n[QUEUE] {len(pending)} period(s) queued on GST server: {', '.join(pending)}")

        if not auto_poll:
            self.log("[TIP] Check again later and choose 'Download Already-Generated Files Only'.")
            return

        self.log("\n=== PHASE 2: Batch Checking & Downloading Ready Files ===")
        self.log("(Checking pending periods every 30 seconds. Stop anytime to resume later.)")

        round_num = 0
        while pending:
            if self.stop_check_fn():
                self.log("[!] Polling stopped by user.")
                break

            round_num += 1
            self.log(f"\n--- Check Round #{round_num} | Remaining: {', '.join(pending)} ---")
            still_pending = []

            for idx, period in enumerate(pending, 1):
                if self.stop_check_fn():
                    self.log("[!] Polling stopped by user.")
                    return
                if progress_fn:
                    progress_fn(idx, len(pending), f"Round #{round_num}: Checking {period}")
                result = self.trigger_generation_only(period)
                if isinstance(result, str) and result.startswith("http"):
                    self._download_zip_and_convert(result, period)
                elif result == "PENDING":
                    still_pending.append(period)
                else:
                    self.log(f"   [{period}] [!] Dropping from queue due to error.")
                time.sleep(1)

            pending = still_pending
            if pending:
                self.log("Waiting 30 seconds before next batch check...")
                for s in range(30):
                    if self.stop_check_fn():
                        self.log("[!] Polling stopped by user.")
                        return
                    time.sleep(1)

        self.log("\n[DONE] Batch download cycle complete!")
        Gstr1ExcelConverter.build_consolidated_excel(self.output_dir, self.gstin, log_fn=self.log)


# ==============================================================================
# MODE 2: WHITEBOOKS GSP API DOWNLOADER (API Token + OTP Flow)
# ==============================================================================
class WhiteBooksApiDownloader:
    def __init__(self, base_dir=None, log_fn=print, otp_fn=None, stop_check_fn=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent
        self.log = log_fn
        self.otp_fn = otp_fn
        self.stop_check_fn = stop_check_fn or (lambda: False)

        load_environment(self.base_dir)
        self.base_url = os.getenv("BASE_URL", "https://apisandbox.whitebooks.in")
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.email = os.getenv("EMAIL")
        self.gst_username = os.getenv("GST_USERNAME") or os.getenv("GOVT_GST_LOGIN_NAME")
        self.gstin = (os.getenv("GSTIN") or "").strip()
        self.state_cd = os.getenv("STATE_CD") or (self.gstin[:2] if self.gstin else "")
        self.ip_address = os.getenv("IP_ADDRESS", "192.168.1.1")

        self.output_dir = self.base_dir / (self.gstin or "API_OUTPUT")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.auth_token = None
        self.txn = None

    def _headers(self):
        headers = {
            "accept": "*/*",
            "gst_username": self.gst_username,
            "state_cd": self.state_cd,
            "ip_address": self.ip_address,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.txn:
            headers["txn"] = self.txn
        if self.auth_token and self.auth_token != "SANDBOX_SUCCESS":
            headers["Authorization"] = self.auth_token
        return headers

    def login(self):
        if not all([self.client_id, self.client_secret, self.email, self.gst_username, self.gstin]):
            self.log("[X] Error: Missing WhiteBooks API credentials in .env.")
            self.log("Required: CLIENT_ID, CLIENT_SECRET, EMAIL, GST_USERNAME, GSTIN")
            return False

        self.log(f"\n--- Authenticating WhiteBooks API for {self.gst_username} ---")
        try:
            otp_resp = self.session.get(
                f"{self.base_url}/authentication/otprequest",
                headers=self._headers(),
                params={"email": self.email},
            )
            otp_resp.raise_for_status()
            otp_data = otp_resp.json()

            if otp_data.get("status_cd") == "0":
                self.log(f"[X] OTP Request failed: {otp_data}")
                return False

            self.txn = otp_data.get("header", {}).get("txn")
            if not self.txn:
                self.log("[X] No transaction ID (txn) returned.")
                return False

            if self.otp_fn:
                otp = self.otp_fn("575757")
            else:
                otp = input("Enter OTP (press Enter for sandbox default 575757): ").strip() or "575757"

            if not otp:
                self.log("[X] No OTP provided. Aborting.")
                return False

            tok_resp = self.session.get(
                f"{self.base_url}/authentication/authtoken",
                headers=self._headers(),
                params={"email": self.email, "otp": otp},
            )
            tok_resp.raise_for_status()
            tok_data = tok_resp.json()

            self.auth_token = (
                tok_data.get("auth_token")
                or tok_data.get("token")
                or tok_data.get("header", {}).get("auth_token")
            )

            if tok_data.get("status_cd") == "1" and not self.auth_token:
                self.auth_token = "SANDBOX_SUCCESS"

            if self.auth_token:
                self.log("[OK] WhiteBooks API authenticated successfully!")
                return True

            self.log(f"[X] Failed to obtain AuthToken: {tok_data}")
            return False
        except Exception as e:
            self.log(f"[X] API Authentication error: {e}")
            return False

    def get_return_reference(self, period):
        try:
            resp = self.session.get(
                f"{self.base_url}/gstr/rettrack",
                headers=self._headers(),
                params={"gstin": self.gstin, "email": self.email, "returnperiod": period},
            )
            resp.raise_for_status()
            data = resp.json()
            for ret in data.get("data", {}).get("EFiledlist", []):
                if ret.get("rtntype") == "GSTR1" and ret.get("status") == "Filed":
                    return True, (ret.get("arn") or ret.get("ref_id"))
            return False, None
        except Exception:
            return False, None

    def download_period(self, period):
        self.log(f"\n--- Downloading via API for Period: {period} ---")
        is_filed, ref_id = self.get_return_reference(period)
        if not is_filed:
            self.log(f"[!] Return for {period} does not appear as Filed. Attempting download anyway...")

        doc_id = ref_id or f"GSTR1{self.gstin}{period}"
        try:
            resp = self.session.get(
                f"{self.base_url}/all/docdwld",
                headers=self._headers(),
                params={
                    "gstin": self.gstin,
                    "retperiod": period,
                    "email": self.email,
                    "id": doc_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status_cd") == "0":
                msg = data.get("error", {}).get("message", "Unknown API error")
                self.log(f"[X] API Error for {period}: {msg}")
                return False

            json_name = f"GSTR1_{self.gstin}_{period}.json"
            json_path = self.output_dir / json_name
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.log(f"[OK] Saved JSON: {json_path.name}")
            Gstr1ExcelConverter.convert_json_file(json_path, log_fn=self.log)
            return True
        except Exception as e:
            self.log(f"[X] API Download failed for {period}: {e}")
            return False

    def logout(self):
        if self.txn:
            try:
                self.session.get(
                    f"{self.base_url}/authentication/logout",
                    headers=self._headers(),
                    params={"email": self.email},
                )
                self.log("Logged out of WhiteBooks API session.")
            except Exception:
                pass


# ==============================================================================
# PERIOD CALCULATION HELPERS
# ==============================================================================
def get_quarter_periods(fy_start_year, q):
    y1 = int(fy_start_year)
    y2 = y1 + 1
    q_map = {
        "Q1": [f"04{y1}", f"05{y1}", f"06{y1}"],
        "Q2": [f"07{y1}", f"08{y1}", f"09{y1}"],
        "Q3": [f"10{y1}", f"11{y1}", f"12{y1}"],
        "Q4": [f"01{y2}", f"02{y2}", f"03{y2}"],
    }
    return q_map.get(q.upper(), [])


def get_fy_periods(fy_start_year):
    y1 = int(fy_start_year)
    y2 = y1 + 1
    return [
        f"04{y1}", f"05{y1}", f"06{y1}",
        f"07{y1}", f"08{y1}", f"09{y1}",
        f"10{y1}", f"11{y1}", f"12{y1}",
        f"01{y2}", f"02{y2}", f"03{y2}",
    ]


def prompt_target_periods():
    print("\nSelect Target Periods:")
    print("1. Single Month (MMYYYY)")
    print("2. Full Quarter (Q1, Q2, Q3, Q4 of a Financial Year)")
    print("3. Full Financial Year (All 12 months Apr-Mar)")
    print("4. Custom List of Months (comma-separated, e.g. 042025, 052025, 062025)")

    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        p = input("Enter month (MMYYYY, e.g., 042025): ").strip()
        return [p] if (len(p) == 6 and p.isdigit()) else []

    elif choice == "2":
        q = input("Enter Quarter (Q1, Q2, Q3, Q4): ").strip().upper()
        fy_start = input("Enter Financial Year Start Year (e.g., 2025 for FY 2025-26): ").strip()
        if not (fy_start.isdigit() and len(fy_start) == 4):
            return []
        return get_quarter_periods(fy_start, q)

    elif choice == "3":
        fy_start = input("Enter Financial Year Start Year (e.g., 2025 for FY 2025-26): ").strip()
        if not (fy_start.isdigit() and len(fy_start) == 4):
            return []
        return get_fy_periods(fy_start)

    elif choice == "4":
        raw = input("Enter comma-separated months (MMYYYY): ").strip()
        items = [x.strip() for x in raw.split(",") if x.strip()]
        return [x for x in items if len(x) == 6 and x.isdigit()]

    return []


def run_offline_excel_converter(base_dir=None, gstin=None, log_fn=print):
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent
    base_dir = Path(base_dir)

    load_environment(base_dir)
    if not gstin:
        gstin = (os.getenv("GSTIN") or "").strip()
    if not gstin:
        gstin = input("Enter GSTIN folder name: ").strip()

    gstin_folder = base_dir / gstin
    if not gstin_folder.exists():
        log_fn(f"[X] Folder not found: {gstin_folder}")
        return

    json_files = sorted(gstin_folder.glob("GSTR1_*.json"))
    if not json_files:
        log_fn(f"[X] No GSTR1_*.json files found in {gstin_folder}")
        return

    log_fn(f"\nFound {len(json_files)} JSON file(s) in {gstin_folder}. Converting...")
    for jf in json_files:
        Gstr1ExcelConverter.convert_json_file(jf, log_fn=log_fn)

    Gstr1ExcelConverter.build_consolidated_excel(gstin_folder, gstin, log_fn=log_fn)


def main():
    print("==========================================================")
    print("   UNIFIED GSTR-1 DOWNLOADER & EXCEL CONVERTER (v2)       ")
    print("==========================================================")
    print("1. Direct GST Portal (Trigger All Upfront -> Batch Download & Excel)")
    print("2. WhiteBooks GSP API (OTP Auth -> Download & Excel)")
    print("3. Offline Excel Converter (Convert Existing JSONs in GSTIN Folder)")

    mode = input("\nEnter choice (1, 2, or 3): ").strip()

    if mode == "1":
        downloader = DirectGstPortalDownloader()
        if not downloader.login():
            return

        print("\nSelect Portal Action:")
        print("1. Trigger Generation for All Selected Periods & Wait/Download")
        print("2. Trigger Generation Only (Exit immediately, download later)")
        print("3. Download Already-Generated Files Only (Skip triggering)")
        action = input("Enter action (1, 2, or 3): ").strip()

        periods = prompt_target_periods()
        if not periods:
            print("[X] Invalid period selection.")
            return

        print(f"\nSelected Periods ({len(periods)}): {', '.join(periods)}")

        if action == "1":
            downloader.batch_trigger_and_collect(periods, trigger_first=True, auto_poll=True)
        elif action == "2":
            downloader.batch_trigger_and_collect(periods, trigger_first=True, auto_poll=False)
        elif action == "3":
            downloader.batch_trigger_and_collect(periods, trigger_first=False, auto_poll=True)
        else:
            print("[X] Invalid action choice.")

    elif mode == "2":
        downloader = WhiteBooksApiDownloader()
        if not downloader.login():
            return
        try:
            periods = prompt_target_periods()
            if not periods:
                print("[X] Invalid period selection.")
                return
            for p in periods:
                downloader.download_period(p)
            Gstr1ExcelConverter.build_consolidated_excel(downloader.output_dir, downloader.gstin)
        finally:
            downloader.logout()

    elif mode == "3":
        run_offline_excel_converter()

    else:
        print("[X] Invalid choice. Please run the script again and select 1, 2, or 3.")


if __name__ == "__main__":
    main()
