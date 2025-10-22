# 🚀 Quick Start Guide

## What You Have

This package includes a complete Flask backend server that:
- Serves a beautiful address viewer web interface
- Acts as a proxy to fetch blockchain transaction data
- Handles errors gracefully
- Includes CORS support for API calls

## Files Included

📄 **app.py** - Main Flask server application
📄 **requirements.txt** - Python dependencies
📄 **README.md** - Detailed documentation
📄 **start.sh** - Linux/Mac startup script
📄 **start.bat** - Windows startup script
📄 **address-viewer.html** - Standalone HTML (optional, embedded in app.py)

## How to Run (Choose One Method)

### Method 1: Easy Start (Recommended)

**On Linux/Mac:**
```bash
./start.sh
```

**On Windows:**
```
start.bat
```

### Method 2: Manual Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python app.py
```

### Method 3: With Virtual Environment (Best Practice)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
```

## Access the Application

Once running, open your browser and go to:
```
http://localhost:5000
```

## How to Use

1. Enter a blockchain address in the input box
2. Click "Search" or press Enter
3. View all transactions for that address
4. Click "View Raw JSON" to see full transaction details

## API Endpoints

- `GET /` - Main web interface
- `GET /api/address/{address}/txs` - Get transactions for an address
- `GET /health` - Server health check

## Architecture

```
User Browser
     ↓
  Flask Server (localhost:5000)
     ↓
  External API (http://157.180.8.224:3000)
     ↓
  Transaction Data
```

## Benefits of Using the Backend

✅ **Security** - API calls go through your server
✅ **Error Handling** - Better error messages and logging
✅ **CORS** - No cross-origin issues
✅ **Caching** - Can add caching later if needed
✅ **Rate Limiting** - Can add rate limiting if needed
✅ **Monitoring** - Can add analytics and logging

## Troubleshooting

**Port already in use?**
Edit `app.py` and change the port:
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Changed from 5000
```

**Dependencies not installing?**
Make sure you have Python 3.7+ installed:
```bash
python --version
```

**Can't connect to external API?**
Check that http://157.180.8.224:3000 is accessible from your network.

## Next Steps

- Add authentication if needed
- Implement caching with Redis
- Add rate limiting
- Deploy to production (Heroku, AWS, etc.)
- Add database to store transactions

Enjoy! 🎉
