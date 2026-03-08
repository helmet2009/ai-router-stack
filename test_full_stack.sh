#!/bin/bash

# ==========================================
# AI Router Stack - Full Integration Test
# ==========================================

echo "========================================="
echo "Testing AI Router Stack Integration"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Check all containers are running
echo -e "\n1. Checking Docker containers..."
CONTAINERS=("ai-router" "open-webui" "redis" "qdrant" "prometheus" "grafana")
ALL_RUNNING=true

for container in "${CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${GREEN}✓${NC} $container is running"
    else
        echo -e "${RED}✗${NC} $container is NOT running"
        ALL_RUNNING=false
    fi
done

if [ "$ALL_RUNNING" = false ]; then
    echo -e "${RED}Some containers are not running!${NC}"
    exit 1
fi

# Test 2: Check Router health
echo -e "\n2. Checking Router health..."
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q '"status"'; then
    echo -e "${GREEN}✓${NC} Router is healthy"
    echo "   Details: $(echo $HEALTH | jq -c '.')"
else
    echo -e "${RED}✗${NC} Router is not healthy"
    echo "   Response: $HEALTH"
    exit 1
fi

# Test 3: Check Redis connection
echo -e "\n3. Checking Redis connection..."
if echo "$HEALTH" | grep -q '"redis_connected":true'; then
    echo -e "${GREEN}✓${NC} Redis connected"
else
    echo -e "${RED}✗${NC} Redis not connected"
fi

# Test 4: Check Qdrant connection
echo -e "\n4. Checking Qdrant connection..."
if echo "$HEALTH" | grep -q '"qdrant_connected":true'; then
    echo -e "${GREEN}✓${NC} Qdrant connected"
else
    echo -e "${RED}✗${NC} Qdrant not connected"
fi

# Test 5: Check Ollama connection
echo -e "\n5. Checking Ollama connection..."
if echo "$HEALTH" | grep -q '"ollama_connected":true'; then
    echo -e "${GREEN}✓${NC} Ollama connected"
else
    echo -e "${RED}✗${NC} Ollama not connected"
fi

# Test 6: List available models from Ollama
echo -e "\n6. Listing Ollama models..."
MODELS=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null)
if [ -n "$MODELS" ]; then
    echo -e "${GREEN}✓${NC} Found models:"
    echo "$MODELS" | head -5 | while read model; do
        echo "   - $model"
    done
else
    echo -e "${RED}✗${NC} No models found"
fi

# Test 7: Test Router API with model
echo -e "\n7. Testing Router API with llama3.2:1b..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -H "x-api-key: a3c7853245277afe3151442ace9ec242ce07275ef257a6b2ca8f4ac79d9fda67" \
  -d '{
    "model": "llama3.2:1b",
    "prompt": "Say hello",
    "stream": false,
    "temperature": 0.7
  }')

if echo "$RESPONSE" | grep -q '"response"'; then
    echo -e "${GREEN}✓${NC} Router API working"
    echo "   Response: $(echo $RESPONSE | jq -r '.response')"
else
    echo -e "${RED}✗${NC} Router API failed"
    echo "   Error: $RESPONSE"
fi

# Test 8: Check Open WebUI
echo -e "\n8. Checking Open WebUI..."
WEBUI_STATUS=$(curl -s http://localhost:8080/health | jq -r '.status')
if [ "$WEBUI_STATUS" = "true" ]; then
    echo -e "${GREEN}✓${NC} Open WebUI is running"
    echo "   Access at: http://localhost:8080"
else
    echo -e "${RED}✗${NC} Open WebUI is not running"
fi

# Test 9: Check Prometheus
echo -e "\n9. Checking Prometheus..."
PROM_STATUS=$(curl -s http://localhost:9090/-/healthy)
if [ "$PROM_STATUS" = "OK" ]; then
    echo -e "${GREEN}✓${NC} Prometheus is running"
    echo "   Access at: http://localhost:9090"
else
    echo -e "${RED}✗${NC} Prometheus is not running"
fi

# Test 10: Check Grafana
echo -e "\n10. Checking Grafana..."
GRAFANA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001)
if [ "$GRAFANA_STATUS" = "200" ]; then
    echo -e "${GREEN}✓${NC} Grafana is running"
    echo "   Access at: http://localhost:3001 (admin/admin123)"
else
    echo -e "${RED}✗${NC} Grafana is not running (status: $GRAFANA_STATUS)"
fi

echo -e "\n========================================="
echo "Integration Test Complete!"
echo "========================================="
echo -e "\n${GREEN}Next Steps:${NC}"
echo "1. Open http://localhost:8080 in your browser"
echo "2. Create an account or login"
echo "3. Go to Settings > Connections"
echo "4. Add Ollama connection with URL: http://router:8000"
echo "5. Select your model (llama3.2:1b) and start chatting!"
echo -e "\n${GREEN}API Endpoints:${NC}"
echo "- Router API: http://localhost:8000"
echo "- Open WebUI: http://localhost:8080"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3001"
echo "- Qdrant: http://localhost:6333"