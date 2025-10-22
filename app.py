from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import requests
import redis
import json
import hashlib
from datetime import datetime, timedelta
import binascii
import threading
import time

def calculate_megahash(difficulty):
    """
    Convert Bitcoin difficulty to megahash per second (MH/s)
    
    Formula: MH/s = Difficulty × 2^32 / (600 × 10^6)
    Where:
    - Difficulty is the Bitcoin difficulty value
    - 2^32 is the base for difficulty calculation
    - 600 seconds is the average block time
    - 10^6 converts to megahash (million hashes per second)
    """
    try:
        if difficulty is None or difficulty == 0:
            return 0
        
        # Convert difficulty to float if it's a string
        if isinstance(difficulty, str):
            difficulty = float(difficulty)
        
        # Calculate megahash: Difficulty × 2^32 / (600 × 10^6)
        megahash = (difficulty * (2**32)) / (600 * (10**6))
        
        # Round to 2 decimal places for display
        return round(megahash, 2)
    except (ValueError, TypeError):
        return 0

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# API Configuration
ADDRESS_API_BASE_URL = "http://157.180.8.224:3000/address"
BLOCK_API_BASE_URL = "http://157.180.8.224:3000/block"
TX_API_BASE_URL = "http://157.180.8.224:3000/tx"
BLOCKS_API_BASE_URL = "http://157.180.8.224:3000/blocks"
MEMPOOL_API_BASE_URL = "http://157.180.8.224:3000/mempool"

# Redis Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
CACHE_TTL = 300  # 5 minutes cache TTL
PRICE_CACHE_TTL = 60  # 1 minute cache TTL for Bitcoin price

# Initialize Redis connection
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
    print("✅ Redis connection established")
except Exception as e:
    print(f"⚠️ Redis not available: {e}")
    print("   Caching will be disabled")
    REDIS_AVAILABLE = False
    redis_client = None

# Bitcoin Price Configuration
BITCOIN_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
BITCOIN_PRICE_CACHE_KEY = "bitcoin_price_usd"
current_bitcoin_price = None
price_update_thread = None

def get_cache_key(api_type, identifier):
    """Generate a cache key for the given API type and identifier"""
    return f"blockchain_explorer:{api_type}:{hashlib.md5(identifier.encode()).hexdigest()}"

def get_from_cache(cache_key):
    """Retrieve data from Redis cache"""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"Cache read error: {e}")
    return None

def set_cache(cache_key, data, ttl=CACHE_TTL):
    """Store data in Redis cache with TTL"""
    if not REDIS_AVAILABLE:
        return False
    
    try:
        redis_client.setex(cache_key, ttl, json.dumps(data))
        return True
    except Exception as e:
        print(f"Cache write error: {e}")
        return False

