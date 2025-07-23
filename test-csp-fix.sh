#!/bin/bash

echo "🛡️  Testing Content Security Policy Fix"
echo "======================================"

# Test 1: Check documentation endpoint CSP
echo "1. Checking documentation CSP policy..."
DOCS_CSP=$(curl -s -I http://server.epicrunze.com/docs | grep -i "content-security-policy")
if echo "$DOCS_CSP" | grep -q "cdn.jsdelivr.net"; then
    echo "✅ Documentation CSP allows external CDN resources"
else
    echo "❌ Documentation CSP still too restrictive"
fi

# Test 2: Check API endpoint CSP
echo ""
echo "2. Checking API endpoint CSP policy..."
API_CSP=$(curl -s -I http://server.epicrunze.com/api/v1/books -H "Authorization: Bearer default-dev-key" | grep -i "content-security-policy")
if echo "$API_CSP" | grep -q "cdn.jsdelivr.net"; then
    echo "❌ API CSP is too permissive (security risk!)"
else
    echo "✅ API CSP maintains strict security policy"
fi

# Test 3: Verify documentation loads
echo ""
echo "3. Testing documentation page loading..."
DOCS_RESPONSE=$(curl -s -w "%{http_code}" http://server.epicrunze.com/docs -o /dev/null)
if [ "$DOCS_RESPONSE" = "200" ]; then
    echo "✅ Documentation page loads successfully"
else
    echo "❌ Documentation page failed to load (HTTP $DOCS_RESPONSE)"
fi

# Test 4: Check if Swagger UI resources are accessible through proxy
echo ""
echo "4. Testing external resource accessibility..."

# Check if the documentation contains references to external resources
DOCS_CONTENT=$(curl -s http://server.epicrunze.com/docs)
if echo "$DOCS_CONTENT" | grep -q "cdn.jsdelivr.net"; then
    echo "✅ Documentation references external CDN resources"
else
    echo "⚠️  Documentation may not reference expected external resources"
fi

if echo "$DOCS_CONTENT" | grep -q "SwaggerUIBundle"; then
    echo "✅ Swagger UI JavaScript bundle referenced"
else
    echo "❌ Swagger UI JavaScript bundle not found"
fi

# Test 5: ReDoc endpoint and Web Worker support
echo ""
echo "5. Testing ReDoc endpoint and Web Worker support..."
REDOC_RESPONSE=$(curl -s -w "%{http_code}" http://server.epicrunze.com/redoc -o /dev/null)
if [ "$REDOC_RESPONSE" = "200" ]; then
    echo "✅ ReDoc page loads successfully"
else
    echo "❌ ReDoc page failed to load (HTTP $REDOC_RESPONSE)"
fi

# Check if ReDoc CSP allows Web Workers
REDOC_CSP=$(curl -s -I http://server.epicrunze.com/redoc | grep -i "content-security-policy")
if echo "$REDOC_CSP" | grep -q "worker-src"; then
    echo "✅ ReDoc CSP allows Web Workers (fixes blob URL errors)"
else
    echo "❌ ReDoc CSP missing Web Worker support"
fi

# Test 6: OpenAPI JSON endpoint  
echo ""
echo "6. Testing OpenAPI JSON endpoint..."
OPENAPI_RESPONSE=$(curl -s http://server.epicrunze.com/openapi.json)
if echo "$OPENAPI_RESPONSE" | jq -e '.info.title' > /dev/null 2>&1; then
    echo "✅ OpenAPI JSON loads and contains valid data"
    TITLE=$(echo "$OPENAPI_RESPONSE" | jq -r '.info.title')
    echo "   API Title: $TITLE"
else
    echo "❌ OpenAPI JSON invalid or not loading"
fi

echo ""
echo "🎉 CSP Fix Verification Complete!"
echo ""
echo "📋 Summary:"
echo "   • Documentation endpoints: Permissive CSP for Swagger UI"
echo "   • API endpoints: Strict CSP for security"
echo "   • External resources: Whitelisted CDN domains only"
echo ""
echo "🌐 Access your documentation:"
echo "   • Swagger UI: http://server.epicrunze.com/docs"
echo "   • ReDoc: http://server.epicrunze.com/redoc"
echo ""
echo "The Content Security Policy errors should now be resolved! 🛡️✨" 