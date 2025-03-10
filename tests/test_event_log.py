"""Tests for the event_log module."""

import tempfile
from typing import List

from eventure import Event, EventLog


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


def test_event_cascade_tracking() -> None:
    """Test tracking cascades of related events."""
    log: EventLog = EventLog()

    # Create a chain of events: A -> B -> C -> D
    # Where A is the root event, and each subsequent event is caused by the previous one

    # Root event (A)
    event_a: Event = log.add_event("user.created", {"user_id": 1})

    # First child event (B)
    log.advance_tick()
    # Create event B with parent_event parameter
    event_b: Event = log.add_event("user.verified", {"user_id": 1}, parent_event=event_a)

    # Second child event (C)
    log.advance_tick()
    # Create event C with parent_event parameter
    event_c: Event = log.add_event(
        "user.updated", {"user_id": 1, "name": "John"}, parent_event=event_b
    )

    # Third child event (D)
    log.advance_tick()
    # Create event D with parent_event parameter
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
