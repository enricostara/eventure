"""Tests for the event_query module."""

import io
from typing import Dict, List, TextIO

from eventure import Event, EventLog, EventQuery


def test_event_query_initialization() -> None:
    """Test initializing EventQuery with an event log."""
    log: EventLog = EventLog()
    query: EventQuery = EventQuery(log)

    assert query.event_log == log


def test_group_events_by_tick() -> None:
    """Test grouping events by tick."""
    log: EventLog = EventLog()

    # Add events at different ticks
    event1: Event = log.add_event("test.event1", {"value": 1})
    log.advance_tick()
    event2: Event = log.add_event("test.event2", {"value": 2})
    event3: Event = log.add_event("test.event3", {"value": 3})
    log.advance_tick()
    event4: Event = log.add_event("test.event4", {"value": 4})

    query: EventQuery = EventQuery(log)
    events_by_tick: Dict[int, List[Event]] = query._group_events_by_tick()

    # Verify grouping
    assert len(events_by_tick) == 3
    assert len(events_by_tick[0]) == 1
    assert len(events_by_tick[1]) == 2
    assert len(events_by_tick[2]) == 1

    assert events_by_tick[0][0] == event1
    assert event2 in events_by_tick[1]
    assert event3 in events_by_tick[1]
    assert events_by_tick[2][0] == event4


def test_identify_root_and_child_events() -> None:
    """Test identifying root and child events within a tick."""
    log: EventLog = EventLog()

    # Create parent event
    parent_event: Event = log.add_event("test.parent", {"value": 1})

    # Create child events in same tick
    child_event1: Event = log.add_event("test.child1", {"value": 2}, parent_event=parent_event)
    child_event2: Event = log.add_event("test.child2", {"value": 3}, parent_event=parent_event)

    # Create another root event in same tick
    other_root: Event = log.add_event("test.other", {"value": 4})

    query: EventQuery = EventQuery(log)
    tick_events: List[Event] = log.get_events_at_tick(0)

    root_events, child_events = query._identify_root_and_child_events(tick_events)

    # Verify root events
    assert len(root_events) == 2
    assert parent_event in root_events
    assert other_root in root_events

    # Verify child events
    assert len(child_events) == 2
    assert child_event1.id in child_events
    assert child_event2.id in child_events


def test_get_sorted_children() -> None:
    """Test getting sorted children of an event."""
    log: EventLog = EventLog()

    # Create parent event
    parent_event: Event = log.add_event("test.parent", {"value": 1})

    # Create child events in same tick with different types
    child_event1: Event = log.add_event(
        "test.child_b", {"value": 2}, parent_event=parent_event
    )
    child_event2: Event = log.add_event(
        "test.child_a", {"value": 3}, parent_event=parent_event
    )

    # Create another event in same tick (not a child)
    log.add_event("test.other", {"value": 4})

    query: EventQuery = EventQuery(log)
    tick_events: List[Event] = log.get_events_at_tick(0)

    # Identify child events
    _, child_events = query._identify_root_and_child_events(tick_events)

    # Get sorted children
    sorted_children: List[Event] = query._get_sorted_children(
        parent_event, tick_events, child_events
    )

    # Verify sorting (should be sorted by type)
    assert len(sorted_children) == 2
    assert sorted_children[0] == child_event2  # child_a comes before child_b
    assert sorted_children[1] == child_event1


def test_get_event_display_info() -> None:
    """Test getting display info for different types of events."""
    log: EventLog = EventLog()

    # Create root event
    root_event: Event = log.add_event("test.root", {"value": 1})

    # Create child event in same tick
    same_tick_child: Event = log.add_event("test.child", {"value": 2}, parent_event=root_event)

    # Create event in next tick with parent from previous tick
    log.advance_tick()
    cross_tick_child: Event = log.add_event(
        "test.cross_tick", {"value": 3}, parent_event=root_event
    )

    query: EventQuery = EventQuery(log)

    # Test root event (no parent)
    prefix, info = query._get_event_display_info(root_event)
    assert prefix == "●"
    assert info == ""

    # Test child event in same tick
    prefix, info = query._get_event_display_info(same_tick_child)
    assert prefix == "└─"
    assert info == ""

    # Test child event from previous tick
    prefix, info = query._get_event_display_info(cross_tick_child)
    assert prefix == "↓"
    assert "caused by" in info
    assert "test.root" in info
    assert "tick 0" in info


def test_print_event_cascade() -> None:
    """Test printing event cascade to a file-like object."""
    log: EventLog = EventLog()

    # Create a simple event cascade across multiple ticks
    root_event: Event = log.add_event("test.root", {"value": 1})
    child1: Event = log.add_event("test.child1", {"value": 2}, parent_event=root_event)

    log.advance_tick()
    log.add_event("test.child2", {"value": 3}, parent_event=root_event)
    log.add_event("test.grandchild", {"value": 4}, parent_event=child1)

    query: EventQuery = EventQuery(log)

    # Capture output
    output: TextIO = io.StringIO()
    query.print_event_cascade(file=output, show_data=True)

    # Verify output contains expected elements
    result: str = output.getvalue()

    # Check for basic structure
    assert "===== EVENT CASCADE VIEWER =====" in result
    assert "TICK 0" in result
    assert "TICK 1" in result

    # Check for events
    assert "test.root" in result
    assert "test.child1" in result
    assert "test.child2" in result
    assert "test.grandchild" in result

    # Check for data
    assert "value: 1" in result
    assert "value: 2" in result
    assert "value: 3" in result
    assert "value: 4" in result

    # Check for relationships
    assert "Triggers events in tick 1" in result
    assert "caused by: test.root @ tick 0" in result
    assert "caused by: test.child1 @ tick 0" in result


def test_print_event_cascade_no_data() -> None:
    """Test printing event cascade without event data."""
    log: EventLog = EventLog()

    # Create a simple event
    log.add_event("test.event", {"value": 1})

    query: EventQuery = EventQuery(log)

    # Capture output with show_data=False
    output: TextIO = io.StringIO()
    query.print_event_cascade(file=output, show_data=False)

    # Verify output doesn't contain data
    result: str = output.getvalue()
    assert "test.event" in result
    assert "value: 1" not in result


def test_print_event_cascade_empty_log() -> None:
    """Test printing event cascade with an empty event log."""
    log: EventLog = EventLog()
    query: EventQuery = EventQuery(log)

    # Capture output
    output: TextIO = io.StringIO()
    query.print_event_cascade(file=output)

    # Verify output
    result: str = output.getvalue()
    assert "===== EVENT CASCADE VIEWER =====" in result
    assert "<No events in log>" in result


def test_print_future_triggers() -> None:
    """Test printing information about future events triggered by an event."""
    log: EventLog = EventLog()

    # Create parent event
    parent_event: Event = log.add_event("test.parent", {"value": 1})

    # Create future children in different ticks
    log.advance_tick()
    log.add_event("test.child1", {"value": 2}, parent_event=parent_event)

    log.advance_tick()
    log.add_event("test.child2", {"value": 3}, parent_event=parent_event)
    log.add_event("test.child3", {"value": 4}, parent_event=parent_event)

    query: EventQuery = EventQuery(log)

    # Capture output
    output: TextIO = io.StringIO()
    query._print_future_triggers(parent_event, "  ", "●", file=output)

    # Verify output
    result: str = output.getvalue()
    assert "Triggers events in" in result
    assert "tick 1 (1)" in result
    assert "tick 2 (2)" in result
