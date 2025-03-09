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
    assert event.id is not None  # Event ID should be automatically generated


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
    assert deserialized_event.id == event.id  # Event ID should be preserved


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


def test_event_id_generation() -> None:
    """Test the event ID generation functionality."""
    # Create events with the same tick and type
    tick: int = 5
    event_type: str = "user.created"
    timestamp: float = datetime.now(timezone.utc).timestamp()

    # Reset the event sequences to ensure consistent test results
    Event._event_sequences = {}

    # Create multiple events with the same tick and type
    event1: Event = Event(tick=tick, timestamp=timestamp, type=event_type, data={})
    event2: Event = Event(tick=tick, timestamp=timestamp, type=event_type, data={})

    # IDs should follow the format: {tick}-{typeHash}-{sequence}
    assert event1.id is not None
    assert event2.id is not None

    # Extract parts of the ID
    parts1: List[str] = event1.id.split("-")
    parts2: List[str] = event2.id.split("-")

    # Check format: tick-typeHash-sequence
    assert len(parts1) == 3
    assert len(parts2) == 3

    # Tick should match
    assert parts1[0] == str(tick)
    assert parts2[0] == str(tick)

    # Type hash should be the same for the same event type
    assert parts1[1] == parts2[1]
    assert len(parts1[1]) == 4  # 4-character hash
    assert parts1[1].isalpha()  # Should be all alpha
    assert parts1[1].isupper()  # Should be uppercase

    # Sequence should increment
    assert int(parts2[2]) == int(parts1[2]) + 1


def test_event_id_uniqueness() -> None:
    """Test that event IDs are unique across different ticks and types."""
    # Reset the event sequences
    Event._event_sequences = {}

    timestamp: float = datetime.now(timezone.utc).timestamp()

    # Create events with different ticks and types
    event1: Event = Event(tick=1, timestamp=timestamp, type="user.created", data={})
    event2: Event = Event(tick=1, timestamp=timestamp, type="user.updated", data={})
    event3: Event = Event(tick=2, timestamp=timestamp, type="user.created", data={})

    # All IDs should be different
    assert event1.id != event2.id
    assert event1.id != event3.id
    assert event2.id != event3.id

    # Check that the tick part is correct
    assert event1.id.startswith("1-")
    assert event2.id.startswith("1-")
    assert event3.id.startswith("2-")

    # Create multiple events with the same tick and type
    event4: Event = Event(tick=3, timestamp=timestamp, type="user.deleted", data={})
    event5: Event = Event(tick=3, timestamp=timestamp, type="user.deleted", data={})
    event6: Event = Event(tick=3, timestamp=timestamp, type="user.deleted", data={})

    # Extract sequence numbers
    seq4: int = int(event4.id.split("-")[2])
    seq5: int = int(event5.id.split("-")[2])
    seq6: int = int(event6.id.split("-")[2])

    # Sequences should increment correctly
    assert seq5 == seq4 + 1
    assert seq6 == seq5 + 1


def test_explicit_event_id() -> None:
    """Test providing an explicit event ID."""
    tick: int = 10
    timestamp: float = datetime.now(timezone.utc).timestamp()
    event_type: str = "user.created"
    data: Dict[str, Any] = {"user_id": 1}
    explicit_id: str = "custom-id-123"

    # Create event with explicit ID
    event: Event = Event(
        tick=tick, timestamp=timestamp, type=event_type, data=data, id=explicit_id
    )

    # ID should be the one we provided
    assert event.id == explicit_id

    # Serialization and deserialization should preserve the ID
    json_str: str = event.to_json()
    deserialized_event: Event = Event.from_json(json_str)
    assert deserialized_event.id == explicit_id


def test_event_id_in_json() -> None:
    """Test that event ID is properly included in JSON serialization."""
    tick: int = 7
    timestamp: float = datetime.now(timezone.utc).timestamp()
    event_type: str = "user.login"
    data: Dict[str, Any] = {"user_id": 42}

    # Create an event
    event: Event = Event(tick=tick, timestamp=timestamp, type=event_type, data=data)

    # Convert to JSON
    json_str: str = event.to_json()

    # Parse JSON manually to verify event_id is included
    import json as json_lib

    parsed_json = json_lib.loads(json_str)

    assert "event_id" in parsed_json
    assert parsed_json["event_id"] == event.id


