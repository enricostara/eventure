"""Tests for the event_bus module."""

from typing import Callable, List

from eventure import Event, EventBus, EventLog


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
