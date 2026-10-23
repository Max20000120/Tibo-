@echo off
chcp 65001 >nul
title Codex 重置通知機器人

echo ========================================================
echo        Codex 額度重置監控機器人 (Tibo Notifier)
echo ========================================================
echo.

:: 檢查 python 是否存在
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python，請先安裝 Python 並將其加入系統 PATH！
    pause
    exit /b 1
)

:: 啟動輪詢腳本
python check_resets.py --loop
if errorlevel 1 (
    echo.
    echo 程式異常結束。
    pause
)
