"""Tests for the event module."""

from datetime import datetime, UTC
from typing import Dict, Any, List, Callable
from eventually import Event, EventBus


def test_event_creation() -> None:
    """Test creating an event with data."""
    data: Dict[str, Any] = {"user_id": 1, "name": "John"}
    event: Event = Event("user.created", data)

    assert event.type == "user.created"
    assert event.data == data
    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo == UTC


def test_event_immutability() -> None:
    """Test that events are immutable."""
    data: Dict[str, Any] = {"user_id": 1, "name": "John"}
    event: Event = Event("user.created", data)

    # Verify we can't modify the event directly
    try:
        event.type = "new.type"  # type: ignore
        assert False, "Should not be able to modify event type"
    except AttributeError:
        pass

    try:
        event.data = {}  # type: ignore
        assert False, "Should not be able to modify event data"
    except AttributeError:
        pass


def test_eventbus_basic_subscription() -> None:
    """Test basic event subscription and publishing."""
    bus: EventBus = EventBus()
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    unsubscribe: Callable[[], None] = bus.subscribe("user.created", handler)
    event: Event = Event("user.created", {"id": 1})
    bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0] == event

    # Test unsubscribing
    unsubscribe()
    bus.publish(event)
    assert len(received_events) == 1  # Should not receive the second event


def test_eventbus_wildcard_subscription() -> None:
    """Test wildcard event subscription."""
    bus: EventBus = EventBus()
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to all user events
    bus.subscribe("user.*", handler)

    # These should be received
    event1: Event = Event("user.created", {"id": 1})
    event2: Event = Event("user.updated", {"id": 1})
    bus.publish(event1)
    bus.publish(event2)

    # This should not be received
    event3: Event = Event("order.created", {"id": 1})
    bus.publish(event3)

    assert len(received_events) == 2
    assert event1 in received_events
    assert event2 in received_events
    assert event3 not in received_events


def test_eventbus_multiple_subscribers() -> None:
    """Test multiple subscribers for the same event type."""
    bus: EventBus = EventBus()
    received1: List[Event] = []
    received2: List[Event] = []

    def handler1(event: Event) -> None:
        received1.append(event)

    def handler2(event: Event) -> None:
        received2.append(event)

    bus.subscribe("user.created", handler1)
    bus.subscribe("user.created", handler2)

    event: Event = Event("user.created", {"id": 1})
    bus.publish(event)

    assert len(received1) == 1
    assert len(received2) == 1
    assert received1[0] == event
    assert received2[0] == event


def test_eventbus_global_subscription() -> None:
    """Test subscribing to all events."""
    bus: EventBus = EventBus()
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    bus.subscribe("*", handler)

    event1: Event = Event("user.created", {"id": 1})
    event2: Event = Event("order.completed", {"id": 2})
    bus.publish(event1)
    bus.publish(event2)

    assert len(received_events) == 2
    assert event1 in received_events
    assert event2 in received_events
