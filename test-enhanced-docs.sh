#!/bin/bash

echo "🧪 Testing Enhanced API Documentation"
echo "====================================="

# Test 1: Health endpoint (no auth required)
echo "1. Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://server.epicrunze.com/health)
if echo "$HEALTH_RESPONSE" | jq -e '.status == "healthy"' > /dev/null; then
    echo "✅ Health endpoint working"
else
    echo "❌ Health endpoint failed"
fi

# Test 2: OpenAPI schema (should contain enhanced descriptions)
echo ""
echo "2. Testing OpenAPI schema enhancements..."
OPENAPI_RESPONSE=$(curl -s http://server.epicrunze.com/openapi.json)
if echo "$OPENAPI_RESPONSE" | jq -e '.info.title == "Audiobook Server API"' > /dev/null; then
    echo "✅ API title correct"
else
    echo "❌ API title missing"
fi

if echo "$OPENAPI_RESPONSE" | jq -e '.info.contact' > /dev/null; then
    echo "✅ Contact information present"
else
    echo "❌ Contact information missing"
fi

if echo "$OPENAPI_RESPONSE" | jq -e '.tags' > /dev/null; then
    echo "✅ Endpoint tags present"
    echo "   Tags: $(echo "$OPENAPI_RESPONSE" | jq -r '.tags[].name' | tr '\n' ', ' | sed 's/,$//')"
else
    echo "❌ Endpoint tags missing"
fi

# Test 3: Authentication with enhanced error messages
echo ""
echo "3. Testing authentication with invalid key..."
AUTH_RESPONSE=$(curl -s -X POST http://server.epicrunze.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"apiKey": "invalid-key"}' \
  -w "%{http_code}")

HTTP_CODE="${AUTH_RESPONSE: -3}"
if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Authentication properly rejects invalid keys"
else
    echo "❌ Authentication test failed (HTTP $HTTP_CODE)"
fi

# Test 4: Valid authentication
echo ""
echo "4. Testing valid authentication..."
VALID_AUTH_RESPONSE=$(curl -s -X POST http://server.epicrunze.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"apiKey": "default-dev-key", "remember": false}')

if echo "$VALID_AUTH_RESPONSE" | jq -e '.sessionToken' > /dev/null; then
    echo "✅ Valid authentication working"
    SESSION_TOKEN=$(echo "$VALID_AUTH_RESPONSE" | jq -r '.sessionToken')
else
    echo "❌ Valid authentication failed"
    SESSION_TOKEN="default-dev-key"  # Fallback to API key
fi

# Test 5: Book listing with authentication
echo ""
echo "5. Testing book listing endpoint..."
BOOKS_RESPONSE=$(curl -s -H "Authorization: Bearer $SESSION_TOKEN" \
  http://server.epicrunze.com/api/v1/books)

if echo "$BOOKS_RESPONSE" | jq -e '.books' > /dev/null; then
    echo "✅ Book listing endpoint working"
    BOOK_COUNT=$(echo "$BOOKS_RESPONSE" | jq '.books | length')
    echo "   Books in system: $BOOK_COUNT"
else
    echo "❌ Book listing endpoint failed"
fi

# Test 6: Documentation accessibility
echo ""
echo "6. Testing documentation endpoints..."

# Swagger UI
DOCS_RESPONSE=$(curl -s -w "%{http_code}" http://server.epicrunze.com/docs -o /dev/null)
if [ "$DOCS_RESPONSE" = "200" ]; then
    echo "✅ Swagger UI accessible at /docs"
else
    echo "❌ Swagger UI not accessible (HTTP $DOCS_RESPONSE)"
fi

# ReDoc
REDOC_RESPONSE=$(curl -s -w "%{http_code}" http://server.epicrunze.com/redoc -o /dev/null)
if [ "$REDOC_RESPONSE" = "200" ]; then
    echo "✅ ReDoc accessible at /redoc"
else
    echo "❌ ReDoc not accessible (HTTP $REDOC_RESPONSE)"
fi

echo ""
echo "🎉 Documentation Enhancement Test Complete!"
echo ""
echo "📖 Access your enhanced documentation:"
echo "   • Interactive Docs: http://server.epicrunze.com/docs"
echo "   • ReDoc: http://server.epicrunze.com/redoc"
echo "   • OpenAPI Spec: http://server.epicrunze.com/openapi.json"
echo ""
echo "🔧 Key Enhancements:"
echo "   • Rich descriptions with examples"
echo "   • Organized endpoint tags"
echo "   • Comprehensive error documentation"
echo "   • Authentication guidance"
echo "   • Audio streaming specifications"
echo ""
echo "Happy documenting! 📚✨" 