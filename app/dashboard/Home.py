"""
EstateIQ Master Dashboard Entrypoint (app/dashboard/Home.py).
Serves as the canonical Streamlit entrypoint referenced in EstateIQ_Final_Round_Implementation_Report.pdf.
Delegates to master app.py.
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Execute master Streamlit application
with open(BASE_DIR / "app.py", "r", encoding="utf-8") as f:
    code = f.read()

exec(code, {"__name__": "__main__", "__file__": str(BASE_DIR / "app.py")})
