#!/usr/bin/env python3
"""Test script to verify logging security fixes."""

import sys
sys.path.insert(0, '/home/user/AIOps')

from aiops.core.error_handler import _mask_sensitive_data


def test_mask_sensitive_data():
    """Test the sensitive data masking function."""

    print("Testing sensitive data masking...")
    print("=" * 60)

    # Test 1: Basic sensitive fields
    test_data_1 = {
        "username": "alice",
        "password": "super_secret_password",
        "api_key": "sk-1234567890abcdef",
        "normal_field": "safe_value"
    }

    masked_1 = _mask_sensitive_data(test_data_1)
    print("\n1. Basic sensitive fields:")
    print(f"   Input:  {test_data_1}")
    print(f"   Output: {masked_1}")
    assert masked_1["password"] == "***REDACTED***"
    assert masked_1["api_key"] == "***REDACTED***"
    assert masked_1["username"] == "alice"
    assert masked_1["normal_field"] == "safe_value"
    print("   ✅ PASS")

    # Test 2: JWT token masking (field name not sensitive, but value is JWT)
    test_data_2 = {
        "response_data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "user": "john"
    }

    masked_2 = _mask_sensitive_data(test_data_2)
    print("\n2. JWT token value masking:")
    print(f"   Input:  {test_data_2['response_data'][:50]}...")
    print(f"   Output: {masked_2['response_data']}")
    assert masked_2["response_data"] == "***JWT_TOKEN***"
    assert masked_2["user"] == "john"
    print("   ✅ PASS")

    # Test 2b: Sensitive field names (token, api_key, etc.)
    test_data_2b = {
        "token": "any_value_here",
        "api_key": "sk-123456",
    }

    masked_2b = _mask_sensitive_data(test_data_2b)
    print("\n2b. Sensitive field names:")
    print(f"   Input:  {test_data_2b}")
    print(f"   Output: {masked_2b}")
    assert masked_2b["token"] == "***REDACTED***"
    assert masked_2b["api_key"] == "***REDACTED***"
    print("   ✅ PASS")

    # Test 3: Long API key-like strings
    test_data_3 = {
        "access_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
        "short": "abc"
    }

    masked_3 = _mask_sensitive_data(test_data_3)
    print("\n3. Long API key-like strings:")
    print(f"   Input:  {test_data_3['access_token']}")
    print(f"   Output: {masked_3['access_token']}")
    assert masked_3["access_token"] == "***REDACTED***"
    assert masked_3["short"] == "abc"
    print("   ✅ PASS")

    # Test 4: Nested dictionaries
    test_data_4 = {
        "user": {
            "name": "alice",
            "settings": {
                "password": "secret123",
                "api_key": "sk-abcdefgh"
            }
        },
        "config": {
            "timeout": 30
        }
    }

    masked_4 = _mask_sensitive_data(test_data_4)
    print("\n4. Nested dictionaries:")
    print(f"   Input:  {test_data_4}")
    print(f"   Output: {masked_4}")
    assert masked_4["user"]["settings"]["password"] == "***REDACTED***"
    assert masked_4["user"]["settings"]["api_key"] == "***REDACTED***"
    assert masked_4["user"]["name"] == "alice"
    assert masked_4["config"]["timeout"] == 30
    print("   ✅ PASS")

    # Test 4b: Field name contains sensitive word (entire field masked)
    test_data_4b = {
        "user_credentials": {
            "username": "alice",
            "password": "secret"
        }
    }

    masked_4b = _mask_sensitive_data(test_data_4b)
    print("\n4b. Field name with sensitive word:")
    print(f"   Input:  {test_data_4b}")
    print(f"   Output: {masked_4b}")
    # "user_credentials" contains "credential" so entire value is masked
    assert masked_4b["user_credentials"] == "***REDACTED***"
    print("   ✅ PASS")

    # Test 5: Lists with dictionaries
    test_data_5 = {
        "users": [
            {"name": "alice", "secret": "key1"},
            {"name": "bob", "secret": "key2"}
        ]
    }

    masked_5 = _mask_sensitive_data(test_data_5)
    print("\n5. Lists with dictionaries:")
    print(f"   Input:  {test_data_5}")
    print(f"   Output: {masked_5}")
    assert masked_5["users"][0]["secret"] == "***REDACTED***"
    assert masked_5["users"][1]["secret"] == "***REDACTED***"
    assert masked_5["users"][0]["name"] == "alice"
    print("   ✅ PASS")

    # Test 6: Various field name patterns
    test_data_6 = {
        "client_secret": "abc123",
        "client-id": "def456",
        "webhook_secret": "ghi789",
        "bearer": "jkl012",
        "authorization": "Bearer token123",
        "normal_data": "safe"
    }

    masked_6 = _mask_sensitive_data(test_data_6)
    print("\n6. Various field name patterns:")
    print(f"   Input:  {test_data_6}")
    print(f"   Output: {masked_6}")
    assert masked_6["client_secret"] == "***REDACTED***"
    assert masked_6["client-id"] == "***REDACTED***"
    assert masked_6["webhook_secret"] == "***REDACTED***"
    assert masked_6["bearer"] == "***REDACTED***"
    assert masked_6["authorization"] == "***REDACTED***"
    assert masked_6["normal_data"] == "safe"
    print("   ✅ PASS")

    print("\n" + "=" * 60)
    print("✅ All tests passed! Sensitive data masking is working correctly.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_mask_sensitive_data()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
