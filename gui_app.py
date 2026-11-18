import os
import sys
import threading
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QColor, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QGroupBox,
    QGridLayout, QFrame, QDialog, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QRadioButton, QButtonGroup, QScrollArea
)

import core_downloader as core

# ==============================================================================
# MODERN DARK THEME QSS (Slate & Indigo Palette)
# ==============================================================================
MODERN_STYLE = """
QMainWindow, QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #1E293B;
    background: #111827;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: #1E293B;
    color: #94A3B8;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #334155;
    border-bottom: none;
}

QTabBar::tab:selected {
    background: #2563EB;
    color: #FFFFFF;
    border-color: #3B82F6;
}

QTabBar::tab:hover:!selected {
    background: #334155;
    color: #F1F5F9;
}

QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    padding-left: 12px;
    padding-right: 12px;
    padding-bottom: 12px;
    font-weight: 600;
    font-size: 13px;
    color: #93C5FD;
    background-color: #1E293B;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #1E293B;
    border-radius: 4px;
}

QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #3B82F6;
}

QPushButton:pressed {
    background-color: #1D4ED8;
}

QPushButton:disabled {
    background-color: #334155;
    color: #64748B;
}

QPushButton.btn-secondary {
    background-color: #334155;
    color: #E2E8F0;
    border: 1px solid #475569;
}

QPushButton.btn-secondary:hover {
    background-color: #475569;
}

QPushButton.btn-success {
    background-color: #059669;
    color: #FFFFFF;
}

QPushButton.btn-success:hover {
    background-color: #10B981;
}

QPushButton.btn-danger {
    background-color: #DC2626;
    color: #FFFFFF;
}

QPushButton.btn-danger:hover {
    background-color: #EF4444;
}

QPushButton.chip-btn {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #475569;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12px;
}

QPushButton.chip-btn:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    border-color: #60A5FA;
}

QLineEdit, QComboBox {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #2563EB;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3B82F6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #475569;
    selection-background-color: #2563EB;
}

QRadioButton, QCheckBox {
    color: #E2E8F0;
    spacing: 8px;
    font-size: 13px;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #64748B;
    background: #0F172A;
}

QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #3B82F6;
}

QProgressBar {
    border: 1px solid #334155;
    border-radius: 6px;
    background-color: #1E293B;
    text-align: center;
    color: #FFFFFF;
    font-weight: 600;
    height: 16px;
}

QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 5px;
}

QTextEdit {
    background-color: #0B0F19;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 6px;
    font-family: "Consolas", "Cascadia Code", "Courier New", monospace;
    font-size: 12px;
    padding: 8px;
}

QTableWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #1E293B;
}

QTableWidget::item:selected {
    background-color: #1E3A8A;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    padding: 6px;
    border: 1px solid #334155;
    font-weight: 600;
}

QScrollBar:vertical {
    border: none;
    background: #0F172A;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# ==============================================================================
# MODAL DIALOGS: CAPTCHA VIEWER & OTP DIALOG
# ==============================================================================
class CaptchaDialog(QDialog):
    """Sleek modal dialog displaying the GST portal captcha image with input field."""
    def __init__(self, captcha_image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GST Portal Captcha Verification")
        self.setModal(True)
        self.setFixedSize(400, 260)
        self.captcha_code = ""
        self.refresh_requested = False

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # Title / Instruction
        lbl_info = QLabel("Please enter the letters and numbers shown below:")
        lbl_info.setStyleSheet("color: #94A3B8; font-size: 13px;")
        layout.addWidget(lbl_info)

        # Captcha Image Display Card
        img_card = QFrame()
        img_card.setStyleSheet("background: #FFFFFF; border-radius: 8px; padding: 6px;")
        img_layout = QHBoxLayout(img_card)
        img_layout.setContentsMargins(8, 8, 8, 8)
        img_layout.setAlignment(Qt.AlignCenter)

        self.lbl_image = QLabel()
        pixmap = QPixmap(captcha_image_path)
        if not pixmap.isNull():
            self.lbl_image.setPixmap(pixmap.scaled(220, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.lbl_image.setText("Captcha image preview unavailable")
            self.lbl_image.setStyleSheet("color: #DC2626;")
        img_layout.addWidget(self.lbl_image)
        layout.addWidget(img_card)

        # Input & Submit
        input_row = QHBoxLayout()
        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText("Enter Captcha Code")
        self.txt_code.setMaxLength(10)
        self.txt_code.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.txt_code.setStyleSheet("padding: 8px; font-size: 14px; letter-spacing: 2px;")
        self.txt_code.returnPressed.connect(self.on_submit)
        input_row.addWidget(self.txt_code)

        btn_submit = QPushButton("Verify & Login")
        btn_submit.setStyleSheet("padding: 9px 18px;")
        btn_submit.clicked.connect(self.on_submit)
        input_row.addWidget(btn_submit)
        layout.addLayout(input_row)

        # Footer Actions
        footer_row = QHBoxLayout()
        btn_refresh = QPushButton("↻ Refresh Captcha")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.on_refresh)
        footer_row.addWidget(btn_refresh)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "btn-danger")
        btn_cancel.clicked.connect(self.reject)
        footer_row.addWidget(btn_cancel)
        layout.addLayout(footer_row)

        self.txt_code.setFocus()

    def on_submit(self):
        val = self.txt_code.text().strip()
        if not val:
            QMessageBox.warning(self, "Input Required", "Please enter the captcha code.")
            return
        self.captcha_code = val
        self.accept()

    def on_refresh(self):
        self.refresh_requested = True
        self.accept()


class OtpDialog(QDialog):
    """Modal dialog for WhiteBooks API OTP input."""
    def __init__(self, default_otp="575757", parent=None):
        super().__init__(parent)
        self.setWindowTitle("WhiteBooks API - OTP Verification")
        self.setModal(True)
        self.setFixedSize(400, 240)
        self.otp_code = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        lbl_title = QLabel("Enter OTP Sent to Registered Email")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #93C5FD;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel("If using sandbox environment, the default OTP is 575757.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(lbl_desc)

        input_row = QHBoxLayout()
        self.txt_otp = QLineEdit()
        self.txt_otp.setText(default_otp)
        self.txt_otp.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.txt_otp.setStyleSheet("padding: 8px; letter-spacing: 3px;")
        self.txt_otp.returnPressed.connect(self.on_submit)
        input_row.addWidget(self.txt_otp)

        btn_sandbox = QPushButton("Sandbox Default")
        btn_sandbox.setProperty("class", "btn-secondary")
        btn_sandbox.clicked.connect(lambda: self.txt_otp.setText("575757"))
        input_row.addWidget(btn_sandbox)
        layout.addLayout(input_row)

        btn_row = QHBoxLayout()
        btn_submit = QPushButton("Verify OTP")
        btn_submit.clicked.connect(self.on_submit)
        btn_row.addWidget(btn_submit)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "btn-danger")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        self.txt_otp.setFocus()
        self.txt_otp.selectAll()

    def on_submit(self):
        val = self.txt_otp.text().strip()
        if not val:
            QMessageBox.warning(self, "Input Required", "Please enter the OTP.")
            return
        self.otp_code = val
        self.accept()


# ==============================================================================
# VISUAL PERIOD SELECTOR WIDGET
# ==============================================================================
class PeriodSelectorWidget(QGroupBox):
    """Interactive visual period selector supporting Month, Quarter, FY, and Custom chips."""
    periods_changed = Signal(list)

    MONTHS = [
        ("April", "04", 0), ("May", "05", 0), ("June", "06", 0),
        ("July", "07", 0), ("August", "08", 0), ("September", "09", 0),
        ("October", "10", 0), ("November", "11", 0), ("December", "12", 0),
        ("January", "01", 1), ("February", "02", 1), ("March", "03", 1)
    ]

    def __init__(self, title="Target Period Selection", parent=None):
        super().__init__(title, parent)
        self.selected_periods = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Mode Selection Row
        mode_row = QHBoxLayout()
        self.btn_group = QButtonGroup(self)

        self.rad_quarter = QRadioButton("Full Quarter")
        self.rad_quarter.setChecked(True)
        self.rad_fy = QRadioButton("Full Financial Year")
        self.rad_single = QRadioButton("Single Month")
        self.rad_custom = QRadioButton("Custom Selection")

        for i, rad in enumerate([self.rad_quarter, self.rad_fy, self.rad_single, self.rad_custom]):
            self.btn_group.addButton(rad, i)
            mode_row.addWidget(rad)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Parameter Controls Row
        ctrl_row = QHBoxLayout()

        lbl_fy = QLabel("Financial Year:")
        lbl_fy.setStyleSheet("color: #94A3B8; font-weight: bold;")
        ctrl_row.addWidget(lbl_fy)

        self.combo_fy = QComboBox()
        current_year = 2025
        for y in range(current_year - 3, current_year + 3):
            self.combo_fy.addItem(f"FY {y}-{str(y+1)[2:]}", y)
        self.combo_fy.setCurrentIndex(3)  # FY 2025-26 default
        self.combo_fy.currentIndexChanged.connect(self._update_periods)
        ctrl_row.addWidget(self.combo_fy)

        # Quarter Selector (Visible in Quarter Mode)
        self.lbl_q = QLabel("Quarter:")
        self.lbl_q.setStyleSheet("color: #94A3B8; font-weight: bold;")
        ctrl_row.addWidget(self.lbl_q)

        self.combo_q = QComboBox()
        self.combo_q.addItems(["Q1 (Apr - Jun)", "Q2 (Jul - Sep)", "Q3 (Oct - Dec)", "Q4 (Jan - Mar)"])
        self.combo_q.currentIndexChanged.connect(self._update_periods)
        ctrl_row.addWidget(self.combo_q)

        # Single Month Selector (Visible in Single Month Mode)
        self.lbl_single_m = QLabel("Month:")
        self.lbl_single_m.setStyleSheet("color: #94A3B8; font-weight: bold;")
        ctrl_row.addWidget(self.lbl_single_m)

        self.combo_single_m = QComboBox()
        for name, code, _ in self.MONTHS:
            self.combo_single_m.addItem(name, code)
        self.combo_single_m.currentIndexChanged.connect(self._update_periods)
        ctrl_row.addWidget(self.combo_single_m)

        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Custom Month Chips Grid
        self.chips_frame = QFrame()
        self.chips_frame.setStyleSheet("background: #0F172A; border-radius: 6px; padding: 6px;")
        chips_layout = QGridLayout(self.chips_frame)
        chips_layout.setContentsMargins(6, 6, 6, 6)
        chips_layout.setSpacing(6)

        self.chip_buttons = []
        for idx, (m_name, m_code, offset) in enumerate(self.MONTHS):
            btn = QPushButton(m_name)
            btn.setCheckable(True)
            btn.setProperty("class", "chip-btn")
            btn.clicked.connect(self._update_custom_periods)
            row = idx // 4
            col = idx % 4
            chips_layout.addWidget(btn, row, col)
            self.chip_buttons.append((btn, m_code, offset))

        layout.addWidget(self.chips_frame)

        # Live Summary Badge
        summary_row = QHBoxLayout()
        lbl_sum_title = QLabel("Selected Periods:")
        lbl_sum_title.setStyleSheet("color: #94A3B8; font-weight: bold;")
        summary_row.addWidget(lbl_sum_title)

        self.lbl_summary = QLabel("None")
        self.lbl_summary.setStyleSheet(
            "background: #1E3A8A; color: #93C5FD; font-weight: bold; "
            "padding: 4px 10px; border-radius: 4px; font-size: 12px;"
        )
        summary_row.addWidget(self.lbl_summary)
        summary_row.addStretch()
        layout.addLayout(summary_row)

        # Connect mode changes
        self.btn_group.idClicked.connect(self._on_mode_changed)
        self._on_mode_changed(0)

    def _on_mode_changed(self, mode_id):
        is_quarter = (mode_id == 0)
        is_fy = (mode_id == 1)
        is_single = (mode_id == 2)
        is_custom = (mode_id == 3)

        self.lbl_q.setVisible(is_quarter)
        self.combo_q.setVisible(is_quarter)
        self.lbl_single_m.setVisible(is_single)
        self.combo_single_m.setVisible(is_single)
        self.chips_frame.setVisible(is_custom)

        self._update_periods()

    def _update_periods(self):
        mode_id = self.btn_group.checkedId()
        fy_year = self.combo_fy.currentData()

        if mode_id == 0:  # Quarter
            q_idx = self.combo_q.currentIndex()
            q_name = f"Q{q_idx + 1}"
            self.selected_periods = core.get_quarter_periods(fy_year, q_name)
        elif mode_id == 1:  # Full FY
            self.selected_periods = core.get_fy_periods(fy_year)
        elif mode_id == 2:  # Single Month
            m_code = self.combo_single_m.currentData()
            # Month year adjustment (Jan-Mar are next calendar year)
            m_idx = self.combo_single_m.currentIndex()
            y = fy_year + 1 if m_idx >= 9 else fy_year
            self.selected_periods = [f"{m_code}{y}"]
        elif mode_id == 3:  # Custom
            self._update_custom_periods()
            return

        self._refresh_summary_label()

    def _update_custom_periods(self):
        fy_year = self.combo_fy.currentData()
        periods = []
        for btn, m_code, offset in self.chip_buttons:
            if btn.isChecked():
                y = fy_year + offset
                periods.append(f"{m_code}{y}")
        self.selected_periods = periods
        self._refresh_summary_label()

    def _refresh_summary_label(self):
        if not self.selected_periods:
            self.lbl_summary.setText("No periods selected")
            self.lbl_summary.setStyleSheet(
                "background: #7F1D1D; color: #FCA5A5; font-weight: bold; "
                "padding: 4px 10px; border-radius: 4px;"
            )
        else:
            txt = f"{len(self.selected_periods)} Period(s): {', '.join(self.selected_periods)}"
            self.lbl_summary.setText(txt)
            self.lbl_summary.setStyleSheet(
                "background: #1E3A8A; color: #93C5FD; font-weight: bold; "
                "padding: 4px 10px; border-radius: 4px;"
            )
        self.periods_changed.emit(self.selected_periods)

    def get_selected_periods(self):
        return list(self.selected_periods)


# ==============================================================================
# BACKGROUND THREAD WORKER FOR PORTAL / API / CONVERSION
# ==============================================================================
class DownloaderWorker(QThread):
    sig_log = Signal(str)
    sig_progress = Signal(int, int, str)
    sig_finished = Signal(bool, str)
    sig_captcha_request = Signal(str)
    sig_otp_request = Signal(str)

    def __init__(self, task_type, params, parent=None):
        super().__init__(parent)
        self.task_type = task_type  # 'PORTAL', 'WHITEBOOKS', 'OFFLINE'
        self.params = params
        self._is_stopped = False

        # Thread synchronization events
        self._captcha_event = threading.Event()
        self._captcha_response = ""
        self._otp_event = threading.Event()
        self._otp_response = ""

    def stop(self):
        self._is_stopped = True
        self._captcha_event.set()
        self._otp_event.set()

    def is_stopped(self):
        return self._is_stopped

    def provide_captcha(self, code):
        self._captcha_response = code
        self._captcha_event.set()

    def provide_otp(self, otp):
        self._otp_response = otp
        self._otp_event.set()

    def _captcha_callback(self, image_path):
        self._captcha_event.clear()
        self._captcha_response = ""
        self.sig_captcha_request.emit(image_path)
        self._captcha_event.wait()
        return self._captcha_response

    def _otp_callback(self, default_otp):
        self._otp_event.clear()
        self._otp_response = ""
        self.sig_otp_request.emit(default_otp)
        self._otp_event.wait()
        return self._otp_response

    def run(self):
        try:
            base_dir = self.params.get("base_dir")

            if self.task_type == "PORTAL":
                action = self.params.get("action", "1")
                periods = self.params.get("periods", [])

                downloader = core.DirectGstPortalDownloader(
                    base_dir=base_dir,
                    log_fn=self.sig_log.emit,
                    captcha_fn=self._captcha_callback,
                    stop_check_fn=self.is_stopped
                )

                if not downloader.login():
                    self.sig_finished.emit(False, "GST Portal login failed.")
                    return

                if not periods:
                    self.sig_finished.emit(False, "No valid periods provided.")
                    return

                if action == "1":
                    downloader.batch_trigger_and_collect(
                        periods, trigger_first=True, auto_poll=True,
                        progress_fn=lambda c, t, l: self.sig_progress.emit(c, t, l)
                    )
                elif action == "2":
                    downloader.batch_trigger_and_collect(
                        periods, trigger_first=True, auto_poll=False,
                        progress_fn=lambda c, t, l: self.sig_progress.emit(c, t, l)
                    )
                elif action == "3":
                    downloader.batch_trigger_and_collect(
                        periods, trigger_first=False, auto_poll=True,
                        progress_fn=lambda c, t, l: self.sig_progress.emit(c, t, l)
                    )

                self.sig_finished.emit(True, "Portal operations completed.")

            elif self.task_type == "WHITEBOOKS":
                periods = self.params.get("periods", [])
                downloader = core.WhiteBooksApiDownloader(
                    base_dir=base_dir,
                    log_fn=self.sig_log.emit,
                    otp_fn=self._otp_callback,
                    stop_check_fn=self.is_stopped
                )

                if not downloader.login():
                    self.sig_finished.emit(False, "WhiteBooks API login failed.")
                    return

                try:
                    total = len(periods)
                    for idx, p in enumerate(periods, 1):
                        if self.is_stopped():
                            self.sig_log.emit("[!] Process cancelled by user.")
                            break
                        self.sig_progress.emit(idx, total, f"Downloading Period {p} ({idx}/{total})")
                        downloader.download_period(p)

                    core.Gstr1ExcelConverter.build_consolidated_excel(
                        downloader.output_dir, downloader.gstin, log_fn=self.sig_log.emit
                    )
                    self.sig_finished.emit(True, "WhiteBooks API downloads completed.")
                finally:
                    downloader.logout()

            elif self.task_type == "OFFLINE":
                folder = self.params.get("folder")
                gstin = self.params.get("gstin", "")
                action = self.params.get("action", "both")

                folder_path = Path(folder)
                json_files = sorted(folder_path.glob("GSTR1_*.json"))
                if not json_files:
                    self.sig_log.emit(f"[X] No GSTR1_*.json files found in {folder_path}")
                    self.sig_finished.emit(False, "No JSON files found.")
                    return

                if action in ("convert", "both"):
                    total = len(json_files)
                    for idx, jf in enumerate(json_files, 1):
                        if self.is_stopped():
                            break
                        self.sig_progress.emit(idx, total, f"Converting {jf.name} ({idx}/{total})")
                        core.Gstr1ExcelConverter.convert_json_file(jf, log_fn=self.sig_log.emit)

                if action in ("consolidate", "both") and not self.is_stopped():
                    self.sig_progress.emit(1, 1, "Building Consolidated Master Excel...")
                    core.Gstr1ExcelConverter.build_consolidated_excel(folder_path, gstin, log_fn=self.sig_log.emit)

                self.sig_finished.emit(True, "Offline conversion complete.")

        except Exception as e:
            self.sig_log.emit(f"[X] Worker execution error: {e}")
            self.sig_finished.emit(False, str(e))


# ==============================================================================
# MAIN APPLICATION WINDOW
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unified GSTR-1 Downloader & Excel Converter")
        self.resize(1120, 780)
        self.setMinimumSize(920, 640)
        self.base_dir = core.get_app_dir()

        # Load environment variables
        core.load_environment(self.base_dir)

        self.worker = None

        self._build_ui()
        self._refresh_status_info()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("background: #1E293B; border-radius: 8px; padding: 10px 16px;")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(8, 6, 8, 6)

        title_col = QVBoxLayout()
        lbl_title = QLabel("Unified GSTR-1 Downloader & Excel Master Suite")
        lbl_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF;")
        lbl_subtitle = QLabel("Automated GST Portal Playwright Download • WhiteBooks GSP API • 10-Table Multi-Sheet Excel Engine")
        lbl_subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_subtitle)
        hdr_layout.addLayout(title_col)
        hdr_layout.addStretch()

        # Status Badges
        self.badge_gstin = QLabel("GSTIN: Not Set")
        self.badge_gstin.setStyleSheet("background: #334155; color: #E2E8F0; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        hdr_layout.addWidget(self.badge_gstin)

        main_layout.addWidget(header)

        # Splitter: Tabs (Left / Top) & Console / Results (Right / Bottom)
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(8)

        # Tabs Container
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_portal_tab(), "🌐 Direct GST Portal")
        self.tabs.addTab(self._build_whitebooks_tab(), "⚡ WhiteBooks GSP API")
        self.tabs.addTab(self._build_offline_tab(), "📊 Offline Excel Converter")
        self.tabs.addTab(self._build_settings_tab(), "⚙️ Settings & .env Manager")
        splitter.addWidget(self.tabs)

        # Activity & Console Container
        console_widget = QWidget()
        cons_layout = QVBoxLayout(console_widget)
        cons_layout.setContentsMargins(0, 8, 0, 0)
        cons_layout.setSpacing(8)

        # Console Header Bar
        cons_bar = QHBoxLayout()
        lbl_cons = QLabel("Activity Log & Live Output:")
        lbl_cons.setStyleSheet("font-weight: bold; color: #93C5FD; font-size: 13px;")
        cons_bar.addWidget(lbl_cons)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(220)
        cons_bar.addWidget(self.progress_bar)

        self.lbl_task_status = QLabel("")
        self.lbl_task_status.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        cons_bar.addWidget(self.lbl_task_status)

        cons_bar.addStretch()

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        cons_bar.addWidget(self.chk_autoscroll)

        btn_copy = QPushButton("Copy Log")
        btn_copy.setProperty("class", "btn-secondary")
        btn_copy.clicked.connect(self._copy_log)
        cons_bar.addWidget(btn_copy)

        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("class", "btn-secondary")
        btn_clear.clicked.connect(self._clear_log)
        cons_bar.addWidget(btn_clear)

        btn_open_folder = QPushButton("📂 Open Output Folder")
        btn_open_folder.setProperty("class", "btn-secondary")
        btn_open_folder.clicked.connect(self._open_output_folder)
        cons_bar.addWidget(btn_open_folder)

        cons_layout.addLayout(cons_bar)

        # Console Text Edit
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        cons_layout.addWidget(self.console)

        splitter.addWidget(console_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)

    # --------------------------------------------------------------------------
    # TAB 1: DIRECT GST PORTAL
    # --------------------------------------------------------------------------
    def _build_portal_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 14, 14, 14)

        # Portal Description Card
        desc = QLabel("Automates logging into services.gst.gov.in using Playwright Stealth, solves captcha interactively, queues GSTR-1 offline downloads, polls status, downloads ZIPs, and parses them into structured Excel workbooks.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc)

        # Period Selector
        self.portal_period_selector = PeriodSelectorWidget("Select Target Filing Periods")
        layout.addWidget(self.portal_period_selector)

        # Portal Action Mode
        grp_action = QGroupBox("Portal Workflow Action")
        act_layout = QVBoxLayout(grp_action)
        act_layout.setSpacing(8)

        self.rad_act1 = QRadioButton("1. Trigger Generation for All Selected Periods & Wait / Batch Download (Recommended)")
        self.rad_act1.setChecked(True)
        self.rad_act2 = QRadioButton("2. Trigger Generation Only (Queue on GST server and exit immediately, download later)")
        self.rad_act3 = QRadioButton("3. Download Already-Generated Files Only (Skip triggering, poll ready files)")

        self.portal_act_group = QButtonGroup(self)
        self.portal_act_group.addButton(self.rad_act1, 1)
        self.portal_act_group.addButton(self.rad_act2, 2)
        self.portal_act_group.addButton(self.rad_act3, 3)

        act_layout.addWidget(self.rad_act1)
        act_layout.addWidget(self.rad_act2)
        act_layout.addWidget(self.rad_act3)
        layout.addWidget(grp_action)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.btn_run_portal = QPushButton("🚀 Start Portal Automation Workflow")
        self.btn_run_portal.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        self.btn_run_portal.clicked.connect(self._start_portal_workflow)
        btn_row.addWidget(self.btn_run_portal)

        self.btn_stop_portal = QPushButton("🛑 Stop Process")
        self.btn_stop_portal.setProperty("class", "btn-danger")
        self.btn_stop_portal.setEnabled(False)
        self.btn_stop_portal.clicked.connect(self._stop_current_worker)
        btn_row.addWidget(self.btn_stop_portal)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()
        return tab

    # --------------------------------------------------------------------------
    # TAB 2: WHITEBOOKS GSP API
    # --------------------------------------------------------------------------
    def _build_whitebooks_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 14, 14, 14)

        desc = QLabel("Direct GSP API integration using WhiteBooks. Authenticates via OTP request, queries return filing reference IDs, downloads official GSTR-1 payload documents, and automatically consolidates into master Excel workbooks.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc)

        self.wb_period_selector = PeriodSelectorWidget("Select Target Filing Periods")
        layout.addWidget(self.wb_period_selector)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.btn_run_wb = QPushButton("⚡ Start WhiteBooks API Download & Convert")
        self.btn_run_wb.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        self.btn_run_wb.clicked.connect(self._start_whitebooks_workflow)
        btn_row.addWidget(self.btn_run_wb)

        self.btn_stop_wb = QPushButton("🛑 Stop Process")
        self.btn_stop_wb.setProperty("class", "btn-danger")
        self.btn_stop_wb.setEnabled(False)
        self.btn_stop_wb.clicked.connect(self._stop_current_worker)
        btn_row.addWidget(self.btn_stop_wb)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()
        return tab

    # --------------------------------------------------------------------------
    # TAB 3: OFFLINE EXCEL CONVERTER
    # --------------------------------------------------------------------------
    def _build_offline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 14, 14, 14)

        # Folder Chooser Card
        grp_folder = QGroupBox("Target GSTIN Data Directory")
        f_layout = QHBoxLayout(grp_folder)
        f_layout.setSpacing(10)

        self.txt_offline_folder = QLineEdit()
        self.txt_offline_folder.setPlaceholderText("Select folder containing GSTR1_*.json files...")
        f_layout.addWidget(self.txt_offline_folder)

        btn_browse = QPushButton("Browse Folder...")
        btn_browse.setProperty("class", "btn-secondary")
        btn_browse.clicked.connect(self._browse_offline_folder)
        f_layout.addWidget(btn_browse)

        btn_refresh_files = QPushButton("Scan Files")
        btn_refresh_files.clicked.connect(self._scan_offline_files)
        f_layout.addWidget(btn_refresh_files)

        layout.addWidget(grp_folder)

        # Discovered Files Table
        self.table_files = QTableWidget()
        self.table_files.setColumnCount(3)
        self.table_files.setHorizontalHeaderLabels(["JSON File Name", "File Size", "Last Modified"])
        self.table_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table_files)

        # Offline Action Buttons
        btn_row = QHBoxLayout()
        self.btn_convert_offline = QPushButton("📊 Convert Discovered JSONs to Excel")
        self.btn_convert_offline.clicked.connect(lambda: self._start_offline_workflow("convert"))
        btn_row.addWidget(self.btn_convert_offline)

        self.btn_consolidate_offline = QPushButton("📑 Build Consolidated Master Excel")
        self.btn_consolidate_offline.clicked.connect(lambda: self._start_offline_workflow("consolidate"))
        btn_row.addWidget(self.btn_consolidate_offline)

        self.btn_both_offline = QPushButton("🚀 Run Both (Convert All & Consolidate)")
        self.btn_both_offline.clicked.connect(lambda: self._start_offline_workflow("both"))
        btn_row.addWidget(self.btn_both_offline)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        return tab

    # --------------------------------------------------------------------------
    # TAB 4: SETTINGS & .ENV MANAGER
    # --------------------------------------------------------------------------
    def _build_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 14, 14, 14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(14)

        # GST Portal Credentials
        grp_portal = QGroupBox("Government GST Portal Credentials (Mode 1)")
        p_layout = QGridLayout(grp_portal)
        p_layout.setSpacing(10)

        p_layout.addWidget(QLabel("Portal Username:"), 0, 0)
        self.txt_portal_user = QLineEdit()
        p_layout.addWidget(self.txt_portal_user, 0, 1)

        p_layout.addWidget(QLabel("Portal Password:"), 1, 0)
        self.txt_portal_pass = QLineEdit()
        self.txt_portal_pass.setEchoMode(QLineEdit.Password)
        p_layout.addWidget(self.txt_portal_pass, 1, 1)

        p_layout.addWidget(QLabel("Company GSTIN:"), 2, 0)
        self.txt_gstin = QLineEdit()
        p_layout.addWidget(self.txt_gstin, 2, 1)

        btn_toggle_pass = QPushButton("Show / Hide Passwords")
        btn_toggle_pass.setProperty("class", "btn-secondary")
        btn_toggle_pass.clicked.connect(self._toggle_passwords)
        p_layout.addWidget(btn_toggle_pass, 1, 2)

        c_layout.addWidget(grp_portal)

        # WhiteBooks API Credentials
        grp_wb = QGroupBox("WhiteBooks GSP API Credentials (Mode 2)")
        wb_layout = QGridLayout(grp_wb)
        wb_layout.setSpacing(10)

        wb_layout.addWidget(QLabel("Base URL:"), 0, 0)
        self.txt_wb_url = QLineEdit()
        wb_layout.addWidget(self.txt_wb_url, 0, 1)

        wb_layout.addWidget(QLabel("Client ID:"), 1, 0)
        self.txt_wb_client_id = QLineEdit()
        wb_layout.addWidget(self.txt_wb_client_id, 1, 1)

        wb_layout.addWidget(QLabel("Client Secret:"), 2, 0)
        self.txt_wb_secret = QLineEdit()
        self.txt_wb_secret.setEchoMode(QLineEdit.Password)
        wb_layout.addWidget(self.txt_wb_secret, 2, 1)

        wb_layout.addWidget(QLabel("Registered Email:"), 3, 0)
        self.txt_wb_email = QLineEdit()
        wb_layout.addWidget(self.txt_wb_email, 3, 1)

        wb_layout.addWidget(QLabel("GST Username:"), 4, 0)
        self.txt_wb_gst_user = QLineEdit()
        wb_layout.addWidget(self.txt_wb_gst_user, 4, 1)

        wb_layout.addWidget(QLabel("State Code:"), 5, 0)
        self.txt_wb_state = QLineEdit()
        wb_layout.addWidget(self.txt_wb_state, 5, 1)

        wb_layout.addWidget(QLabel("IP Address:"), 6, 0)
        self.txt_wb_ip = QLineEdit()
        wb_layout.addWidget(self.txt_wb_ip, 6, 1)

        c_layout.addWidget(grp_wb)

        # Save & Actions
        action_row = QHBoxLayout()
        btn_save = QPushButton("💾 Save Configuration to .env")
        btn_save.setStyleSheet("padding: 10px 20px; font-size: 13px;")
        btn_save.clicked.connect(self._save_settings)
        action_row.addWidget(btn_save)

        btn_reload = QPushButton("↻ Reload from .env")
        btn_reload.setProperty("class", "btn-secondary")
        btn_reload.clicked.connect(self._load_settings_into_ui)
        action_row.addWidget(btn_reload)

        action_row.addStretch()
        c_layout.addLayout(action_row)
        c_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self._load_settings_into_ui()
        return tab

    # --------------------------------------------------------------------------
    # SETTINGS LOGIC
    # --------------------------------------------------------------------------
    def _toggle_passwords(self):
        cur = self.txt_portal_pass.echoMode()
        new_mode = QLineEdit.Normal if cur == QLineEdit.Password else QLineEdit.Password
        self.txt_portal_pass.setEchoMode(new_mode)
        self.txt_wb_secret.setEchoMode(new_mode)

    def _load_settings_into_ui(self):
        core.load_environment(self.base_dir)
        self.txt_portal_user.setText(os.getenv("GOVT_GST_LOGIN_NAME") or os.getenv("GST_USERNAME", ""))
        self.txt_portal_pass.setText(os.getenv("GOVT_GST_LOGIN_PASSWORD") or os.getenv("GST_PASSWORD", ""))
        gstin = os.getenv("GSTIN", "").strip()
        self.txt_gstin.setText(gstin)

        self.txt_wb_url.setText(os.getenv("BASE_URL", "https://apisandbox.whitebooks.in"))
        self.txt_wb_client_id.setText(os.getenv("CLIENT_ID", ""))
        self.txt_wb_secret.setText(os.getenv("CLIENT_SECRET", ""))
        self.txt_wb_email.setText(os.getenv("EMAIL", ""))
        self.txt_wb_gst_user.setText(os.getenv("GST_USERNAME") or os.getenv("GOVT_GST_LOGIN_NAME", ""))
        self.txt_wb_state.setText(os.getenv("STATE_CD", "") or (gstin[:2] if gstin else ""))
        self.txt_wb_ip.setText(os.getenv("IP_ADDRESS", "192.168.1.1"))

        # Also set default offline folder
        default_folder = self.base_dir / (gstin or "UNKNOWN_GSTIN")
        self.txt_offline_folder.setText(str(default_folder))
        self._refresh_status_info()

    def _save_settings(self):
        env_content = f"""# ==============================================================================
