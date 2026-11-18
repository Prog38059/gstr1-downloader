@echo off
title Unified GSTR-1 Downloader & Excel Converter
cd /d "%~dp0"
python run.py
if errorlevel 1 pause