def get_cache_stats():
    """Get cache statistics"""
    if not REDIS_AVAILABLE:
        return {"status": "disabled", "reason": "Redis not available"}
    
    try:
        info = redis_client.info()
        return {
            "status": "enabled",
            "keys": redis_client.dbsize(),
            "memory_usage": info.get('used_memory_human', 'N/A'),
            "hit_rate": info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def fetch_bitcoin_price():
    """Fetch Bitcoin price from external API"""
    try:
        response = requests.get(BITCOIN_PRICE_API_URL, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        price_usd = float(data['bitcoin']['usd'])
        
        # Store in Redis cache
        if REDIS_AVAILABLE:
            price_data = {
                'price_usd': price_usd,
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }
            redis_client.setex(BITCOIN_PRICE_CACHE_KEY, PRICE_CACHE_TTL, json.dumps(price_data))
            print(f"💰 Bitcoin price updated: ${price_usd:,.2f} USD")
        
        return price_usd
        
    except Exception as e:
        print(f"❌ Error fetching Bitcoin price: {e}")
        return None

def get_bitcoin_price():
    """Get Bitcoin price from cache or fetch if not available"""
    global current_bitcoin_price
    
    # Try to get from Redis cache first
    if REDIS_AVAILABLE:
        try:
            cached_price_data = redis_client.get(BITCOIN_PRICE_CACHE_KEY)
            if cached_price_data:
                price_data = json.loads(cached_price_data)
                current_bitcoin_price = price_data['price_usd']
                return current_bitcoin_price
        except Exception as e:
            print(f"Cache read error for Bitcoin price: {e}")
    
    # If not in cache, fetch from API
    price = fetch_bitcoin_price()
    if price:
        current_bitcoin_price = price
    return current_bitcoin_price

def price_update_worker():
    """Background worker to update Bitcoin price periodically"""
    while True:
        try:
            fetch_bitcoin_price()
            time.sleep(60)  # Update every minute
        except Exception as e:
            print(f"Price update worker error: {e}")
            time.sleep(60)  # Wait before retrying

def start_price_updater():
    """Start the background price update thread"""
    global price_update_thread
    if price_update_thread is None or not price_update_thread.is_alive():
        price_update_thread = threading.Thread(target=price_update_worker, daemon=True)
        price_update_thread.start()
        print("💰 Bitcoin price updater started")

def calculate_transaction_usd_value(transaction_data):
    """Calculate USD value for a transaction based on Bitcoin price at transaction time"""
    try:
        bitcoin_price = get_bitcoin_price()
        if not bitcoin_price:
            return None
        
        # Get transaction timestamp
        status = transaction_data.get('status', {})
        block_time = status.get('block_time')
        
        if not block_time:
            return None
        
        # For now, we'll use current price as historical price data is complex
        # In a production system, you'd want to fetch historical prices
        
        total_value_satoshis = 0
        
        # Calculate total value from outputs
        vout = transaction_data.get('vout', [])
        for output in vout:
            total_value_satoshis += output.get('value', 0)
        
        # Convert satoshis to BTC (1 BTC = 100,000,000 satoshis)
        total_value_btc = total_value_satoshis / 100000000
        
        # Calculate USD value
        usd_value = total_value_btc * bitcoin_price
        
        return {
            'total_satoshis': total_value_satoshis,
            'total_btc': total_value_btc,
            'usd_value': usd_value,
            'bitcoin_price_usd': bitcoin_price,
            'calculation_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error calculating USD value: {e}")
        return None

def decode_coinbase_message(scriptsig_hex):
    """
    Decode coinbase message from scriptsig hex string
    """
    try:
        if not scriptsig_hex:
            return "N/A"
        
        # Remove any whitespace
        scriptsig_hex = scriptsig_hex.strip()
        
        # Convert hex to bytes
        scriptsig_bytes = bytes.fromhex(scriptsig_hex)
        
        # The coinbase message is typically after the first few bytes
        # Format: [length][message_bytes]
        if len(scriptsig_bytes) < 2:
            return "Invalid coinbase data"
        
        # Skip the first byte (length indicator) and try to decode as text
        message_bytes = scriptsig_bytes[1:]
        
        # Try to decode as UTF-8
        try:
            decoded_text = message_bytes.decode('utf-8', errors='ignore')
            # Clean up the text - remove non-printable characters except spaces
            cleaned_text = ''.join(char if char.isprintable() or char.isspace() else '' for char in decoded_text)
            return cleaned_text.strip() if cleaned_text.strip() else "Empty message"
        except:
            # If UTF-8 fails, try to decode as ASCII
            try:
                decoded_text = message_bytes.decode('ascii', errors='ignore')
                cleaned_text = ''.join(char if char.isprintable() or char.isspace() else '' for char in decoded_text)
                return cleaned_text.strip() if cleaned_text.strip() else "Empty message"
            except:
                return "Binary data (not text)"
                
    except Exception as e:
        return f"Decode error: {str(e)}"

# HTML Template (embedded in Python)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Address Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 0.95em;
        }

        .nav-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 15px;
        }

        .nav-btn {
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 600;
            color: white;
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }

        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
            transform: translateY(-2px);
        }

        .search-section {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }

        .input-group {
            display: flex;
            gap: 10px;
            max-width: 800px;
            margin: 0 auto;
        }

        .search-options {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-top: 15px;
            justify-content: center;
        }

        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .checkbox-wrapper input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        .checkbox-wrapper label {
            font-size: 14px;
            color: #666;
            cursor: pointer;
            user-select: none;
        }

        .input-wrapper {
            flex: 1;
            position: relative;
        }

        input[type="text"] {
            width: 100%;
            padding: 14px 20px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-family: 'Courier New', monospace;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        button {
            padding: 14px 30px;
            font-size: 16px;
            font-weight: 600;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .content {
            padding: 30px;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error {
            background: #fee;
            border-left: 4px solid #f44;
            padding: 20px;
            border-radius: 8px;
            color: #c33;
            margin: 20px 0;
        }

        .error-title {
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 1.1em;
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
        }

        .results-count {
            font-size: 1.2em;
            color: #333;
            font-weight: 600;
        }

        .transaction-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }

        .transaction-card:hover {
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
        }

        .tx-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #f0f0f0;
        }

        .tx-hash {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #667eea;
            font-weight: 600;
            word-break: break-all;
            flex: 1;
            margin-right: 15px;
        }

        .tx-time {
            color: #666;
            font-size: 0.85em;
            white-space: nowrap;
        }

        .tx-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .detail-item {
            display: flex;
            flex-direction: column;
        }

        .detail-label {
            font-size: 0.8em;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
            font-weight: 600;
        }

        .detail-value {
            font-size: 0.95em;
            color: #333;
            font-family: 'Courier New', monospace;
            word-break: break-all;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .status-confirmed {
            background: #d4edda;
            color: #155724;
        }

        .status-pending {
            background: #fff3cd;
            color: #856404;
        }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }

        .no-results-icon {
            font-size: 4em;
            margin-bottom: 20px;
            opacity: 0.5;
        }

        .json-viewer {
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            max-height: 300px;
            overflow: auto;
        }

        .json-content {
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .toggle-json {
            background: #6c757d;
            padding: 8px 16px;
            font-size: 0.85em;
            margin-top: 10px;
        }

        .section-header {
            margin: 20px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }

        .section-header h3 {
            color: #333;
            font-size: 1.1em;
            margin: 0;
        }

        .inputs-outputs {
            margin: 15px 0;
        }

        .io-item {
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 10px;
        }

        .io-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #ddd;
        }

        .io-header strong {
            color: #333;
            font-size: 0.95em;
        }

        .coinbase-badge {
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
        }

        .value-badge {
            background: #007bff;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
        }

        .io-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }

        .io-details .detail-item {
            margin-bottom: 0;
        }

        .io-details .detail-label {
            font-size: 0.75em;
            color: #666;
        }

        .io-details .detail-value {
            font-size: 0.85em;
            color: #333;
        }

        .clickable-link {
            color: #667eea;
            cursor: pointer;
            text-decoration: underline;
            transition: color 0.3s ease;
        }

        .clickable-link:hover {
            color: #5a6fd8;
        }

        @media (max-width: 768px) {
            .input-group {
                flex-direction: column;
            }

            .tx-header {
                flex-direction: column;
            }

            .tx-hash {
                margin-bottom: 10px;
                margin-right: 0;
            }

            .tx-details {
                grid-template-columns: 1fr;
            }

            .io-details {
                grid-template-columns: 1fr;
            }

            .io-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 5px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Address Viewer</h1>
            <p>Enter an address to view all associated transactions</p>
            <div class="nav-buttons">
                <a href="/" class="nav-btn">🔍 Address Viewer</a>
                <a href="/block" class="nav-btn">🧱 Block Viewer</a>
                <a href="/transaction" class="nav-btn">🔗 Transaction Viewer</a>
                <a href="/latest-blocks" class="nav-btn">📋 Latest Blocks</a>
                <a href="/mempool" class="nav-btn">💾 Mempool</a>
                <a href="/details" class="nav-btn">💰 Pricing Details</a>
            </div>
        </div>

        <div class="search-section">
            <div class="input-group">
                <div class="input-wrapper">
                    <input 
                        type="text" 
                        id="addressInput" 
                        placeholder="Enter blockchain address (e.g., 0x123...)" 
                        autocomplete="off"
                    />
                </div>
                <button id="searchBtn" onclick="fetchTransactions()">Search</button>
            </div>
            <div class="search-options">
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="forceRefresh" />
                    <label for="forceRefresh">🔄 Force refresh (bypass cache)</label>
                </div>
                <div class="checkbox-wrapper">
                    <span id="cacheStatus" style="font-size: 12px; color: #888;">Cache: Loading...</span>
                </div>
            </div>
        </div>

        <div class="content">
            <div id="results"></div>
        </div>
    </div>

    <script>
        // Use relative URL to call our backend
        const API_BASE_URL = '/api/address';
        
        // Allow Enter key to trigger search
        document.getElementById('addressInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                fetchTransactions();
            }
        });

        async function fetchTransactions() {
            const address = document.getElementById('addressInput').value.trim();
            const resultsDiv = document.getElementById('results');
            const searchBtn = document.getElementById('searchBtn');
            const forceRefresh = document.getElementById('forceRefresh').checked;

            // Validation
            if (!address) {
                resultsDiv.innerHTML = `
                    <div class="error">
                        <div class="error-title">⚠️ Validation Error</div>
                        <div>Please enter a valid address</div>
                    </div>
                `;
                return;
            }

            // Show loading state
            searchBtn.disabled = true;
            searchBtn.textContent = 'Searching...';
            resultsDiv.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <div>Fetching transactions for address: <strong>${address}</strong></div>
                    ${forceRefresh ? '<div style="margin-top: 10px; color: #ff6b35;">🔄 Bypassing cache...</div>' : ''}
                </div>
            `;

            try {
                const url = `${API_BASE_URL}/${address}/txs${forceRefresh ? '?force_refresh=true' : ''}`;
                const response = await fetch(url);

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP Error: ${response.status}`);
                }

                const data = await response.json();
                displayResults(data, address);

            } catch (error) {
                resultsDiv.innerHTML = `
                    <div class="error">
                        <div class="error-title">❌ Error Fetching Data</div>
                        <div><strong>Message:</strong> ${error.message}</div>
                        <div style="margin-top: 10px; font-size: 0.9em;">
                            Please check:
                            <ul style="margin-left: 20px; margin-top: 5px;">
                                <li>The address is correct</li>
                                <li>The backend server is running</li>
                                <li>Your internet connection is working</li>
                            </ul>
                        </div>
                    </div>
                `;
            } finally {
                searchBtn.disabled = false;
                searchBtn.textContent = 'Search';
            }
        }

        function displayResults(data, address) {
            const resultsDiv = document.getElementById('results');

            // Check if data is an array
            const transactions = Array.isArray(data) ? data : (data.transactions || []);

            if (!transactions || transactions.length === 0) {
                resultsDiv.innerHTML = `
                    <div class="no-results">
                        <div class="no-results-icon">📭</div>
                        <h2>No Transactions Found</h2>
                        <p>No transactions were found for address: <strong>${address}</strong></p>
                    </div>
                `;
                return;
            }

            let html = `
                <div class="results-header">
                    <div class="results-count">
                        📊 Found ${transactions.length} transaction${transactions.length !== 1 ? 's' : ''}
                    </div>
                </div>
            `;

            transactions.forEach((tx, index) => {
                // Extract data from the actual API structure
                const txid = tx.txid || 'N/A';
                const fee = tx.fee || 0;
                const size = tx.size || 0;
                const weight = tx.weight || 0;
                const version = tx.version || 'N/A';
                const locktime = tx.locktime || 0;
                const sigops = tx.sigops || 0;
                
                // Status information
                const status = tx.status || {};
                const blockHash = status.block_hash || 'N/A';
                const blockHeight = status.block_height || 'N/A';
                const blockTime = status.block_time || 'N/A';
                const confirmed = status.confirmed || false;
                
                // Inputs and outputs
                const vin = tx.vin || [];
                const vout = tx.vout || [];

                html += `
                    <div class="transaction-card">
                        <div class="tx-header">
                            <div class="tx-hash">
                                <strong>TXID:</strong> ${txid}
                            </div>
                            <div class="tx-time">
                                ${formatTimestamp(blockTime)}
                            </div>
                        </div>
                        <div class="tx-details">
                            <div class="detail-item">
                                <div class="detail-label">Block Height</div>
                                <div class="detail-value">${blockHeight}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Block Hash</div>
                                <div class="detail-value"><span class="clickable-link" onclick="viewBlock('${blockHash}')">${blockHash}</span></div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Fee</div>
                                <div class="detail-value">${fee} satoshis</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Size</div>
                                <div class="detail-value">${size} bytes</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Weight</div>
                                <div class="detail-value">${weight}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Version</div>
                                <div class="detail-value">${version}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Locktime</div>
                                <div class="detail-value">${locktime}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">SigOps</div>
                                <div class="detail-value">${sigops}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Status</div>
                                <div class="detail-value">
                                    <span class="status-badge status-${confirmed ? 'confirmed' : 'pending'}">
                                        ${confirmed ? 'CONFIRMED' : 'PENDING'}
                                    </span>
                                </div>
                            </div>
                        </div>
                        
                        ${vin.length > 0 ? `
                        <div class="section-header">
                            <h3>📥 Inputs (${vin.length})</h3>
                        </div>
                        <div class="inputs-outputs">
                            ${vin.map((input, i) => `
                                <div class="io-item">
                                    <div class="io-header">
                                        <strong>Input ${i + 1}</strong>
                                        ${input.is_coinbase ? '<span class="coinbase-badge">COINBASE</span>' : ''}
                                    </div>
                                    <div class="io-details">
                                        <div class="detail-item">
                                            <div class="detail-label">Previous TXID</div>
                                            <div class="detail-value">${input.txid || 'N/A'}</div>
                                        </div>
                                        <div class="detail-item">
                                            <div class="detail-label">Vout</div>
                                            <div class="detail-value">${input.vout !== undefined ? input.vout : 'N/A'}</div>
                                        </div>
                                        <div class="detail-item">
                                            <div class="detail-label">Sequence</div>
                                            <div class="detail-value">${input.sequence || 'N/A'}</div>
                                        </div>
                                        <div class="detail-item">
                                            <div class="detail-label">ScriptSig</div>
                                            <div class="detail-value">${input.scriptsig || 'N/A'}</div>
                                        </div>
                                        <div class="detail-item">
                                            <div class="detail-label">ScriptSig ASM</div>
                                            <div class="detail-value">${input.scriptsig_asm || 'N/A'}</div>
                                        </div>
                                        ${input.witness && input.witness.length > 0 ? `
                                        <div class="detail-item">
                                            <div class="detail-label">Witness</div>
                                            <div class="detail-value">${input.witness.join(', ')}</div>
                                        </div>
                                        ` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        ` : ''}
                        
                        ${vout.length > 0 ? `
                        <div class="section-header">
                            <h3>📤 Outputs (${vout.length})</h3>
                        </div>
                        <div class="inputs-outputs">
                            ${vout.map((output, i) => `
                                <div class="io-item">
                                    <div class="io-header">
                                        <strong>Output ${i + 1}</strong>
                                        <span class="value-badge">${output.value} satoshis</span>
                                    </div>
                                    <div class="io-details">
                                        <div class="detail-item">
                                            <div class="detail-label">ScriptPubKey</div>
                                            <div class="detail-value">${output.scriptpubkey || 'N/A'}</div>
                                        </div>
                                        <div class="detail-item">
                                            <div class="detail-label">Address</div>
                                            <div class="detail-value">${output.scriptpubkey_address || 'N/A'}</div>
                                        </div>
                                        <div class="detail-item">
                                            <div class="detail-label">Type</div>
                                            <div class="detail-value">${output.scriptpubkey_type || 'N/A'}</div>
                                        </div>
                                        <div class="detail-item">
                                            <div class="detail-label">ScriptPubKey ASM</div>
                                            <div class="detail-value">${output.scriptpubkey_asm || 'N/A'}</div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        ` : ''}
                        
                        <button class="toggle-json" onclick="toggleJson(${index})">
                            View Raw JSON
                        </button>
                        <div id="json-${index}" class="json-viewer" style="display: none;">
                            <div class="json-content">${JSON.stringify(tx, null, 2)}</div>
                        </div>
                    </div>
                `;
            });

            resultsDiv.innerHTML = html;
        }

        function toggleJson(index) {
            const jsonDiv = document.getElementById(`json-${index}`);
            const isVisible = jsonDiv.style.display !== 'none';
            jsonDiv.style.display = isVisible ? 'none' : 'block';
            event.target.textContent = isVisible ? 'View Raw JSON' : 'Hide Raw JSON';
        }

        function formatTimestamp(timestamp) {
            if (!timestamp || timestamp === 'N/A') return 'N/A';
            
            // If timestamp is a number (Unix timestamp)
            if (typeof timestamp === 'number') {
                return new Date(timestamp * 1000).toLocaleString();
            }
            
            // If timestamp is already a date string
            const date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
                return date.toLocaleString();
            }
            
            return timestamp;
        }

        function viewBlock(blockHash) {
            // Navigate to block viewer with the block hash
            window.location.href = `/block?hash=${blockHash}`;
        }

        // Load cache status
        async function loadCacheStatus() {
            try {
                const response = await fetch('/api/cache/stats');
                const stats = await response.json();
                const statusElement = document.getElementById('cacheStatus');
                
                if (stats.status === 'enabled') {
                    statusElement.innerHTML = `Cache: ✅ Enabled (${stats.keys} keys)`;
                    statusElement.style.color = '#28a745';
                } else if (stats.status === 'disabled') {
                    statusElement.innerHTML = `Cache: ❌ Disabled (${stats.reason})`;
                    statusElement.style.color = '#dc3545';
                } else {
                    statusElement.innerHTML = `Cache: ⚠️ Error (${stats.reason})`;
                    statusElement.style.color = '#ffc107';
                }
            } catch (error) {
                document.getElementById('cacheStatus').innerHTML = 'Cache: ❌ Error';
                document.getElementById('cacheStatus').style.color = '#dc3545';
            }
        }

        // Focus on input on page load and handle URL parameters
        window.addEventListener('load', function() {
            loadCacheStatus();
            
            const urlParams = new URLSearchParams(window.location.search);
            const txid = urlParams.get('txid');
            if (txid) {
                document.getElementById('addressInput').value = txid;
                fetchTransactions();
            } else {
                document.getElementById('addressInput').focus();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/address/<address>/txs', methods=['GET'])
def get_transactions(address):
    """
    Proxy endpoint to fetch transactions from the external API with caching
    """
    try:
        # Validate address (basic validation)
        if not address or len(address) < 10:
            return jsonify({
                'error': 'Invalid address format',
                'message': 'Please provide a valid blockchain address'
            }), 400

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key
        cache_key = get_cache_key('address', address)
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for address: {address}")
                return jsonify(cached_data), 200

        # Make request to external API
        url = f"{ADDRESS_API_BASE_URL}/{address}/txs"
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the JSON data
        data = response.json()
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached data for address: {address}")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/block')
def block_viewer():
    """Serve the block viewer HTML page"""
    with open('block-viewer.html', 'r') as f:
        return f.read()

@app.route('/transaction')
def transaction_viewer():
    """Serve the transaction viewer HTML page"""
    with open('transaction-viewer.html', 'r') as f:
        return f.read()

@app.route('/latest-blocks')
def latest_blocks():
    """Serve the latest blocks HTML page"""
    with open('latest-blocks.html', 'r') as f:
        return f.read()

@app.route('/api/block/<block_hash>/txs', methods=['GET'])
def get_block_transactions(block_hash):
    """
    Proxy endpoint to fetch transactions from a specific block with caching
    """
    try:
        # Validate block hash (basic validation)
        if not block_hash or len(block_hash) < 10:
            return jsonify({
                'error': 'Invalid block hash format',
                'message': 'Please provide a valid block hash'
            }), 400

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key
        cache_key = get_cache_key('block', block_hash)
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for block: {block_hash}")
                return jsonify(cached_data), 200

        # Make request to external API
        url = f"{BLOCK_API_BASE_URL}/{block_hash}/txs"
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the JSON data
        data = response.json()
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached data for block: {block_hash}")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/api/block/<block_hash>/info', methods=['GET'])
def get_block_info(block_hash):
    """
    Proxy endpoint to fetch block information (difficulty, bits, etc.) with caching
    """
    try:
        # Validate block hash (basic validation)
        if not block_hash or len(block_hash) < 10:
            return jsonify({
                'error': 'Invalid block hash format',
                'message': 'Please provide a valid block hash'
            }), 400

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key for block info
        cache_key = get_cache_key('block_info', block_hash)
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for block info: {block_hash}")
                # Ensure megahash is calculated for cached data too
                if 'difficulty' in cached_data and cached_data['difficulty'] is not None:
                    cached_data['megahash'] = calculate_megahash(cached_data['difficulty'])
                elif 'megahash' not in cached_data:
                    cached_data['megahash'] = 0
                return jsonify(cached_data), 200

        # Make request to external API for block info
        url = f"{BLOCK_API_BASE_URL}/{block_hash}"
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the JSON data
        data = response.json()
        
        # Add megahash calculation if difficulty is present
        if 'difficulty' in data and data['difficulty'] is not None:
            data['megahash'] = calculate_megahash(data['difficulty'])
        else:
            data['megahash'] = 0
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached block info for: {block_hash}")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/api/block-height/<height>', methods=['GET'])
def get_block_hash_from_height(height):
    """
    Proxy endpoint to fetch block hash from block height with caching
    """
    try:
        # Validate block height (must be a positive integer)
        try:
            height_int = int(height)
            if height_int < 0:
                raise ValueError("Height must be positive")
        except ValueError:
            return jsonify({
                'error': 'Invalid block height format',
                'message': 'Please provide a valid block height (positive integer)'
            }), 400

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key for block height
        cache_key = get_cache_key('block_height', height)
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for block height: {height}")
                return jsonify(cached_data), 200

        # Make request to external API for block hash
        url = f"http://157.180.8.224:3000/block-height/{height}"
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the block hash (it's returned as plain text)
        block_hash = response.text.strip()
        
        # Create response data
        data = {
            'height': height_int,
            'hash': block_hash,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached block hash for height: {height}")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/api/tx/<txid>', methods=['GET'])
def get_transaction(txid):
    """
    Proxy endpoint to fetch transaction details from the external API with caching
    """
    try:
        # Validate transaction ID (basic validation)
        if not txid or len(txid) < 10:
            return jsonify({
                'error': 'Invalid transaction ID format',
                'message': 'Please provide a valid transaction ID'
            }), 400

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key
        cache_key = get_cache_key('transaction', txid)
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for transaction: {txid}")
                return jsonify(cached_data), 200

        # Make request to external API
        url = f"{TX_API_BASE_URL}/{txid}"
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the JSON data
        data = response.json()
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached data for transaction: {txid}")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    stats = get_cache_stats()
    return jsonify(stats), 200

@app.route('/api/bitcoin/price', methods=['GET'])
def get_bitcoin_price_api():
    """Get current Bitcoin price in USD"""
    try:
        price = get_bitcoin_price()
        if price:
            return jsonify({
                'price_usd': price,
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }), 200
        else:
            return jsonify({
                'error': 'Price not available',
                'message': 'Could not fetch Bitcoin price'
            }), 503
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/transaction/<txid>/pricing', methods=['GET'])
def get_transaction_pricing(txid):
    """Get USD pricing information for a transaction"""
    try:
        # Validate transaction ID
        if not txid or len(txid) < 10:
            return jsonify({
                'error': 'Invalid transaction ID format',
                'message': 'Please provide a valid transaction ID'
            }), 400

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key for transaction pricing
        cache_key = get_cache_key('transaction_pricing', txid)
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for transaction pricing: {txid}")
                return jsonify(cached_data), 200

        # Fetch transaction data first
        tx_url = f"{TX_API_BASE_URL}/{txid}"
        response = requests.get(tx_url, timeout=30)
        response.raise_for_status()
        transaction_data = response.json()
        
        # Calculate USD value
        pricing_info = calculate_transaction_usd_value(transaction_data)
        
        if not pricing_info:
            return jsonify({
                'error': 'Pricing calculation failed',
                'message': 'Could not calculate USD value for this transaction'
            }), 500
        
        # Add transaction details to pricing info
        pricing_info['transaction_id'] = txid
        pricing_info['transaction_data'] = {
            'block_height': transaction_data.get('status', {}).get('block_height'),
            'block_time': transaction_data.get('status', {}).get('block_time'),
            'confirmed': transaction_data.get('status', {}).get('confirmed', False)
        }
        
        # Store in cache
        set_cache(cache_key, pricing_info, CACHE_TTL)
        print(f"💾 Cached pricing data for transaction: {txid}")
        
        return jsonify(pricing_info), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Transaction fetch failed',
            'message': f'Could not fetch transaction data: {str(e)}'
        }), 503
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/blocks/latest', methods=['GET'])
def get_latest_blocks():
    """
    Proxy endpoint to fetch the latest blocks from the external API with caching
    """
    try:
        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key for latest blocks
        cache_key = get_cache_key('latest_blocks', 'latest')
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for latest blocks")
                # Ensure megahash is calculated for cached data too
                if isinstance(cached_data, list):
                    for block in cached_data:
                        if 'difficulty' in block and block['difficulty'] is not None:
                            block['megahash'] = calculate_megahash(block['difficulty'])
                        elif 'megahash' not in block:
                            block['megahash'] = 0
                elif isinstance(cached_data, dict) and 'difficulty' in cached_data:
                    cached_data['megahash'] = calculate_megahash(cached_data['difficulty'])
                return jsonify(cached_data), 200

        # Make request to external API for latest blocks
        url = BLOCKS_API_BASE_URL
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the JSON data
        data = response.json()
        
        # Add megahash calculation for each block if difficulty is present
        if isinstance(data, list):
            for block in data:
                if 'difficulty' in block and block['difficulty'] is not None:
                    block['megahash'] = calculate_megahash(block['difficulty'])
                else:
                    block['megahash'] = 0
        elif isinstance(data, dict) and 'difficulty' in data:
            data['megahash'] = calculate_megahash(data['difficulty'])
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached latest blocks data")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cache entries"""
    if not REDIS_AVAILABLE:
        return jsonify({
            'error': 'Cache not available',
            'message': 'Redis is not available'
        }), 503
    
    try:
        # Clear all keys with our prefix
        keys = redis_client.keys('blockchain_explorer:*')
        if keys:
            redis_client.delete(*keys)
            return jsonify({
                'message': f'Cleared {len(keys)} cache entries',
                'cleared_keys': len(keys)
            }), 200
        else:
            return jsonify({
                'message': 'No cache entries to clear',
                'cleared_keys': 0
            }), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to clear cache',
            'message': str(e)
        }), 500

@app.route('/api/mempool', methods=['GET'])
def get_mempool_status():
    """
    Proxy endpoint to fetch mempool status from the external API with caching
    """
    try:
        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key for mempool status
        cache_key = get_cache_key('mempool', 'status')
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for mempool status")
                return jsonify(cached_data), 200

        # Make request to external API for mempool status
        url = MEMPOOL_API_BASE_URL
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the JSON data
        data = response.json()
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached mempool status data")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/api/mempool/recent', methods=['GET'])
def get_mempool_recent():
    """
    Proxy endpoint to fetch recent mempool transactions from the external API with caching
    """
    try:
        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Generate cache key for recent mempool transactions
        cache_key = get_cache_key('mempool', 'recent')
        
        # Try to get from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"✅ Cache hit for recent mempool transactions")
                return jsonify(cached_data), 200

        # Make request to external API for recent mempool transactions
        url = f"{MEMPOOL_API_BASE_URL}/recent"
        
        # Set a timeout to avoid hanging requests
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get the JSON data
        data = response.json()
        
        # Store in cache
        set_cache(cache_key, data)
        print(f"💾 Cached recent mempool transactions data")
        
        # Return the JSON data
        return jsonify(data), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The external API took too long to respond'
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the external API. Please check if the API is accessible.'
        }), 503

    except requests.exceptions.HTTPError as e:
        return jsonify({
            'error': 'HTTP error',
            'message': f'External API returned error: {e.response.status_code}',
            'details': str(e)
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': 'An error occurred while fetching data',
            'details': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/mempool')
def mempool_viewer():
    """Serve the mempool viewer HTML page"""
    with open('mempool-viewer.html', 'r') as f:
        return f.read()

@app.route('/details')
def details_viewer():
    """Serve the details/pricing viewer HTML page"""
    with open('details.html', 'r') as f:
        return f.read()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    cache_stats = get_cache_stats()
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'address_api_url': ADDRESS_API_BASE_URL,
        'block_api_url': BLOCK_API_BASE_URL,
        'mempool_api_url': MEMPOOL_API_BASE_URL,
        'cache': cache_stats
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Address Viewer Backend Server")
    print("=" * 60)
    print(f"📡 Address API: {ADDRESS_API_BASE_URL}")
    print(f"📡 Block API: {BLOCK_API_BASE_URL}")
    print(f"🌐 Server starting at: http://localhost:5000")
    print(f"🏥 Health check: http://localhost:5000/health")
    print("=" * 60)
    
    # Start Bitcoin price updater
    start_price_updater()
    
    print("\nPress CTRL+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
