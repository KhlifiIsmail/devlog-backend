"""
Test Redis connection.
"""
import redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

print("🔍 Testing Redis connection...")
print(f"📍 Redis URL: {REDIS_URL}")

try:
    r = redis.from_url(REDIS_URL)
    
    # Test ping
    response = r.ping()
    print(f"✅ Redis PING: {response}")
    
    # Test set/get
    r.set('test_key', 'test_value')
    value = r.get('test_key')
    print(f"✅ Redis SET/GET: {value.decode()}")
    
    # Get Redis info
    info = r.info()
    print(f"✅ Redis version: {info['redis_version']}")
    print(f"✅ Connected clients: {info['connected_clients']}")
    
    print("\n🎉 Redis connection successful!")
    
except redis.ConnectionError:
    print("\n❌ Error: Could not connect to Redis")
    print("   Make sure Redis is running:")
    print("   docker run -d --name devlog_redis -p 6379:6379 redis:7-alpine")
except Exception as e:
    print(f"\n❌ Error: {e}")