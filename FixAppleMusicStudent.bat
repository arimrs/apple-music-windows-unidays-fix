@echo off
chcp 65001 >nul
title Apple Music Windows + UNiDAYS One-Click Fix v1.0.0
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OneClickFix.ps1" %*
pause
