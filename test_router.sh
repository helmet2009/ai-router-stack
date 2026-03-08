#!/bin/bash

echo "Testing AI Router Stack..."

# Test 1: Check if router is responding
echo "1. Testing router health endpoint..."
curl -s http://localhost:8000/health | jq .

# Test 2: Test metrics endpoint
echo -e "\n2. Testing metrics endpoint..."
curl -s http://localhost:8000/metrics | head -20

# Test 3: Test generate endpoint (non-streaming)
echo -e "\n3. Testing generate endpoint (non-streaming)..."
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -H "x-api-key: a3c7853245277afe3151442ace9ec242ce07275ef257a6b2ca8f4ac79d9fda67" \
  -d '{
    "model": "deepseek-r1:latest",
    "prompt": "Hello, how are you?",
    "stream": false
  }' | jq -c '.response'

# Test 4: Check Redis connection
echo -e "\n4. Checking Redis connection..."
docker exec ai-router python -c "
import asyncio
import redis.asyncio as redis
import os

async def test():
    r = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379'))
    try:
        await r.ping()
        print('Redis: Connected successfully')
    except Exception as e:
        print(f'Redis: Connection failed - {e}')

asyncio.run(test())
"

echo -e "\nTest completed!"