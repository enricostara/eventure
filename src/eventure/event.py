"""
Event handling module for Eventure.

This module provides the core Event and EventBus classes for implementing
a robust event system with type-safe event handling and wildcard subscriptions.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Event:
    """Represents a single game event that occurred at a specific tick.

    Events are immutable records of state changes in the game. Each event:
    - Is tied to a specific tick number
    - Has a UTC timestamp for real-world time reference
    - Contains a type identifier for different kinds of events
    - Includes arbitrary data specific to the event type

    Args:
        tick: Game tick when the event occurred
        timestamp: UTC timestamp when the event occurred
        type: Event type from the EventType enum
        data: Dictionary containing event-specific data
    """

    tick: int
    timestamp: float  # UTC timestamp
    type: str
    data: Dict[str, Any]

    def to_json(self) -> str:
        """Convert event to JSON string for storage or transmission."""
        return json.dumps(
            {
                "tick": self.tick,
                "timestamp": self.timestamp,
                "type": self.type,
                "data": self.data,
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
        )


class EventLog:
    """Manages the sequence of game events and provides replay capability.

    The EventLog is the core of the game's state management system:
    - Maintains ordered sequence of all events
    - Tracks current tick number
    - Provides methods to add events and advance time
    - Handles saving and loading of event history

    The event log can be saved to disk and loaded later to:
    - Restore a game in progress
    - Review game history
    - Debug game state issues
    - Analyze gameplay patterns
    """

    def __init__(self):
        self.events: List[Event] = []
        self._current_tick: int = 0

    @property
    def current_tick(self) -> int:
        """Current game tick number.

        Ticks are the fundamental unit of game time. Each tick can
        contain zero or more events that modify the game state.
        """
        return self._current_tick

    def advance_tick(self) -> None:
        """Advance to next tick.

        This should be called once per game update cycle. Multiple
        events can occur within a single tick, but they will always
        be processed in the order they were added.
        """
        self._current_tick += 1

    def add_event(self, type: str, data: Dict[str, Any]) -> Event:
        """Add a new event at the current tick.

        Args:
            type: Event type as a string
            data: Dictionary containing event-specific data

        Returns:
            The newly created and added Event

        Note:
            Events are immutable once created. To modify game state,
            create a new event rather than trying to modify existing ones.
        """
        event = Event(
            tick=self.current_tick,
            timestamp=datetime.now(timezone.utc).timestamp(),
            type=type,
            data=data,
        )
        self.events.append(event)
        return event

    def get_events_at_tick(self, tick: int) -> List[Event]:
        """Get all events that occurred at a specific tick.

        This is useful for:
        - Debugging what happened at a specific point in time
        - Processing all state changes for a given tick
        - Analyzing game history
        """
        return [e for e in self.events if e.tick == tick]

    def save_to_file(self, filename: str) -> None:
        """Save event log to file.

        The entire game state can be reconstructed from this file.
        Each event is stored as a separate line of JSON for easy
        parsing and appending.
        """
        with open(filename, "w") as f:
            for event in self.events:
                f.write(event.to_json() + "\n")

    @classmethod
    def load_from_file(cls, filename: str) -> "EventLog":
        """Load event log from file.

        Creates a new EventLog instance and populates it with
        events from the saved file. The current tick is set to
        the highest tick found in the loaded events.
        """
        log = cls()
        with open(filename, "r") as f:
            for line in f:
                if line.strip():
                    event = Event.from_json(line)
                    log.events.append(event)
                    # Update current tick to highest tick found
                    log._current_tick = max(log._current_tick, event.tick)
        return log


class EventBus:
    """Central event bus for publishing events and subscribing to them.

    The EventBus decouples event producers from event consumers, allowing
    components to communicate without direct references to each other.

    Features:
    - Subscribe to specific event types
    - Publish events to all interested subscribers
    - Automatic event creation with current tick and timestamp
    """

    def __init__(self, event_log: Optional[EventLog] = None):
        """Initialize the event bus.

        Args:
            event_log: Optional reference to an EventLog for tick information
        """
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self.event_log = event_log

    def set_event_log(self, event_log: EventLog) -> None:
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
    ) -> Event:
        """Publish an event to all subscribers.

        Args:
            event_type: The type of event to publish as a string
            data: Dictionary containing event-specific data
            tick: Optional tick number (defaults to current tick from event_log)
            timestamp: Optional timestamp (defaults to current time)

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

        # Create the event
        event = Event(tick=tick, timestamp=timestamp, type=event_type, data=data)

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
