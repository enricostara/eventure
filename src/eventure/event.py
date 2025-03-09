"""
Event handling module for Eventure.

This module provides the core Event and EventBus classes for implementing
a robust event system with type-safe event handling and wildcard subscriptions.
"""

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, ClassVar, Dict, List, Optional, Set


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


class EventLog:
    """Manages the sequence of game events and provides replay capability.

    The EventLog is the core of the game's state management system:
    - Maintains ordered sequence of all events
    - Tracks current tick number
    - Provides methods to add events and advance time
    - Handles saving and loading of event history
    - Supports tracking cascades of related events

    The event log can be saved to disk and loaded later to:
    - Restore a game in progress
    - Review game history
    - Debug game state issues
    - Analyze gameplay patterns
    - Trace causality chains between events
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

    def add_event(
        self, type: str, data: Dict[str, Any], parent_event: Optional[Event] = None
    ) -> Event:
        """Add a new event at the current tick.

        Args:
            type: Event type as a string
            data: Dictionary containing event-specific data
            parent_event: Optional parent event that caused this event (for cascade tracking)

        Returns:
            The newly created and added Event

        Note:
            Events are immutable once created. To modify game state,
            create a new event rather than trying to modify existing ones.
        """
        parent_id = parent_event.id if parent_event else None
        event = Event(
            tick=self.current_tick,
            timestamp=datetime.now(timezone.utc).timestamp(),
            type=type,
            data=data,
            parent_id=parent_id,
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

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Get an event by its unique ID.

        Args:
            event_id: The unique ID of the event to find

        Returns:
            The event with the given ID, or None if not found
        """
        for event in self.events:
            if event.id == event_id:
                return event
        return None

    def get_event_cascade(self, event_id: str) -> List[Event]:
        """Get the cascade of events starting from the specified event ID.

        This returns the event with the given ID and all events that have it
        as an ancestor in their parent chain.

        Args:
            event_id: The ID of the root event in the cascade

        Returns:
            A list of events in the cascade, ordered by tick and sequence
        """
        # Find the root event
        root_event = self.get_event_by_id(event_id)
        if not root_event:
            return []

        # Start with the root event
        cascade = [root_event]

        # Build a map of parent_id to events for faster lookup
        parent_map: Dict[str, List[Event]] = {}
        for event in self.events:
            if event.parent_id:
                if event.parent_id not in parent_map:
                    parent_map[event.parent_id] = []
                parent_map[event.parent_id].append(event)

        # Recursively find all child events
        def add_children(parent_id: str) -> None:
            if parent_id in parent_map:
                for child in parent_map[parent_id]:
                    cascade.append(child)
                    add_children(child.id)

        add_children(event_id)

        # Sort by tick, type hash, and then sequence
        # This ensures correct ordering since sequence is calculated per tick+type combination
        return sorted(
            cascade, key=lambda e: (e.tick, e.id.split("-")[1], int(e.id.split("-")[2]))
        )

    def print_event_cascade(self, file=sys.stdout, show_data=True) -> None:
        """Print events organized by tick with clear cascade relationships.
        Optimized for showing parent-child relationships within the same tick.

        This method provides a visual representation of the event log, showing
        how events relate to each other across ticks and within the same tick.
        It's especially useful for debugging complex event sequences and understanding
        cause-effect relationships between events.

        Args:
            file: File-like object to print to (defaults to stdout).
            show_data: Whether to show event data (defaults to True).
        """
        # Group events by tick
        events_by_tick: Dict[int, List[Event]] = {}
        for event in self.events:
            if event.tick not in events_by_tick:
                events_by_tick[event.tick] = []
            events_by_tick[event.tick].append(event)

        print("===== EVENT CASCADE VIEWER =====", file=file)

        if not events_by_tick:
            print("\n<No events in log>", file=file)
            return

        for tick in sorted(events_by_tick.keys()):
            print(f"\n┌─── TICK {tick} ───┐", file=file)

            # Get events for this tick
            tick_events: List[Event] = events_by_tick[tick]

            # Find root events for this tick
            # These are either:
            # 1. Events with no parent
            # 2. Events whose parent is in a previous tick
            root_events_for_tick: List[Event] = []
            child_events: Set[str] = set()

            for event in tick_events:
                if event.parent_id:
                    parent = self.get_event_by_id(event.parent_id)
                    if parent and parent.tick == tick:
                        # This is a child of an event in the same tick
                        child_events.add(event.id)
                        continue
                # This is a root event for this tick
                root_events_for_tick.append(event)

            # Sort root events by type and sequence for consistent output
            root_events_for_tick.sort(key=lambda e: (e.type, int(e.id.split("-")[2])))

            # No events in this tick
            if not root_events_for_tick:
                print("  <No events>", file=file)
                print("└" + "─" * (14 + len(str(tick))) + "┘", file=file)
                continue

            # Print each root event tree for this tick
            for i, event in enumerate(root_events_for_tick):
                # Print a separator between root events in the same tick
                if i > 0:
                    print("│", file=file)

                # Print this root event and its children as a tree
                self._print_event_in_cascade(
                    event,
                    tick_events,
                    child_events,
                    indent_level=1,
                    file=file,
                    show_data=show_data,
                )

            print("└" + "─" * (14 + len(str(tick))) + "┘", file=file)

    def _print_event_in_cascade(
        self,
        event: Event,
        tick_events: List[Event],
        known_children: Set[str],
        indent_level: int = 1,
        file=sys.stdout,
        show_data: bool = True,
    ) -> None:
        """Helper method to recursively print an event and its children within a cascade.

        Args:
            event: The event to print.
            tick_events: All events for the current tick.
            known_children: Set of event IDs that are children of other events in this tick.
            indent_level: Current indentation level.
            file: File-like object to print to.
            show_data: Whether to show event data.
        """
        indent: str = "  " * indent_level

        # Determine event symbol and cross-tick info
        if event.parent_id:
            parent = self.get_event_by_id(event.parent_id)
            if parent and parent.tick < event.tick:
                # This is triggered by an event from a previous tick
                event_prefix = "↓"  # Downward arrow indicating triggered from previous tick
                cross_tick_info = f" (caused by: {parent.type} @ tick {parent.tick})"
            else:
                # This is a child event in the current tick
                event_prefix = "└─"
                cross_tick_info = ""
        else:
            # This is a root event with no parent
            event_prefix = "●"
            cross_tick_info = ""

        # Print current event header
        print(f"{indent}{event_prefix} {event.type}{cross_tick_info}", file=file)

        # Print ID in a more compact way
        print(f"{indent}{'│ ' if event_prefix == '└─' else '  '}ID: {event.id}", file=file)

        # Print data if requested
        if show_data and event.data:
            data_indent = f"{indent}{'│ ' if event_prefix == '└─' else '  '}"

            if isinstance(event.data, dict) and len(event.data) > 0:
                print(f"{data_indent}Data:", file=file)
                for k, v in event.data.items():
                    print(f"{data_indent}  {k}: {v}", file=file)
            else:
                print(f"{data_indent}Data: {event.data}", file=file)

        # Find and print direct children within the same tick
        children = [
            e for e in tick_events if e.parent_id == event.id and e.id in known_children
        ]

        # Sort children by type and sequence
        children.sort(key=lambda e: (e.type, int(e.id.split("-")[2])))

        # If this event triggers future events, note it before printing children
        future_children = [
            e for e in self.events if e.parent_id == event.id and e.tick > event.tick
        ]

        if future_children:
            future_by_tick: Dict[int, List[Event]] = {}
            for child in future_children:
                if child.tick not in future_by_tick:
                    future_by_tick[child.tick] = []
                future_by_tick[child.tick].append(child)

            triggers_indent = f"{indent}{'│ ' if event_prefix == '└─' else '  '}"
            tick_strs: List[str] = []

            for child_tick in sorted(future_by_tick.keys()):
                tick_children = future_by_tick[child_tick]
                event_count = len(tick_children)
                tick_strs.append(f"tick {child_tick} ({event_count})")

            if tick_strs:
                if len(tick_strs) == 1:
                    print(f"{triggers_indent}↓ Triggers events in {tick_strs[0]}", file=file)
                else:
                    print(
                        f"{triggers_indent}↓ Triggers events in: {', '.join(tick_strs)}",
                        file=file,
                    )

        # If there are children in this tick, print them
        if children:
            for child in children:
                self._print_event_in_cascade(
                    child,
                    tick_events,
                    known_children,
                    indent_level + 1,
                    file=file,
                    show_data=show_data,
                )

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
    - Support for event cascade tracking through parent-child relationships
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
