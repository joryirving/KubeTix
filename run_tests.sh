#!/bin/bash
# Comprehensive test runner for KubeContext Manager

set -e

echo "🧪 Running KubeContext Manager Test Suite"
echo "=========================================="
echo ""

# Run unit tests
echo "📦 Unit Tests"
echo "-------------"
python3 test_kc_share.py -v
echo ""

# Run integration tests
echo "🔌 Integration Tests"
echo "--------------------"
python3 test_integration.py -v
echo ""

echo "=========================================="
echo "✅ All tests passed!"
echo "=========================================="
