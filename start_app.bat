@echo off
title Lil Mian Command Center
cd /d "C:\Users\Admin\Desktop\AwwMian_Command_Center"

echo [1/2] Starting Lil Mian Discord Bot...
start "Lil Mian Discord Bot" cmd /k "cd /d C:\Users\Admin\Desktop\AwwMian_Command_Center && python bot.py"

echo [2/2] Starting Real-Time Creator Dashboard in Browser...
python -m streamlit run dashboard.py