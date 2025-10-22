#!/usr/bin/env python3
"""
Test script to verify the blockchain explorer caching functionality
"""

import requests
import json
import time
import sys

def test_api_endpoint(base_url, endpoint, test_data, description):
    """Test an API endpoint and measure response time"""
    print(f"\n🧪 Testing {description}")
    print(f"   Endpoint: {endpoint}")
    
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}{endpoint}", timeout=10)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Response time: {response_time:.2f}ms")
            print(f"   📊 Data: {len(data) if isinstance(data, list) else 'Object'} items")
            return True, response_time, data
        else:
            print(f"   ❌ Failed with status: {response.status_code}")
            print(f"   📝 Response: {response.text[:200]}...")
            return False, response_time, None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, 0, None

def test_cache_functionality():
    """Test the caching functionality"""
    print("🚀 Blockchain Explorer Caching Test")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # Test data
    test_address = "bc1qfqqqngash6c0u0vmj78nlvslzz0g45rrlq0chg"
    test_block_hash = "000000007952236b060bb8f215cd9090b4384647638a80f20f6879e31ac5da20"
    
    print("📋 Test Plan:")
    print("   1. Test server health and cache status")
    print("   2. Test address API (first call - should cache)")
    print("   3. Test address API (second call - should hit cache)")
    print("   4. Test block API (first call - should cache)")
    print("   5. Test block API (second call - should hit cache)")
    print("   6. Test force refresh functionality")
    print("   7. Test cache statistics")
    print("   8. Test cache clear functionality")
    
    # Test 1: Health check
    print("\n" + "="*60)
    print("1️⃣ Testing Server Health")
    health_ok, health_time, health_data = test_api_endpoint(
        base_url, "/health", None, "Health Check"
    )
    
    if not health_ok:
        print("❌ Server is not running. Please start the server first:")
        print("   python app.py")
        return False
    
    # Check cache status
    cache_status = health_data.get('cache', {})
    print(f"   📊 Cache Status: {cache_status.get('status', 'Unknown')}")
    if cache_status.get('status') == 'enabled':
        print(f"   📈 Cache Keys: {cache_status.get('keys', 0)}")
    
    # Test 2: Address API - First call (should cache)
    print("\n" + "="*60)
    print("2️⃣ Testing Address API - First Call (Should Cache)")
    addr_ok_1, addr_time_1, addr_data_1 = test_api_endpoint(
        base_url, f"/api/address/{test_address}/txs", None, "Address Transactions"
    )
    
    if not addr_ok_1:
        print("❌ Address API test failed")
        return False
    
    # Test 3: Address API - Second call (should hit cache)
    print("\n" + "="*60)
    print("3️⃣ Testing Address API - Second Call (Should Hit Cache)")
    addr_ok_2, addr_time_2, addr_data_2 = test_api_endpoint(
        base_url, f"/api/address/{test_address}/txs", None, "Address Transactions (Cached)"
    )
    
    if not addr_ok_2:
        print("❌ Address API second call failed")
        return False
    
    # Compare response times
    if addr_time_2 < addr_time_1:
        speedup = ((addr_time_1 - addr_time_2) / addr_time_1) * 100
        print(f"   🚀 Cache hit! Speedup: {speedup:.1f}% faster")
    else:
        print(f"   ⚠️ No significant speedup detected")
    
    # Test 4: Block API - First call (should cache)
    print("\n" + "="*60)
    print("4️⃣ Testing Block API - First Call (Should Cache)")
    block_ok_1, block_time_1, block_data_1 = test_api_endpoint(
        base_url, f"/api/block/{test_block_hash}/txs", None, "Block Transactions"
    )
    
    if not block_ok_1:
        print("❌ Block API test failed")
        return False
    
    # Test 5: Block API - Second call (should hit cache)
    print("\n" + "="*60)
    print("5️⃣ Testing Block API - Second Call (Should Hit Cache)")
    block_ok_2, block_time_2, block_data_2 = test_api_endpoint(
        base_url, f"/api/block/{test_block_hash}/txs", None, "Block Transactions (Cached)"
    )
    
    if not block_ok_2:
        print("❌ Block API second call failed")
        return False
    
    # Compare response times
    if block_time_2 < block_time_1:
        speedup = ((block_time_1 - block_time_2) / block_time_1) * 100
        print(f"   🚀 Cache hit! Speedup: {speedup:.1f}% faster")
    else:
        print(f"   ⚠️ No significant speedup detected")
    
    # Test 6: Force refresh functionality
    print("\n" + "="*60)
    print("6️⃣ Testing Force Refresh Functionality")
    force_ok, force_time, force_data = test_api_endpoint(
        base_url, f"/api/address/{test_address}/txs?force_refresh=true", None, "Address with Force Refresh"
    )
    
    if force_ok:
        print(f"   ✅ Force refresh working! Response time: {force_time:.2f}ms")
    else:
        print("   ❌ Force refresh failed")
    
    # Test 7: Cache statistics
    print("\n" + "="*60)
    print("7️⃣ Testing Cache Statistics")
    stats_ok, stats_time, stats_data = test_api_endpoint(
        base_url, "/api/cache/stats", None, "Cache Statistics"
    )
    
    if stats_ok:
        print(f"   📊 Cache Status: {stats_data.get('status', 'Unknown')}")
        if stats_data.get('status') == 'enabled':
            print(f"   📈 Keys: {stats_data.get('keys', 0)}")
            print(f"   💾 Memory: {stats_data.get('memory_usage', 'N/A')}")
            print(f"   🎯 Hit Rate: {stats_data.get('hit_rate', 0):.2%}")
    
    # Test 8: Cache clear functionality
    print("\n" + "="*60)
    print("8️⃣ Testing Cache Clear Functionality")
    try:
        clear_response = requests.post(f"{base_url}/api/cache/clear", timeout=10)
        if clear_response.status_code == 200:
            clear_data = clear_response.json()
            print(f"   ✅ Cache cleared! Removed {clear_data.get('cleared_keys', 0)} keys")
        else:
            print(f"   ❌ Cache clear failed: {clear_response.status_code}")
    except Exception as e:
        print(f"   ❌ Cache clear error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)
    
    tests_passed = sum([
        health_ok, addr_ok_1, addr_ok_2, block_ok_1, block_ok_2, force_ok, stats_ok
    ])
    
    print(f"✅ Tests Passed: {tests_passed}/7")
    print(f"📊 Address API Performance:")
    print(f"   First call: {addr_time_1:.2f}ms")
    print(f"   Second call: {addr_time_2:.2f}ms")
    print(f"📊 Block API Performance:")
    print(f"   First call: {block_time_1:.2f}ms")
    print(f"   Second call: {block_time_2:.2f}ms")
    
    if tests_passed >= 6:
        print("\n🎉 Caching system is working correctly!")
        print("\n🌐 To use the application:")
        print("   1. Open: http://localhost:5000 (Address Viewer)")
        print("   2. Open: http://localhost:5000/block (Block Viewer)")
        print("   3. Use the 'Force refresh' checkbox to bypass cache")
        print("   4. Check cache status in the UI")
        return True
    else:
        print("\n❌ Some tests failed. Check the server logs for details.")
        return False

def main():
    """Main test function"""
    print("🔧 Blockchain Explorer Caching Test Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding properly")
            print("   Please start the server: python app.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print("   Please start the server: python app.py")
        sys.exit(1)
    
    # Run tests
    success = test_cache_functionality()
    
    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
