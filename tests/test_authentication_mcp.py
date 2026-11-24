"""
Tests 37-39: Authentication MCP Tools Integration.
Tests cyber_security_mcp.py tool registration, execution, and JSON output structure.
"""
import json
import pytest
import cyber_security_mcp


def test_37_mcp_tools_registration():
    """Test 37: Verify all 13 security MCP tools are properly registered."""
    mcp_instance = cyber_security_mcp.mcp
    tools = getattr(mcp_instance, "_tools", None)
    if tools is None and hasattr(mcp_instance, "_tool_manager"):
        tools = mcp_instance._tool_manager._tools
    assert tools is not None
    assert len(tools) == 13

    expected_tools = [
        "detect_unauthorized_access",
        "get_failed_login_events",
        "analyze_authentication_patterns",
        "get_authentication_security_status",
        "get_security_alerts",
    ]
    for tool_name in expected_tools:
        assert tool_name in tools, f"Expected MCP tool {tool_name} not found"


def test_38_detect_unauthorized_access_execution():
    """Test 38: detect_unauthorized_access executes safely and returns expected structure."""
    raw = cyber_security_mcp.detect_unauthorized_access(minutes=15)
    assert isinstance(raw, str)
    result = json.loads(raw)
    assert "status" in result
    assert "timestamp_utc" in result
    assert "failed_logins_summary" in result
    assert "port_analysis" in result
    assert "overall_threat_level" in result


def test_39_authentication_mcp_tools_safe_execution():
    """Test 39: Authentication status, patterns, and alerts tools run safely."""
    raw_status = cyber_security_mcp.get_authentication_security_status()
    assert isinstance(raw_status, str)
    status_res = json.loads(raw_status)
    assert "windows_audit_capability" in status_res
    assert "detection_policy" in status_res

    raw_patterns = cyber_security_mcp.analyze_authentication_patterns(minutes=10)
    assert isinstance(raw_patterns, str)
    patterns_res = json.loads(raw_patterns)
    assert "findings" in patterns_res

    raw_alerts = cyber_security_mcp.get_security_alerts(limit=5)
    assert isinstance(raw_alerts, str)
    alerts_res = json.loads(raw_alerts)
    assert "alerts" in alerts_res
