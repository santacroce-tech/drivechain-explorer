# Address Viewer Backend

A Flask-based backend server that serves an address viewer web application and proxies API requests to fetch blockchain transaction data.

## Features

✅ **Flask Backend** - Lightweight Python web server
✅ **API Proxy** - Securely fetches data from external blockchain API
✅ **Embedded HTML** - Serves the frontend directly
✅ **Error Handling** - Comprehensive error handling and validation
✅ **CORS Enabled** - Cross-Origin Resource Sharing support
✅ **Health Check** - Endpoint to monitor server status

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install Flask flask-cors requests
```

## Running the Server

1. **Start the server:**
```bash
python app.py
```

2. **Access the application:**
   - Open your browser and go to: http://localhost:5000
   - The server will be running on all network interfaces (0.0.0.0:5000)

3. **Health check:**
   - Visit: http://localhost:5000/health

## API Endpoints

### `GET /`
Serves the main HTML address viewer interface.

### `GET /api/address/<address>/txs`
Fetches transactions for a given blockchain address.

**Parameters:**
- `address` (path parameter) - The blockchain address to query

**Example:**
```
GET http://localhost:5000/api/address/0x1234567890abcdef/txs
```

**Response:**
```json
[
  {
    "hash": "0xabc...",
    "blockNumber": 12345,
    "from": "0x123...",
    "to": "0x456...",
    "value": "1000000000000000000",
    "timestamp": 1234567890
  }
]
```

### `GET /health`
Returns server health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-22T10:30:00",
  "api_base_url": "http://157.180.8.224:3000/address"
}
```

## Configuration

You can modify the external API URL by changing the `API_BASE_URL` variable in `app.py`:

```python
API_BASE_URL = "http://157.180.8.224:3000/address"
```

## Error Handling

The backend handles various error scenarios:
- Invalid address format (400)
- Connection errors (503)
- Request timeouts (504)
- HTTP errors from external API
- Internal server errors (500)

## Development Mode

The server runs in debug mode by default, which provides:
- Auto-reload on code changes
- Detailed error messages
- Interactive debugger

To disable debug mode for production:
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

## Production Deployment

For production, consider using a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or with Waitress (Windows-compatible):
```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

## Project Structure

```
.
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Technologies Used

- **Flask** - Web framework
- **Flask-CORS** - Cross-origin resource sharing
- **Requests** - HTTP library for API calls

## License

MIT License

## Support

For issues or questions, please check the error messages in the browser console or server logs.
