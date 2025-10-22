#!/bin/bash

echo "=============================================="
echo "  Address Viewer Backend Server"
echo "=============================================="
echo ""
echo "Installing dependencies..."
pip install -q Flask flask-cors requests --break-system-packages

echo ""
echo "Starting server..."
echo ""

python app.py
