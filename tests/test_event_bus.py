"""
ZYE AI — Unit Tests: Unified Event Bus Engine
=============================================

Tests:
- Specific event subscriptions and callbacks
- Wildcard subscriptions
- Payload secret redaction (API keys, passwords)
- Bounded event history (overflow eviction)
- Observer exception isolation
"""

from zye_core.event_bus import ZyeEventBus, get_event_bus, reset_event_bus, redact_payload
from zye_core.types import ZyeEvent, ZyeEventType


def test_event_bus_publish_and_subscribe():
    bus = ZyeEventBus(history_limit=10)
    received = []

    def on_user_speech(ev: ZyeEvent):
        received.append(ev)

    bus.subscribe(ZyeEventType.USER_SPEECH_STARTED, on_user_speech)
    ev = bus.publish(
        event_type=ZyeEventType.USER_SPEECH_STARTED,
        source_module="test_module",
        payload={"utterance": "hello"},
        session_id="sess_1",
    )

    assert len(received) == 1
    assert received[0].event_id == ev.event_id
    assert received[0].payload["utterance"] == "hello"


def test_event_bus_wildcard_subscription():
    bus = ZyeEventBus(history_limit=10)
    all_events = []

    bus.subscribe_all(lambda ev: all_events.append(ev))
    bus.publish(ZyeEventType.SESSION_STARTED, "test")
    bus.publish(ZyeEventType.SESSION_ENDED, "test")

    assert len(all_events) == 2
    assert all_events[0].event_type == ZyeEventType.SESSION_STARTED
    assert all_events[1].event_type == ZyeEventType.SESSION_ENDED


def test_event_bus_payload_secret_redaction():
    raw_payload = {
        "api_key": "AIzaSySecretKey12345",
        "user_query": "Bearer my_secret_token_abc",
        "nested": {"token": "top_secret_xyz"},
        "normal_field": "safe_value",
    }
    redacted = redact_payload(raw_payload)

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["normal_field"] == "safe_value"
    assert "AIzaSy" not in str(redacted)


def test_event_bus_bounded_history():
    bus = ZyeEventBus(history_limit=5)
    for i in range(12):
        bus.publish(ZyeEventType.TASK_STARTED, "test", payload={"index": i})

    hist = bus.get_history()
    assert len(hist) == 5
    assert hist[-1].payload["index"] == 11
    assert hist[0].payload["index"] == 7


def test_event_bus_observer_exception_isolation():
    bus = ZyeEventBus(history_limit=10)
    results = []

    def broken_callback(ev):
        raise RuntimeError("Crash in subscriber!")

    def working_callback(ev):
        results.append(ev.event_type)

    bus.subscribe(ZyeEventType.SECURITY_ALERT, broken_callback)
    bus.subscribe(ZyeEventType.SECURITY_ALERT, working_callback)

    # Should not raise exception
    bus.publish(ZyeEventType.SECURITY_ALERT, "sec_monitor")
    assert len(results) == 1
    assert results[0] == ZyeEventType.SECURITY_ALERT
