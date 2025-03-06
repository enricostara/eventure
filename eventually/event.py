"""
Event handling module for Eventually.

This module provides the core Event and EventBus classes for implementing
a robust event system with type-safe event handling and wildcard subscriptions.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass(frozen=True)
class Event:
    """
    Represents an immutable event in the system.

    An Event is a frozen dataclass that contains:
    - type: The event type (e.g., "user.created", "order.completed")
    - data: The event payload
    - timestamp: UTC timestamp when the event was created
    """

    type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.now(UTC)


class EventBus:
    """
    A central event bus that handles event publishing and subscription.

    Features:
    - Type-safe event handling
    - Support for wildcard subscriptions (e.g., "user.*")
    - Asynchronous event processing (planned)
    """

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}

    def subscribe(
        self, event_type: str, handler: Callable[[Event], None]
    ) -> Callable[[], None]:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: The type of events to subscribe to. Can include wildcards.
            handler: The function to call when an event is received.

        Returns:
            A function that can be called to unsubscribe.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

        def unsubscribe() -> None:
            if event_type in self._subscribers:
                handlers: List[Callable[[Event], None]] = self._subscribers[event_type]
                if handler in handlers:
                    handlers.remove(handler)
                if not handlers:
                    del self._subscribers[event_type]

        return unsubscribe

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish.
        """
        # Create a list of all matching subscribers
        handlers: List[Callable[[Event], None]] = []
        for pattern, subscriber_handlers in self._subscribers.items():
            if self._matches_pattern(event.type, pattern):
                handlers.extend(subscriber_handlers)

        # Notify all matching subscribers
        for handler in handlers:
            handler(event)

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """
        Check if an event type matches a subscription pattern.

        Args:
            event_type: The actual event type.
            pattern: The subscription pattern, which may include wildcards.

        Returns:
            True if the event type matches the pattern.
        """
        if pattern == "*":
            return True

        pattern_parts: List[str] = pattern.split(".")
        event_parts: List[str] = event_type.split(".")

        if len(pattern_parts) != len(event_parts):
            return False

        return all(
            p == "*" or p == e for p, e in zip(pattern_parts, event_parts)
        )
