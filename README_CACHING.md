# Blockchain Explorer with Redis Caching

A comprehensive blockchain explorer application with Redis caching, featuring both address and block viewers with intelligent caching and force refresh capabilities.

## 🚀 Features

### Core Functionality
- **Address Viewer** - Search and view blockchain transactions by address
- **Block Viewer** - Search and view block details and transactions by block hash
- **Cross-Navigation** - Clickable links between transactions and blocks
- **Modern UI** - Responsive design with beautiful gradients and animations

### Caching System
- **Redis Integration** - High-performance caching with Redis
- **Smart Caching** - Automatic cache with 5-minute TTL
- **Force Refresh** - Checkbox to bypass cache when needed
- **Cache Statistics** - Real-time cache status and performance metrics
- **Cache Management** - Clear cache functionality via API

### Technical Features
- **Flask Backend** - Lightweight Python web server
- **API Proxy** - Secure external API integration
- **Error Handling** - Comprehensive error handling and validation
- **CORS Support** - Cross-Origin Resource Sharing enabled
- **Health Monitoring** - Health check endpoints with cache status

## 📋 Prerequisites

- Python 3.7 or higher
- Redis server (optional but recommended)
- pip (Python package installer)

## 🛠️ Installation

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install and Start Redis (Optional)
```bash
# On macOS with Homebrew
brew install redis
brew services start redis

# On Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# On Windows
# Download Redis from https://redis.io/download
```

### 3. Verify Redis Installation (Optional)
```bash
redis-cli ping
# Should return: PONG
```

## 🚀 Running the Application

### 1. Start the Server
```bash
python app.py
```

### 2. Access the Application
- **Address Viewer**: http://localhost:5000
- **Block Viewer**: http://localhost:5000/block
- **Health Check**: http://localhost:5000/health
- **Cache Stats**: http://localhost:5000/api/cache/stats

## 🧪 Testing

### Run the Caching Test Suite
```bash
python test_caching.py
```

This will test:
- Server health and cache status
- Address API caching (first and second calls)
- Block API caching (first and second calls)
- Force refresh functionality
- Cache statistics
- Cache clear functionality

### Manual Testing
1. **Test Caching**: Search for the same address/block twice and observe faster response times
2. **Test Force Refresh**: Check the "Force refresh" checkbox and search again
3. **Test Cache Status**: Observe the cache status indicator in the UI
4. **Test Navigation**: Click on block hashes in transactions to navigate to block viewer

## 📊 API Endpoints

### Core Endpoints
- `GET /` - Address viewer interface
- `GET /block` - Block viewer interface
- `GET /health` - Health check with cache status

### API Endpoints
- `GET /api/address/<address>/txs` - Get transactions for address
- `GET /api/block/<block_hash>/txs` - Get transactions for block
- `GET /api/cache/stats` - Get cache statistics
- `POST /api/cache/clear` - Clear all cache entries

### Query Parameters
- `?force_refresh=true` - Bypass cache and fetch fresh data

## ⚙️ Configuration

### Redis Configuration
Edit the Redis settings in `app.py`:
```python
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
CACHE_TTL = 300  # 5 minutes cache TTL
```

### API Configuration
Update the external API URLs in `app.py`:
```python
ADDRESS_API_BASE_URL = "http://157.180.8.224:3000/address"
BLOCK_API_BASE_URL = "http://157.180.8.224:3000/block"
```

## 🔧 Cache Management

### Cache Statistics
The application provides real-time cache statistics:
- **Status**: Enabled/Disabled/Error
- **Keys**: Number of cached items
- **Memory Usage**: Redis memory consumption
- **Hit Rate**: Cache hit percentage

### Cache Operations
- **Automatic Caching**: All API responses are cached automatically
- **TTL**: Cache entries expire after 5 minutes
- **Force Refresh**: Users can bypass cache when needed
- **Cache Clear**: Administrators can clear all cache entries

## 🎨 UI Features

### Address Viewer
- Address search with validation
- Transaction details with inputs/outputs
- Clickable block hash links
- Force refresh checkbox
- Cache status indicator
- JSON viewer for raw data

### Block Viewer
- Block hash search with validation
- Block information display
- Transaction list with details
- Clickable transaction links
- Force refresh checkbox
- Cache status indicator

### Navigation
- Seamless navigation between viewers
- URL parameter support for direct links
- Breadcrumb-style navigation

## 🚨 Error Handling

### Graceful Degradation
- **Redis Unavailable**: Application continues without caching
- **API Errors**: Comprehensive error messages and suggestions
- **Network Issues**: Timeout handling and retry logic
- **Validation**: Input validation with helpful error messages

### Error Types
- **Validation Errors**: Invalid address/block hash format
- **Connection Errors**: External API unavailable
- **Timeout Errors**: Request timeout handling
- **Cache Errors**: Redis connection issues

## 📈 Performance

### Caching Benefits
- **Faster Response Times**: Cached responses are significantly faster
- **Reduced API Load**: Fewer requests to external APIs
- **Better User Experience**: Instant responses for cached data
- **Cost Savings**: Reduced external API usage

### Performance Monitoring
- Response time tracking
- Cache hit rate monitoring
- Memory usage statistics
- Error rate tracking

## 🔒 Security

### API Security
- Input validation and sanitization
- Rate limiting considerations
- CORS configuration
- Error message sanitization

### Cache Security
- Cache key isolation
- TTL-based expiration
- Memory usage limits
- Access control

## 🐛 Troubleshooting

### Common Issues

#### Redis Connection Issues
```
⚠️ Redis not available: [Errno 61] Connection refused
```
**Solution**: Start Redis server or run without caching

#### API Connection Issues
```
❌ Error Fetching Data: Connection error
```
**Solution**: Check external API availability and network connection

#### Cache Not Working
```
Cache: ❌ Disabled (Redis not available)
```
**Solution**: Install and start Redis server

### Debug Mode
Enable debug mode in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

## 📝 Development

### Project Structure
```
explorer/
├── app.py                 # Main Flask application
├── block-viewer.html      # Block viewer interface
├── requirements.txt       # Python dependencies
├── test_caching.py        # Caching test suite
├── README_CACHING.md      # This file
└── README.md             # Basic README
```

### Adding New Features
1. Update the Flask routes in `app.py`
2. Add corresponding HTML templates
3. Update the JavaScript functions
4. Add tests to `test_caching.py`
5. Update this documentation

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Run the test suite: `python test_caching.py`
3. Check server logs for error details
4. Verify Redis and external API availability

---

**Happy Exploring! 🚀**
