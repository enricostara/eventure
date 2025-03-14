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

    # Verify sorting (should be sorted by timestamp)
    assert len(sorted_children) == 2
    assert sorted_children[0] == child_event1  # First created event comes first
    assert sorted_children[1] == child_event2  # Second created event comes second


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


def test_get_events_by_type() -> None:
    """Test getting events by type."""
    log: EventLog = EventLog()

    # Add events of different types
    log.add_event("test.type1", {"value": 1})
    log.add_event("test.type1", {"value": 2})
    log.add_event("test.type2", {"value": 3})
    log.add_event("test.type3", {"value": 4})

    query: EventQuery = EventQuery(log)

    # Test getting events by type
    type1_events: List[Event] = query.get_events_by_type("test.type1")
    type2_events: List[Event] = query.get_events_by_type("test.type2")
    type3_events: List[Event] = query.get_events_by_type("test.type3")
    nonexistent_events: List[Event] = query.get_events_by_type("test.nonexistent")

    # Verify results
    assert len(type1_events) == 2
    assert all(e.type == "test.type1" for e in type1_events)

    assert len(type2_events) == 1
    assert type2_events[0].type == "test.type2"

    assert len(type3_events) == 1
    assert type3_events[0].type == "test.type3"

    assert len(nonexistent_events) == 0


def test_get_events_by_data() -> None:
    """Test getting events by data key-value pair."""
    log: EventLog = EventLog()

    # Add events with different data
    log.add_event("test.event", {"key1": "value1", "key2": "value2"})
    log.add_event("test.event", {"key1": "value1", "key2": "different"})
    log.add_event("test.event", {"key1": "different", "key3": "value3"})

    query: EventQuery = EventQuery(log)

    # Test getting events by data
    key1_value1_events: List[Event] = query.get_events_by_data("key1", "value1")
    key2_value2_events: List[Event] = query.get_events_by_data("key2", "value2")
    key3_value3_events: List[Event] = query.get_events_by_data("key3", "value3")
    nonexistent_events: List[Event] = query.get_events_by_data("nonexistent", "value")

    # Verify results
    assert len(key1_value1_events) == 2
    assert all(e.data["key1"] == "value1" for e in key1_value1_events)

    assert len(key2_value2_events) == 1
    assert key2_value2_events[0].data["key2"] == "value2"

    assert len(key3_value3_events) == 1
    assert key3_value3_events[0].data["key3"] == "value3"

    assert len(nonexistent_events) == 0


def test_get_child_events() -> None:
    """Test getting direct child events of a parent event."""
    log: EventLog = EventLog()

    # Create parent events
    parent1: Event = log.add_event("test.parent1", {"value": 1})
    parent2: Event = log.add_event("test.parent2", {"value": 2})

    # Create child events
    child1: Event = log.add_event("test.child1", {"value": 3}, parent_event=parent1)
    child2: Event = log.add_event("test.child2", {"value": 4}, parent_event=parent1)
    child3: Event = log.add_event("test.child3", {"value": 5}, parent_event=parent2)

    # Create grandchild event
    log.add_event("test.grandchild", {"value": 6}, parent_event=child1)

    query: EventQuery = EventQuery(log)

    # Test getting child events
    parent1_children: List[Event] = query.get_child_events(parent1)
    parent2_children: List[Event] = query.get_child_events(parent2)
    child1_children: List[Event] = query.get_child_events(child1)
    child2_children: List[Event] = query.get_child_events(child2)

    # Verify results
    assert len(parent1_children) == 2
    assert child1 in parent1_children
    assert child2 in parent1_children

    assert len(parent2_children) == 1
    assert child3 in parent2_children

    assert len(child1_children) == 1

    assert len(child2_children) == 0


def test_get_cascade_events() -> None:
    """Test getting all events in a cascade starting from a root event."""
    log: EventLog = EventLog()

    # Create a cascade of events
    root: Event = log.add_event("test.root", {"value": 1})

    child1: Event = log.add_event("test.child1", {"value": 2}, parent_event=root)
    child2: Event = log.add_event("test.child2", {"value": 3}, parent_event=root)

    grandchild1: Event = log.add_event("test.grandchild1", {"value": 4}, parent_event=child1)
    grandchild2: Event = log.add_event("test.grandchild2", {"value": 5}, parent_event=child2)

    great_grandchild: Event = log.add_event(
        "test.great_grandchild", {"value": 6}, parent_event=grandchild1
    )

    # Create an unrelated event
    log.add_event("test.unrelated", {"value": 7})

    query: EventQuery = EventQuery(log)

    # Test getting cascade events
    root_cascade: List[Event] = query.get_cascade_events(root)
    child1_cascade: List[Event] = query.get_cascade_events(child1)
    grandchild2_cascade: List[Event] = query.get_cascade_events(grandchild2)

    # Verify results
    assert len(root_cascade) == 6  # root + 2 children + 2 grandchildren + 1 great-grandchild
    assert root in root_cascade
    assert child1 in root_cascade
    assert child2 in root_cascade
    assert grandchild1 in root_cascade
    assert grandchild2 in root_cascade
    assert great_grandchild in root_cascade

    assert len(child1_cascade) == 3  # child1 + grandchild1 + great-grandchild
    assert child1 in child1_cascade
    assert grandchild1 in child1_cascade
    assert great_grandchild in child1_cascade

    assert len(grandchild2_cascade) == 1  # just grandchild2