def test_event_with_parent() -> None:
    """Test creating an event with a parent event reference."""
    # Create parent event
    parent_event: Event = Event(
        tick=1,
        timestamp=datetime.now(timezone.utc).timestamp(),
        type="user.created",
        data={"user_id": 1},
    )

    # Create child event referencing parent
    child_event: Event = Event(
        tick=2,
        timestamp=datetime.now(timezone.utc).timestamp(),
        type="user.updated",
        data={"user_id": 1, "name": "Updated"},
        parent_id=parent_event.id,
    )

    # Verify parent reference
    assert child_event.parent_id == parent_event.id

    # Test serialization and deserialization preserves parent_id
    json_str: str = child_event.to_json()
    deserialized_event: Event = Event.from_json(json_str)
    assert deserialized_event.parent_id == parent_event.id


def test_eventlog_add_event_with_parent() -> None:
    """Test adding an event with a parent event reference to EventLog."""
    log: EventLog = EventLog()

    # Add parent event
    parent_event: Event = log.add_event("user.created", {"user_id": 1})

    # Advance tick
    log.advance_tick()

    # Add child event with parent reference
    child_event: Event = log.add_event(
        "user.updated", {"user_id": 1, "name": "Updated"}, parent_event=parent_event
    )

    # Verify parent reference
    assert child_event.parent_id == parent_event.id

    # Test retrieving event by ID
    retrieved_parent: Event = log.get_event_by_id(parent_event.id)
    assert retrieved_parent is not None
    assert retrieved_parent.id == parent_event.id
    assert retrieved_parent.type == "user.created"


def test_eventbus_publish_with_parent() -> None:
    """Test publishing an event with a parent event reference via EventBus."""
    bus: EventBus = EventBus()
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to both event types
    bus.subscribe("user.created", handler)
    bus.subscribe("user.updated", handler)

    # Publish parent event
    parent_event: Event = bus.publish("user.created", {"user_id": 1})

    # Publish child event with parent reference
    child_event: Event = bus.publish(
        "user.updated", {"user_id": 1, "name": "Updated"}, parent_event=parent_event
    )

    # Verify parent reference
    assert child_event.parent_id == parent_event.id

    # Verify both events were received by handler
    assert len(received_events) == 2
    assert received_events[0].id == parent_event.id
    assert received_events[1].id == child_event.id
    assert received_events[1].parent_id == parent_event.id


def test_event_cascade_tracking() -> None:
    """Test tracking cascades of related events."""
    log: EventLog = EventLog()

    # Create a chain of events: A -> B -> C -> D
    # Where A is the root event, and each subsequent event is caused by the previous one

    # Root event (A)
    event_a: Event = log.add_event("user.created", {"user_id": 1})

    # First child event (B)
    log.advance_tick()
    event_b: Event = log.add_event("user.verified", {"user_id": 1}, parent_event=event_a)

    # Second child event (C)
    log.advance_tick()
    event_c: Event = log.add_event(
        "user.updated", {"user_id": 1, "name": "John"}, parent_event=event_b
    )

    # Third child event (D)
    log.advance_tick()
    event_d: Event = log.add_event("user.logged_in", {"user_id": 1}, parent_event=event_c)

    # Also add an unrelated event (X)
    log.advance_tick()
    event_x: Event = log.add_event("system.backup", {"status": "completed"})

    # Get cascade starting from root event A
    cascade_a: List[Event] = log.get_event_cascade(event_a.id)

    # Should include A, B, C, D but not X
    assert len(cascade_a) == 4
    assert cascade_a[0].id == event_a.id  # Root event should be first
    assert cascade_a[1].id == event_b.id
    assert cascade_a[2].id == event_c.id
    assert cascade_a[3].id == event_d.id

    # Get cascade starting from event B
    cascade_b: List[Event] = log.get_event_cascade(event_b.id)

    # Should include B, C, D but not A or X
    assert len(cascade_b) == 3
    assert cascade_b[0].id == event_b.id
    assert cascade_b[1].id == event_c.id
    assert cascade_b[2].id == event_d.id

    # Get cascade for the unrelated event X
    cascade_x: List[Event] = log.get_event_cascade(event_x.id)

    # Should only include X
    assert len(cascade_x) == 1
    assert cascade_x[0].id == event_x.id
