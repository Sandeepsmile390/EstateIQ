#!/bin/bash
echo "========================================================================="
echo "EstateIQ Elite Algorithm Package -- Metric Evaluation & Chart Generator"
echo "========================================================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
export PYTHONPATH="$SCRIPT_DIR/..:$SCRIPT_DIR"

python3 run_evaluation.py

if [ $? -eq 0 ]; then
    echo ""
    echo "[SUCCESS] Elite Algorithm Evaluation completed successfully!"
    echo "Reports generated in: reports/"
    echo "Charts generated in:  charts/"
else
    echo ""
    echo "[ERROR] Evaluation failed."
    exit 1
fi
