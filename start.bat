@echo off
REM Instala las dependencias solo si faltan, luego abre la app.
python -c "import PySide6, sympy" 2>nul || python -m pip install -r requirements.txt
python main.py
