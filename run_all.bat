@echo off
REM ==================================================================
REM run_all.bat  -  rebuilds everything in one go:
REM   fake data  ->  raw  ->  staging  ->  audit tables  ->  hiring pipeline
REM Double-click this file, or type  .\run_all.bat  in the VS Code terminal.
REM Then open Power BI and click Refresh.
REM ==================================================================

cd /d "%~dp0"
set PSQL="C:\Program Files\PostgreSQL\18\bin\psql.exe"

set /p PGPASSWORD=Type your Postgres password and press Enter:
echo.

echo [1/5] Making the fake data...
python generate_data.py || goto :failed

echo.
echo [2/5] Loading the raw files into Postgres...
%PSQL% -U postgres -d hr_portfolio -q -v ON_ERROR_STOP=1 -f sql\01_load_raw.sql || goto :failed

echo [3/5] Cleaning them into staging...
%PSQL% -U postgres -d hr_portfolio -q -v ON_ERROR_STOP=1 -f sql\02_staging.sql || goto :failed

echo [4/5] Building the audit tables (every row below should say MATCH)...
%PSQL% -U postgres -d hr_portfolio -q -v ON_ERROR_STOP=1 -f sql\03_audit_checks.sql || goto :failed

echo [5/5] Building the hiring pipeline tables (every row should say MATCH)...
%PSQL% -U postgres -d hr_portfolio -q -v ON_ERROR_STOP=1 -f sql\04_pipeline.sql || goto :failed

echo.
echo Done. Open Power BI and click Home, then Refresh.
pause
exit /b 0

:failed
echo.
echo Something failed. Scroll up and read the first ERROR line.
pause
exit /b 1
