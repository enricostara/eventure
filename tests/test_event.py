"""Tests for the event module."""

import tempfile
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from eventure import Event, EventBus, EventLog


def test_event_creation() -> None:
    """Test creating an event with tick, timestamp, type and data."""
    tick: int = 1
    timestamp: float = datetime.now(timezone.utc).timestamp()
    event_type: str = "user.created"
    data: Dict[str, Any] = {"user_id": 1, "name": "John"}

    event: Event = Event(tick=tick, timestamp=timestamp, type=event_type, data=data)

    assert event.tick == tick
    assert event.timestamp == timestamp
    assert event.type == event_type
    assert event.data == data


def test_event_json_serialization() -> None:
    """Test event serialization to and from JSON."""
    tick: int = 1
    timestamp: float = datetime.now(timezone.utc).timestamp()
    event_type: str = "user.created"
    data: Dict[str, Any] = {"user_id": 1, "name": "John"}

    event: Event = Event(tick=tick, timestamp=timestamp, type=event_type, data=data)

    # Serialize to JSON
    json_str: str = event.to_json()
    assert isinstance(json_str, str)

    # Deserialize from JSON
    deserialized_event: Event = Event.from_json(json_str)

    # Verify all properties match
    assert deserialized_event.tick == event.tick
    assert deserialized_event.timestamp == event.timestamp
    assert deserialized_event.type == event.type
    assert deserialized_event.data == event.data


def test_eventlog_basic_operations() -> None:
    """Test basic EventLog operations: adding events and advancing ticks."""
    log: EventLog = EventLog()

    # Initial state
    assert log.current_tick == 0
    assert len(log.events) == 0

    # Add an event
    event: Event = log.add_event("user.created", {"user_id": 1})
    assert event.tick == 0
    assert event.type == "user.created"
    assert len(log.events) == 1

    # Advance tick
    log.advance_tick()
    assert log.current_tick == 1

    # Add another event
    event2: Event = log.add_event("user.updated", {"user_id": 1, "name": "Updated"})
    assert event2.tick == 1
    assert len(log.events) == 2

    # Get events at a specific tick
    tick0_events: List[Event] = log.get_events_at_tick(0)
    assert len(tick0_events) == 1
    assert tick0_events[0].type == "user.created"

    tick1_events: List[Event] = log.get_events_at_tick(1)
    assert len(tick1_events) == 1
    assert tick1_events[0].type == "user.updated"


def test_eventlog_file_persistence() -> None:
    """Test saving and loading EventLog to/from file."""
    log: EventLog = EventLog()

    # Add some events
    log.add_event("user.created", {"user_id": 1})
    log.advance_tick()
    log.add_event("user.updated", {"user_id": 1, "name": "Updated"})

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        filename: str = temp_file.name
        log.save_to_file(filename)

    # Load from file
    loaded_log: EventLog = EventLog.load_from_file(filename)

    # Verify loaded log matches original
    assert len(loaded_log.events) == len(log.events)
    assert loaded_log.current_tick == log.current_tick

    # Check specific events
    assert loaded_log.events[0].type == "user.created"
    assert loaded_log.events[1].type == "user.updated"


def test_eventbus_basic_subscription() -> None:
    """Test basic event subscription and publishing."""
    log: EventLog = EventLog()
    bus: EventBus = EventBus(log)
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to an event type
    unsubscribe: Callable[[], None] = bus.subscribe("user.created", handler)

    # Publish an event
    bus.publish("user.created", {"user_id": 1})

    # Verify handler was called
    assert len(received_events) == 1
    assert received_events[0].type == "user.created"
    assert received_events[0].data["user_id"] == 1
    assert received_events[0].tick == 0  # Current tick from EventLog

    # Test unsubscribing
    unsubscribe()
    bus.publish("user.created", {"user_id": 2})
    assert len(received_events) == 1  # Should not receive the second event


def test_eventbus_without_eventlog() -> None:
    """Test EventBus without an EventLog."""
    bus: EventBus = EventBus()  # No EventLog provided
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    bus.subscribe("user.created", handler)

    # Publish with explicit tick
    event: Event = bus.publish("user.created", {"user_id": 1}, tick=5)

    assert event.tick == 5
    assert len(received_events) == 1
    assert received_events[0].tick == 5

    # Publish without tick (should default to 0)
    event2: Event = bus.publish("user.created", {"user_id": 2})
    assert event2.tick == 0
    assert received_events[1].tick == 0


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

    event: Event = bus.publish("user.created", {"user_id": 1})

    assert len(received1) == 1
    assert len(received2) == 1
    assert received1[0] == event
    assert received2[0] == event


def test_eventbus_wildcard_subscription() -> None:
    """Test wildcard event subscription."""
    bus: EventBus = EventBus()
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to all user events with wildcard
    bus.subscribe("user.*", handler)

    # These should be received (user.*)
    event1: Event = bus.publish("user.created", {"user_id": 1})
    event2: Event = bus.publish("user.updated", {"user_id": 1})

    assert len(received_events) == 2
    assert received_events[0] == event1
    assert received_events[1] == event2


def test_eventbus_global_subscription() -> None:
    """Test subscribing to all events with wildcard."""
    bus: EventBus = EventBus()
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to all events with wildcard
    bus.subscribe("*", handler)

    # Publish different event types
    event1: Event = bus.publish("user.created", {"user_id": 1})
    event2: Event = bus.publish("order.completed", {"order_id": 2})

    # Verify all events were received
    assert len(received_events) == 2
    assert received_events[0] == event1
    assert received_events[1] == event2


def test_eventbus_set_event_log() -> None:
    """Test setting EventLog after EventBus creation."""
    bus: EventBus = EventBus()  # No EventLog initially
    log: EventLog = EventLog()

    # Advance tick in the log
    log.advance_tick()
    log.advance_tick()  # Now at tick 2

    # Set the EventLog
    bus.set_event_log(log)

    # Publish an event (should use current tick from EventLog)
    event: Event = bus.publish("test.event", {})

    assert event.tick == 2  # Should use current tick from EventLog
