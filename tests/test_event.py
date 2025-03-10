"""Tests for the event module."""

import json as json_lib
from datetime import datetime, timezone
from typing import Any, Dict, List

from eventure import Event


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
