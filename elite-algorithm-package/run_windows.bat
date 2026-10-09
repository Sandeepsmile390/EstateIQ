@echo off
echo =========================================================================
echo EstateIQ Elite Algorithm Package -- Metric Evaluation ^& Chart Generator
echo =========================================================================
echo.

set PYTHONPATH=%~dp0..;%~dp0

python run_evaluation.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Elite Algorithm Evaluation completed successfully!
    echo Reports generated in: reports/
    echo Charts generated in:  charts/
) else (
    echo.
    echo [ERROR] Evaluation failed with code %ERRORLEVEL%.
)
pause
