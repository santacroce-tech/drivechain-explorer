@echo off
echo ==============================================
echo   Address Viewer Backend Server
echo ==============================================
echo.
echo Installing dependencies...
pip install Flask flask-cors requests
echo.
echo Starting server...
echo.
python app.py
pause
