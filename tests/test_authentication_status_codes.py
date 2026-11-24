"""
Tests 17-20: Authentication Status and SubStatus NTSTATUS Codes.
Tests 0xC0000064 (User not found), 0xC000006A (Bad password),
0xC0000234 (Account locked out), and unknown NTSTATUS handling.
"""
from zye_cybersecurity.authentication.status_code_analyzer import StatusCodeAnalyzer


def test_17_user_not_found_0xC0000064():
    """Test 17: 0xC0000064 correctly mapped to STATUS_NO_SUCH_USER."""
    info = StatusCodeAnalyzer.get_status_info("0xC0000064")
    assert info.code == "0xC0000064"
    assert info.symbol == "STATUS_NO_SUCH_USER"
    assert StatusCodeAnalyzer.is_account_not_found("0xC0000064") is True
    assert StatusCodeAnalyzer.is_bad_password("0xC0000064") is False


def test_18_bad_password_0xC000006A():
    """Test 18: 0xC000006A correctly mapped to STATUS_WRONG_PASSWORD."""
    info = StatusCodeAnalyzer.get_status_info("0xC000006A")
    assert info.code == "0xC000006A"
    assert info.symbol == "STATUS_WRONG_PASSWORD"
    assert StatusCodeAnalyzer.is_bad_password("0xC000006A") is True
    assert StatusCodeAnalyzer.is_account_not_found("0xC000006A") is False


def test_19_account_locked_0xC0000234():
    """Test 19: 0xC0000234 correctly mapped to STATUS_ACCOUNT_LOCKED_OUT."""
    info = StatusCodeAnalyzer.get_status_info("0xC0000234")
    assert info.code == "0xC0000234"
    assert info.symbol == "STATUS_ACCOUNT_LOCKED_OUT"
    assert StatusCodeAnalyzer.is_account_locked("0xC0000234") is True


def test_20_unknown_ntstatus_code():
    """Test 20: Unknown NTSTATUS codes handled gracefully with default description."""
    info = StatusCodeAnalyzer.get_status_info("0xC0000999")
    assert info.code == "0xC0000999"
    assert info.symbol == "STATUS_UNKNOWN_FAILURE"
    assert "Unmapped" in info.description or "Unknown" in info.description