def test_print_event_details() -> None:
    """Test printing details of a single event."""
    log: EventLog = EventLog()

    # Create an event with data
    event: Event = log.add_event("test.event", {"key1": "value1", "key2": 42})

    query: EventQuery = EventQuery(log)

    # Capture output
    output: TextIO = io.StringIO()
    query.print_event_details(event, file=output)

    # Verify output
    result: str = output.getvalue()

    assert "● test.event" in result
    assert f"ID: {event.id}" in result
    assert "Data:" in result
    assert "key1: value1" in result
    assert "key2: 42" in result


def test_print_single_cascade() -> None:
    """Test printing a single event cascade starting from a root event."""
    log: EventLog = EventLog()

    # Create a simple cascade
    root: Event = log.add_event("test.root", {"value": 1})
    _child: Event = log.add_event("test.child", {"value": 2}, parent_event=root)

    query: EventQuery = EventQuery(log)

    # Capture output
    output: TextIO = io.StringIO()
    query.print_single_cascade(root, file=output)

    # Verify output
    result: str = output.getvalue()

    assert "test.root" in result
    assert "test.child" in result
    assert "value: 1" in result
    assert "value: 2" in result


def test_count_events_by_type() -> None:
    """Test counting events by type."""
    log: EventLog = EventLog()

    # Add events of different types
    log.add_event("test.type1", {"value": 1})
    log.add_event("test.type1", {"value": 2})
    log.add_event("test.type2", {"value": 3})
    log.add_event("test.type2", {"value": 4})
    log.add_event("test.type2", {"value": 5})
    log.add_event("test.type3", {"value": 6})

    query: EventQuery = EventQuery(log)

    # Test counting events by type
    counts: Dict[str, int] = query.count_events_by_type()

    # Verify counts
    assert len(counts) == 3
    assert counts["test.type1"] == 2
    assert counts["test.type2"] == 3
    assert counts["test.type3"] == 1


def test_get_events_at_tick() -> None:
    """Test getting all events at a specific tick."""
    log: EventLog = EventLog()

    # Add events at different ticks
    log.add_event("test.event", {"tick": 0})
    log.add_event("test.event", {"tick": 0})

    log.advance_tick()
    log.add_event("test.event", {"tick": 1})

    log.advance_tick()
    log.add_event("test.event", {"tick": 2})
    log.add_event("test.event", {"tick": 2})
    log.add_event("test.event", {"tick": 2})

    query: EventQuery = EventQuery(log)

    # Test getting events at specific ticks
    tick0_events: List[Event] = query.get_events_at_tick(0)
    tick1_events: List[Event] = query.get_events_at_tick(1)
    tick2_events: List[Event] = query.get_events_at_tick(2)
    tick3_events: List[Event] = query.get_events_at_tick(3)  # Nonexistent tick

    # Verify results
    assert len(tick0_events) == 2
    assert all(e.tick == 0 for e in tick0_events)

    assert len(tick1_events) == 1
    assert tick1_events[0].tick == 1

    assert len(tick2_events) == 3
    assert all(e.tick == 2 for e in tick2_events)

    assert len(tick3_events) == 0


def test_get_root_events() -> None:
    """Test getting root events, optionally filtered by tick."""
    log: EventLog = EventLog()

    # Create events at tick 0
    root1: Event = log.add_event("test.root1", {"value": 1})
    _child1: Event = log.add_event("test.child1", {"value": 2}, parent_event=root1)
    root2: Event = log.add_event("test.root2", {"value": 3})

    # Create events at tick 1
    log.advance_tick()
    root3: Event = log.add_event("test.root3", {"value": 4})
    child2: Event = log.add_event(
        "test.child2", {"value": 5}, parent_event=root1
    )  # Cross-tick child
    _child3: Event = log.add_event("test.child3", {"value": 6}, parent_event=root3)

    query: EventQuery = EventQuery(log)

    # Test getting all root events
    all_roots: List[Event] = query.get_root_events()

    # Test getting root events at specific ticks
    tick0_roots: List[Event] = query.get_root_events(tick=0)
    tick1_roots: List[Event] = query.get_root_events(tick=1)

    # Verify -root events include those with no parent OR with parent in a previous tick
    assert len(all_roots) == 4
    assert root1 in all_roots
    assert root2 in all_roots
    assert root3 in all_roots
    assert any(
        e.id == child2.id for e in all_roots
    )  # child2 is a root in tick 1 because its parent is in tick 0

    assert len(tick0_roots) == 2
    assert root1 in tick0_roots
    assert root2 in tick0_roots

    assert len(tick1_roots) == 2
    assert root3 in tick1_roots
    assert any(e.id == child2.id for e in tick1_roots)  # child2 is a root in tick 1
