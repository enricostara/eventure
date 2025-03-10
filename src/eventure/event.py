"""
Event handling module for Eventure.

This module provides the core Event and EventBus classes for implementing
a robust event system with type-safe event handling and wildcard subscriptions.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional

if TYPE_CHECKING:
    from eventure.event_log import EventLog


@dataclass
class Event:
    """Represents a single game event that occurred at a specific tick.

    Events are immutable records of state changes in the game. Each event:
    - Is tied to a specific tick number
    - Has a UTC timestamp for real-world time reference
    - Contains a type identifier for different kinds of events
    - Includes arbitrary data specific to the event type
    - Has a unique event_id in the format tick-typeHash-sequence
    - May reference a parent event that caused this event (for cascade tracking)

    Args:
        tick: Game tick when the event occurred
        timestamp: UTC timestamp when the event occurred
        type: Event type from the EventType enum
        data: Dictionary containing event-specific data
        id: Optional explicit event ID (generated if not provided)
        parent_id: Optional ID of the parent event that caused this one
    """

    # Class variable to track event sequence numbers
    _event_sequences: ClassVar[Dict[int, Dict[str, int]]] = {}

    tick: int
    timestamp: float  # UTC timestamp
    type: str
    data: Dict[str, Any]
    id: str = None  # Will be set in __post_init__
    parent_id: Optional[str] = None  # Reference to parent event that caused this one

    def __post_init__(self):
        # Generate event_id if not provided
        if self.id is None:
            self.id = self._generate_event_id()

    @staticmethod
    def _generate_type_hash(event_type: str) -> str:
        """
        Generate a 4-character alpha hash from an event type.

        Args:
            event_type: The event type to hash

        Returns:
            A 4-character alpha hash
        """
        # Generate md5 hash
        md5_hash = hashlib.md5(event_type.encode()).hexdigest()

        # Extract only alpha characters
        alpha_chars = re.sub(r"[^a-zA-Z]", "", md5_hash)

        # Return first 4 alpha characters (uppercase for better readability)
        return alpha_chars[:4].upper()

    @classmethod
    def _get_next_sequence(cls, tick: int, type_hash: str) -> int:
        """
        Get the next sequence number for a given tick and event type hash.

        Args:
            tick: The current tick
            type_hash: The hashed event type

        Returns:
            The next sequence number
        """
        # Initialize tick counter if not exists
        if tick not in cls._event_sequences:
            cls._event_sequences[tick] = {}

        # Initialize type counter if not exists
        if type_hash not in cls._event_sequences[tick]:
            cls._event_sequences[tick][type_hash] = 0

        # Increment and return
        cls._event_sequences[tick][type_hash] += 1
        return cls._event_sequences[tick][type_hash]

    def _generate_event_id(self) -> str:
        """
        Generate a structured event ID using tick + type hash + sequence.

        Returns:
            A structured event ID
        """
        type_hash = self._generate_type_hash(self.type)
        sequence = self._get_next_sequence(self.tick, type_hash)
        return f"{self.tick}-{type_hash}-{sequence}"

    def to_json(self) -> str:
        """Convert event to JSON string for storage or transmission."""
        return json.dumps(
            {
                "tick": self.tick,
                "timestamp": self.timestamp,
                "type": self.type,
                "data": self.data,
                "event_id": self.id,
                "parent_id": self.parent_id,
            }
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create event from JSON string for loading or receiving."""
        data = json.loads(json_str)
        return cls(
            tick=data["tick"],
            timestamp=data["timestamp"],
            type=data["type"],
            data=data["data"],
            id=data.get("event_id"),
            parent_id=data.get("parent_id"),
        )


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

    def __init__(self, event_log: Optional["EventLog"] = None):
        """Initialize the event bus.

        Args:
            event_log: Optional reference to an EventLog for tick information
        """
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self.event_log = event_log

    def set_event_log(self, event_log: "EventLog") -> None:
        """Set the reference to the event log for tick information.

        Args:
            event_log: The event log to use for tick information
        """
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
        tick: Optional[int] = None,
        timestamp: Optional[float] = None,
        parent_event: Optional[Event] = None,
    ) -> Event:
        """Publish an event to all subscribers.

        Args:
            event_type: The type of event to publish as a string
            data: Dictionary containing event-specific data
            tick: Optional tick number (defaults to current tick from event_log)
            timestamp: Optional timestamp (defaults to current time)
            parent_event: Optional parent event that caused this event (for cascade tracking)

        Returns:
            The created event

        Note:
            This method does NOT add the event to the event log.
            It only creates the event and dispatches it to subscribers.
        """
        # Get current tick from event_log if available
        if tick is None and self.event_log:
            tick = self.event_log.current_tick
        elif tick is None:
            tick = 0

        # Use current time if timestamp not provided
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).timestamp()

        # Create the event with optional parent reference
        parent_id = parent_event.id if parent_event else None
        event = Event(
            tick=tick, timestamp=timestamp, type=event_type, data=data, parent_id=parent_id
        )

        # Dispatch to subscribers
        self._dispatch(event)

        return event

    def _dispatch(self, event: Event) -> None:
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
