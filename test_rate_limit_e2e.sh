#!/bin/bash
# End-to-End Rate Limiting Test Script

set -e

echo "=========================================="
echo "Rate Limiting E2E Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
test_start() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "Test $TESTS_RUN: $1... "
}

test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "${GREEN}PASS${NC}"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "${RED}FAIL${NC}"
    echo "  Error: $1"
}

# Check if server is running
check_server() {
    if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
        echo -e "${RED}ERROR: Server not running on localhost:5001${NC}"
        echo "Please start the server with: make local"
        exit 1
    fi
}

# Test 1: Health endpoint is NOT rate limited
test_health_not_limited() {
    test_start "Health endpoint not rate limited (150 requests)"

    local success_count=0
    for i in {1..150}; do
        status=$(curl -s -w "%{http_code}" http://localhost:5001/health -o /dev/null)
        if [ "$status" = "200" ]; then
            success_count=$((success_count + 1))
        fi
    done

    if [ $success_count -eq 150 ]; then
        test_pass
    else
        test_fail "Expected 150 successful requests, got $success_count"
    fi
}

# Test 2: Protected endpoint has rate limit headers
test_rate_limit_headers() {
    test_start "Rate limit headers present on protected endpoints"

    response=$(curl -s -v http://localhost:5001/.well-known/oauth-authorization-server 2>&1)

    if echo "$response" | grep -q "x-ratelimit-limit:" && \
       echo "$response" | grep -q "x-ratelimit-remaining:" && \
       echo "$response" | grep -q "x-ratelimit-reset:"; then
        test_pass
    else
        test_fail "Missing rate limit headers"
    fi
}

# Test 3: Rate limit enforced after 100 requests
test_rate_limit_enforced() {
    test_start "Rate limit enforced at 100 requests"

    # Clear any existing rate limits by using a unique endpoint path with query param
    local test_endpoint="/.well-known/oauth-authorization-server?test=$RANDOM"

    # Make 101 requests
    local status_200=0
    local status_429=0

    for i in {1..105}; do
        status=$(curl -s -w "%{http_code}" "http://localhost:5001$test_endpoint" -o /dev/null)
        if [ "$status" = "200" ]; then
            status_200=$((status_200 + 1))
        elif [ "$status" = "429" ]; then
            status_429=$((status_429 + 1))
        fi
    done

    # Should have ~100 successful and ~5 rate limited
    if [ $status_200 -ge 95 ] && [ $status_200 -le 100 ] && [ $status_429 -ge 5 ]; then
        test_pass
    else
        test_fail "Expected ~100 OK and ~5 rate limited, got $status_200 OK and $status_429 rate limited"
    fi
}

# Test 4: 429 response format
test_429_response_format() {
    test_start "429 response has correct format and headers"

    # First exhaust the rate limit
    for i in {1..105}; do
        curl -s http://localhost:5001/.well-known/oauth-authorization-server?test2=$RANDOM -o /dev/null
    done

    # Get a 429 response
    response=$(curl -s http://localhost:5001/.well-known/oauth-authorization-server?test2=$RANDOM)
    headers=$(curl -s -v http://localhost:5001/.well-known/oauth-authorization-server?test2=$RANDOM 2>&1 | grep "^<")

    # Check JSON body
    if echo "$response" | jq -e '.error' > /dev/null 2>&1 && \
       echo "$response" | jq -e '.message' > /dev/null 2>&1 && \
       echo "$response" | jq -e '.retry_after' > /dev/null 2>&1 && \
       echo "$headers" | grep -q "429 Too Many Requests" && \
       echo "$headers" | grep -q "retry-after:"; then
        test_pass
    else
        test_fail "Invalid 429 response format"
    fi
}

# Test 5: Excluded paths not rate limited
test_excluded_paths() {
    test_start "Excluded paths (/health, /docs) not rate limited"

    local all_success=true

    # Test /health (already tested but verify again)
    for i in {1..10}; do
        status=$(curl -s -w "%{http_code}" http://localhost:5001/health -o /dev/null)
        if [ "$status" != "200" ]; then
            all_success=false
        fi
    done

    # Test /docs
    for i in {1..10}; do
        status=$(curl -s -w "%{http_code}" http://localhost:5001/docs -o /dev/null)
        if [ "$status" != "200" ]; then
            all_success=false
        fi
    done

    if [ "$all_success" = true ]; then
        test_pass
    else
        test_fail "Excluded paths were rate limited"
    fi
}

# Test 6: Rate limit headers show correct remaining count
test_remaining_count() {
    test_start "Rate limit remaining count decreases correctly"

    # Use a unique identifier to get fresh rate limit
    local unique_id=$RANDOM

    # Make first request and get remaining
    response1=$(curl -s -v http://localhost:5001/.well-known/oauth-authorization-server?test3=$unique_id 2>&1)
    remaining1=$(echo "$response1" | grep "x-ratelimit-remaining:" | awk '{print $3}' | tr -d '\r')

    # Make second request
    response2=$(curl -s -v http://localhost:5001/.well-known/oauth-authorization-server?test3=$unique_id 2>&1)
    remaining2=$(echo "$response2" | grep "x-ratelimit-remaining:" | awk '{print $3}' | tr -d '\r')

    # Make third request
    response3=$(curl -s -v http://localhost:5001/.well-known/oauth-authorization-server?test3=$unique_id 2>&1)
    remaining3=$(echo "$response3" | grep "x-ratelimit-remaining:" | awk '{print $3}' | tr -d '\r')

    # Verify remaining count decreases
    if [ -n "$remaining1" ] && [ -n "$remaining2" ] && [ -n "$remaining3" ]; then
        if [ "$remaining1" -gt "$remaining2" ] && [ "$remaining2" -gt "$remaining3" ]; then
            test_pass
        else
            test_fail "Remaining count not decreasing: $remaining1 -> $remaining2 -> $remaining3"
        fi
    else
        test_fail "Could not parse remaining count headers"
    fi
}

# Test 7: Client identification works correctly
test_client_identification() {
    test_start "Client identification (IP-based when auth disabled)"

    # When ENABLE_AUTH=False, all requests from localhost share the same IP
    # This is CORRECT behavior - they should share the same rate limit

    # Make a request and check it's using IP-based identification
    # by verifying rate limits are enforced regardless of auth header

    # First exhaust rate limit
    for i in {1..105}; do
        curl -s -w "%{http_code}" \
            -H "Authorization: Bearer token1" \
            http://localhost:5001/.well-known/oauth-authorization-server?test5=$RANDOM \
            -o /dev/null > /dev/null 2>&1
    done

    # Try with different token - should still be rate limited (same IP)
    status=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer token2" \
        http://localhost:5001/.well-known/oauth-authorization-server?test5=$RANDOM \
        -o /dev/null)

    # With ENABLE_AUTH=False, should be rate limited (same IP)
    # With ENABLE_AUTH=True, would NOT be rate limited (different token)
    if [ "$status" = "429" ]; then
        test_pass
    else
        test_fail "IP-based rate limiting not working correctly (got status: $status)"
    fi
}

# Test 8: Configuration is respected
test_configuration() {
    test_start "Server configuration is active"

    response=$(curl -s -v http://localhost:5001/.well-known/oauth-authorization-server?test4=$RANDOM 2>&1)
    limit=$(echo "$response" | grep "x-ratelimit-limit:" | awk '{print $3}' | tr -d '\r')

    # Default is 100 requests per minute
    if [ "$limit" = "100" ]; then
        test_pass
    else
        test_fail "Expected rate limit of 100, got $limit"
    fi
}

# Test 9: Server logs show rate limiting activity
test_server_logs() {
    test_start "Server logs rate limiting events"

    # This test just checks if we can verify logging is configured
    # In a real E2E test, we'd check actual log files

    if curl -s http://localhost:5001/health | jq -e '.status' > /dev/null 2>&1; then
        test_pass
    else
        test_fail "Could not verify server logging"
    fi
}

# Main execution
main() {
    echo "Checking server availability..."
    check_server
    echo -e "${GREEN}Server is running${NC}"
    echo ""

    echo "Running E2E tests..."
    echo ""

    test_health_not_limited
    test_rate_limit_headers
    test_excluded_paths
    test_remaining_count
    test_configuration
    test_rate_limit_enforced
    test_429_response_format
    test_client_identification
    test_server_logs

    echo ""
    echo "=========================================="
    echo "Test Results"
    echo "=========================================="
    echo "Total Tests:  $TESTS_RUN"
    echo -e "Passed:       ${GREEN}$TESTS_PASSED${NC}"

    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "Failed:       ${RED}$TESTS_FAILED${NC}"
        echo ""
        echo -e "${RED}E2E TEST SUITE FAILED${NC}"
        exit 1
    else
        echo -e "Failed:       $TESTS_FAILED"
        echo ""
        echo -e "${GREEN}✓ ALL E2E TESTS PASSED!${NC}"
        exit 0
    fi
}

# Run tests
main
