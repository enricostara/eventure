"""
Event bus module for Eventure.

This module provides the EventBus class for publishing events and subscribing to them.
"""

from typing import Any, Callable, Dict, List, Optional

from eventure.event import Event
from eventure.event_log import EventLog


class EventBus:
    """Central event bus for publishing events and subscribing to them.

    The EventBus decouples event producers from event consumers, allowing
    components to communicate without direct references to each other.

    Features:
    - Subscribe to specific event types
    - Publish events to all interested subscribers
    - Automatic event creation with current tick and timestamp
    - Support for event cascade tracking through parent-child relationships
    """

    def __init__(self, event_log: EventLog):
        """Initialize the event bus.

        Args:
            event_log: Reference to an EventLog for event creation and tick information
        """
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self.event_log = event_log

    def subscribe(
        self, event_type: str, handler: Callable[[Event], None]
    ) -> Callable[[], None]:
        """Subscribe a handler to a specific event type.

        Args:
            event_type: The type of event to subscribe to as a string
            handler: Function to call when an event of this type is published

        Returns:
            A function that can be called to unsubscribe the handler
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

        # Return an unsubscribe function
        def unsubscribe():
            if event_type in self.subscribers and handler in self.subscribers[event_type]:
                self.subscribers[event_type].remove(handler)

        return unsubscribe

    def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        parent_event: Optional[Event] = None,
    ) -> Event:
        """Publish an event to all subscribers.

        Args:
            event_type: The type of event to publish as a string
            data: Dictionary containing event-specific data
            parent_event: Optional parent event that caused this event (for cascade tracking)

        Returns:
            The created event

        Note:
            This method adds the event to the event log.
            It also dispatches the event to all subscribers.
        """
        # Use the event_log to create and add the event
        if self.event_log is None:
            raise ValueError("EventBus requires an EventLog to publish events")

        # Create and add the event using event_log
        event = self.event_log.add_event(event_type, data, parent_event)

        # Dispatch to subscribers
        self.dispatch(event)

        return event

    def dispatch(self, event: Event) -> None:
        """Dispatch the event to all interested subscribers.

        Args:
            event: The event to dispatch

        Note:
            This method supports two types of wildcard subscriptions:
            1. Global wildcard "*" which will receive all events regardless of type
            2. Prefix wildcard "prefix.*" which will receive all events with the given prefix

            The event is dispatched to handlers in this order:
            1. Exact type match subscribers
            2. Prefix wildcard subscribers
            3. Global wildcard subscribers
        """
        # Notify specific event type subscribers
        if event.type in self.subscribers:
            for handler in self.subscribers[event.type]:
                handler(event)

        # Notify prefix wildcard subscribers (e.g., "user.*")
        for pattern, handlers in self.subscribers.items():
            if pattern.endswith(".*") and event.type.startswith(pattern[:-1]):
                for handler in handlers:
                    handler(event)

        # Notify global wildcard subscribers
        if "*" in self.subscribers:
            for handler in self.subscribers["*"]:
                handler(event)
