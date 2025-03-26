@echo off
echo Starting Price Tracker at %date% %time%

:: Change to the script directory
cd /d "%~dp0"

:: Activate the virtual environment (create it first with: python -m venv venv)
call venv\Scripts\activate

:: Run the price checker
python app\tasks\check_prices.py --check-all

:: Log completion
echo Price Tracker completed at %date% %time%

:: Deactivate virtual environment
call venv\Scripts\deactivate

:: Pause only if run manually (not via Task Scheduler)
if not defined SCHEDULED_TASK pause 