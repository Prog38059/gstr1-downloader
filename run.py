"""
Unified GSTR-1 Downloader & Excel Converter Launcher
- Default: Launches modern PySide6 GUI
- Argument '--cli': Launches original interactive CLI mode
"""
import sys

if __name__ == "__main__":
    if "--cli" in sys.argv:
        import core_downloader
        core_downloader.main()
    else:
        import gui_app
        gui_app.main()