# GSTR-1 AUTOMATION CONFIGURATION
# ==============================================================================
# MODE 1: DIRECT GOVT GST PORTAL
GOVT_GST_LOGIN_NAME={self.txt_portal_user.text().strip()}
GOVT_GST_LOGIN_PASSWORD={self.txt_portal_pass.text().strip()}
GSTIN={self.txt_gstin.text().strip()}

# MODE 2: WHITEBOOKS GSP API
BASE_URL={self.txt_wb_url.text().strip()}
CLIENT_ID={self.txt_wb_client_id.text().strip()}
CLIENT_SECRET={self.txt_wb_secret.text().strip()}
EMAIL={self.txt_wb_email.text().strip()}
GST_USERNAME={self.txt_wb_gst_user.text().strip()}
STATE_CD={self.txt_wb_state.text().strip()}
IP_ADDRESS={self.txt_wb_ip.text().strip()}
"""
        env_file = self.base_dir / ".env"
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(env_content)
            core.load_environment(self.base_dir)
            self._refresh_status_info()
            QMessageBox.information(self, "Settings Saved", f"Configuration successfully saved to {env_file.name}!")
            self._append_log("[OK] Updated settings saved to .env")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")

    def _refresh_status_info(self):
        gstin = os.getenv("GSTIN", "").strip()
        if gstin:
            self.badge_gstin.setText(f"GSTIN: {gstin}")
            self.badge_gstin.setStyleSheet("background: #1E3A8A; color: #93C5FD; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        else:
            self.badge_gstin.setText("GSTIN: Not Configured")
            self.badge_gstin.setStyleSheet("background: #7F1D1D; color: #FCA5A5; padding: 6px 12px; border-radius: 6px; font-weight: bold;")

    # --------------------------------------------------------------------------
    # OFFLINE SCANNER LOGIC
    # --------------------------------------------------------------------------
    def _browse_offline_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select GSTIN Directory", self.txt_offline_folder.text())
        if folder:
            self.txt_offline_folder.setText(folder)
            self._scan_offline_files()

    def _scan_offline_files(self):
        folder_str = self.txt_offline_folder.text().strip()
        folder = Path(folder_str) if folder_str else self.base_dir
        if not folder.exists():
            self._append_log(f"[X] Directory does not exist: {folder}")
            return

        json_files = sorted(folder.glob("GSTR1_*.json"))
        self.table_files.setRowCount(len(json_files))

        for row, f in enumerate(json_files):
            stat = f.stat()
            size_kb = f"{stat.st_size / 1024:.1f} KB"
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))

            self.table_files.setItem(row, 0, QTableWidgetItem(f.name))
            self.table_files.setItem(row, 1, QTableWidgetItem(size_kb))
            self.table_files.setItem(row, 2, QTableWidgetItem(mtime))

        self._append_log(f"[OK] Discovered {len(json_files)} GSTR-1 JSON file(s) in {folder.name}")

    # --------------------------------------------------------------------------
    # WORKFLOW RUNNERS
    # --------------------------------------------------------------------------
    def _start_portal_workflow(self):
        periods = self.portal_period_selector.get_selected_periods()
        if not periods:
            QMessageBox.warning(self, "Selection Required", "Please select at least one target period.")
            return

        action_id = str(self.portal_act_group.checkedId())
        self._start_worker(
            "PORTAL",
            {"base_dir": str(self.base_dir), "action": action_id, "periods": periods}
        )

    def _start_whitebooks_workflow(self):
        periods = self.wb_period_selector.get_selected_periods()
        if not periods:
            QMessageBox.warning(self, "Selection Required", "Please select at least one target period.")
            return

        self._start_worker(
            "WHITEBOOKS",
            {"base_dir": str(self.base_dir), "periods": periods}
        )

    def _start_offline_workflow(self, action):
        folder = self.txt_offline_folder.text().strip()
        if not folder or not Path(folder).exists():
            QMessageBox.warning(self, "Folder Required", "Please select a valid directory containing JSON files.")
            return

        gstin = os.getenv("GSTIN", "").strip() or Path(folder).name
        self._start_worker(
            "OFFLINE",
            {"folder": folder, "gstin": gstin, "action": action}
        )

    def _start_worker(self, task_type, params):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Task In Progress", "A task is already running. Please wait or stop it first.")
            return

        self.btn_run_portal.setEnabled(False)
        self.btn_stop_portal.setEnabled(True)
        self.btn_run_wb.setEnabled(False)
        self.btn_stop_wb.setEnabled(True)
        self.btn_convert_offline.setEnabled(False)
        self.btn_consolidate_offline.setEnabled(False)
        self.btn_both_offline.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_task_status.setText("Initializing...")

        self.worker = DownloaderWorker(task_type, params, self)
        self.worker.sig_log.connect(self._append_log)
        self.worker.sig_progress.connect(self._on_progress)
        self.worker.sig_captcha_request.connect(self._handle_captcha_request)
        self.worker.sig_otp_request.connect(self._handle_otp_request)
        self.worker.sig_finished.connect(self._on_worker_finished)
        self.worker.start()

    def _stop_current_worker(self):
        if self.worker and self.worker.isRunning():
            self._append_log("[!] Stopping current process...")
            self.worker.stop()
            self.lbl_task_status.setText("Stopping...")

    def _on_progress(self, current, total, label):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.lbl_task_status.setText(label)

    def _on_worker_finished(self, success, message):
        self.btn_run_portal.setEnabled(True)
        self.btn_stop_portal.setEnabled(False)
        self.btn_run_wb.setEnabled(True)
        self.btn_stop_wb.setEnabled(False)
        self.btn_convert_offline.setEnabled(True)
        self.btn_consolidate_offline.setEnabled(True)
        self.btn_both_offline.setEnabled(True)

        self.progress_bar.setVisible(False)
        self.lbl_task_status.setText("Ready")

        if success:
            self._append_log(f"\n[OK] {message}")
            QMessageBox.information(self, "Completed", message)
        else:
            self._append_log(f"\n[X] {message}")
            QMessageBox.critical(self, "Execution Stopped", message)

        self._scan_offline_files()

    # --------------------------------------------------------------------------
    # CAPTCHA & OTP MODAL HANDLERS
    # --------------------------------------------------------------------------
    @Slot(str)
    def _handle_captcha_request(self, image_path):
        dlg = CaptchaDialog(image_path, self)
        if dlg.exec() == QDialog.Accepted:
            if dlg.refresh_requested:
                self.worker.provide_captcha("__REFRESH__")
            else:
                self.worker.provide_captcha(dlg.captcha_code)
        else:
            self.worker.provide_captcha("")

    @Slot(str)
    def _handle_otp_request(self, default_otp):
        dlg = OtpDialog(default_otp, self)
        if dlg.exec() == QDialog.Accepted:
            self.worker.provide_otp(dlg.otp_code)
        else:
            self.worker.provide_otp("")

    # --------------------------------------------------------------------------
    # CONSOLE & LOGGING UTILITIES
    # --------------------------------------------------------------------------
    def _append_log(self, text):
        # Format colored output based on prefix
        color = "#E2E8F0"
        if "[OK]" in text:
            color = "#34D399"  # Emerald Green
        elif "[WAIT]" in text or "[QUEUE]" in text or "[TIP]" in text:
            color = "#FBBF24"  # Amber
        elif "[X]" in text:
            color = "#F87171"  # Crimson Red
        elif "===" in text or "---" in text:
            color = "#38BDF8"  # Cyan Header

        html = f"<div style='color: {color}; margin: 1px 0;'>{text.replace('\n', '<br>')}</div>"
        self.console.append(html)

        if self.chk_autoscroll.isChecked():
            self.console.moveCursor(QTextCursor.End)

    def _copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.console.toPlainText())
        QMessageBox.information(self, "Copied", "Log contents copied to clipboard!")

    def _clear_log(self):
        self.console.clear()

    def _open_output_folder(self):
        gstin = os.getenv("GSTIN", "").strip() or "UNKNOWN_GSTIN"
        folder = self.base_dir / gstin
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open folder: {e}")


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
