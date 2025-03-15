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

    # Verify the event was added to the log
    assert len(log.events) == 1
    assert log.events[0].type == "user.created"
    assert log.events[0].data["user_id"] == 1

    # Test unsubscribing
    unsubscribe()
    bus.publish("user.created", {"user_id": 2})
    assert len(received_events) == 1  # Should not receive the second event
    assert len(log.events) == 2  # But the event should still be in the log


def test_eventbus_without_eventlog() -> None:
    """Test EventBus with an EventLog."""
    log: EventLog = EventLog()  # Create an EventLog
    bus: EventBus = EventBus(log)  # Provide the EventLog
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    bus.subscribe("user.created", handler)

    # Publish an event
    event: Event = bus.publish("user.created", {"user_id": 1})

    # Verify the event was created with the current tick (0)
    assert event.tick == 0
    assert len(received_events) == 1
    assert len(log.events) == 1  # Event should be in the log


def test_eventbus_multiple_subscribers() -> None:
    """Test multiple subscribers for the same event type."""
    log: EventLog = EventLog()
    bus: EventBus = EventBus(log)
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
    assert len(log.events) == 1


def test_eventbus_wildcard_subscription() -> None:
    """Test wildcard event subscription."""
    log: EventLog = EventLog()
    bus: EventBus = EventBus(log)
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
    assert len(log.events) == 2


def test_eventbus_global_subscription() -> None:
    """Test subscribing to all events with wildcard."""
    log: EventLog = EventLog()
    bus: EventBus = EventBus(log)
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to ALL events with global wildcard
    bus.subscribe("*", handler)

    # All of these should be received
    event1: Event = bus.publish("user.created", {"user_id": 1})
    event2: Event = bus.publish("item.added", {"item_id": 100})
    event3: Event = bus.publish("game.started", {"level": 1})

    assert len(received_events) == 3
    assert received_events[0] == event1
    assert received_events[1] == event2
    assert received_events[2] == event3
    assert len(log.events) == 3


def test_eventbus_publish_with_parent() -> None:
    """Test publishing an event with a parent event reference via EventBus."""
    log: EventLog = EventLog()
    bus: EventBus = EventBus(log)
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
    assert len(log.events) == 2  # Both events should be in the log

    # Verify both events were received by handler
    assert len(received_events) == 2
    assert received_events[0].id == parent_event.id
    assert received_events[1].id == child_event.id
    assert received_events[1].parent_id == parent_event.id


def test_eventbus_suffix_wildcard_subscription() -> None:
    """Test suffix wildcard event subscription."""
    log: EventLog = EventLog()
    bus: EventBus = EventBus(log)
    received_events: List[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to all error events with suffix wildcard
    bus.subscribe("*.error", handler)

    # These should be received (*.error)
    event1: Event = bus.publish("user.error", {"message": "User not found"})
    event2: Event = bus.publish("network.error", {"message": "Connection failed"})

    # This should not be received (not an error event)
    bus.publish("user.login", {"user_id": 123})

    assert len(received_events) == 2
    assert received_events[0] == event1
    assert received_events[1] == event2
    assert len(log.events) == 3  # All events should be in the log
