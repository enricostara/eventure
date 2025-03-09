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
from typing import Any, Callable, ClassVar, Dict, List, Optional, Set, Tuple


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
        events_by_tick = self._group_events_by_tick()

        # Print header
        print("===== EVENT CASCADE VIEWER =====", file=file)

        if not events_by_tick:
            print("\n<No events in log>", file=file)
            return

        # Process each tick
        for tick in sorted(events_by_tick.keys()):
            self._print_tick_events(tick, events_by_tick[tick], file, show_data)

    def _group_events_by_tick(self) -> Dict[int, List[Event]]:
        """Group all events by their tick number.

        Returns:
            Dictionary mapping tick numbers to lists of events
        """
        events_by_tick: Dict[int, List[Event]] = {}
        for event in self.events:
            if event.tick not in events_by_tick:
                events_by_tick[event.tick] = []
            events_by_tick[event.tick].append(event)
        return events_by_tick

    def _print_tick_events(
        self, tick: int, tick_events: List[Event], file=sys.stdout, show_data: bool = True
    ) -> None:
        """Print all events for a specific tick.

        Args:
            tick: The tick number
            tick_events: List of events in this tick
            file: File-like object to print to
            show_data: Whether to show event data
        """
        # Print tick header
        print(f"\n┌─── TICK {tick} ───┐", file=file)

        # Get root events and child events for this tick
        root_events, child_events = self._identify_root_and_child_events(tick_events)

        # No events in this tick
        if not root_events:
            print("  <No events>", file=file)
            print("└" + "─" * (14 + len(str(tick))) + "┘", file=file)
            return

        # Print each root event tree
        self._print_root_events(root_events, tick_events, child_events, file, show_data)

        # Print tick footer
        print("└" + "─" * (14 + len(str(tick))) + "┘", file=file)

    def _identify_root_and_child_events(
        self, tick_events: List[Event]
    ) -> Tuple[List[Event], Set[str]]:
        """Identify root events and child events within a tick.

        Root events are either:
        1. Events with no parent
        2. Events whose parent is in a previous tick

        Args:
            tick_events: List of events in the current tick

        Returns:
            Tuple of (sorted_root_events, child_event_ids)
        """
        root_events: List[Event] = []
        child_events: Set[str] = set()

        # First pass: identify child events
        for event in tick_events:
            if event.parent_id:
                parent = self.get_event_by_id(event.parent_id)
                if parent and parent.tick == event.tick:
                    # This is a child of an event in the same tick
                    child_events.add(event.id)

        # Second pass: collect root events (not in child_events)
        for event in tick_events:
            if event.id not in child_events:
                root_events.append(event)

        # Sort root events by type and sequence for consistent output
        root_events.sort(key=lambda e: (e.type, int(e.id.split("-")[2])))

        return root_events, child_events

    def _print_root_events(
        self,
        root_events: List[Event],
        tick_events: List[Event],
        child_events: Set[str],
        file=sys.stdout,
        show_data: bool = True,
    ) -> None:
        """Print each root event and its children.

        Args:
            root_events: List of root events to print
            tick_events: All events for the current tick
            child_events: Set of event IDs that are children of other events
            file: File-like object to print to
            show_data: Whether to show event data
        """
        for i, event in enumerate(root_events):
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

        # Get event display info
        event_prefix, cross_tick_info = self._get_event_display_info(event)

        # Print event header and ID
        self._print_event_header(event, indent, event_prefix, cross_tick_info, file)

        # Print event data if requested
        if show_data:
            self._print_event_data(event, indent, event_prefix, file)

        # Find and print children in current tick
        children = self._get_sorted_children(event, tick_events, known_children)

        # Print future event triggers if any
        self._print_future_triggers(event, indent, event_prefix, file)

        # Recursively print children
        for child in children:
            self._print_event_in_cascade(
                child,
                tick_events,
                known_children,
                indent_level + 1,
                file=file,
                show_data=show_data,
            )

    def _get_event_display_info(self, event: Event) -> Tuple[str, str]:
        """Determine event symbol and cross-tick info based on event's parent relationship.

        Args:
            event: The event to get display info for

        Returns:
            Tuple of (event_prefix, cross_tick_info)
        """
        if event.parent_id:
            parent = self.get_event_by_id(event.parent_id)
            if parent and parent.tick < event.tick:
                # This is triggered by an event from a previous tick
                return "↓", f" (caused by: {parent.type} @ tick {parent.tick})"
            else:
                # This is a child event in the current tick
                return "└─", ""
        else:
            # This is a root event with no parent
            return "●", ""

    def _print_event_header(
        self,
        event: Event,
        indent: str,
        event_prefix: str,
        cross_tick_info: str,
        file=sys.stdout,
    ) -> None:
        """Print the event header line with type and ID.

        Args:
            event: The event to print
            indent: Current indentation string
            event_prefix: Symbol to use before event type
            cross_tick_info: Additional info about cross-tick relationships
            file: File-like object to print to
        """
        # Print current event header
        print(f"{indent}{event_prefix} {event.type}{cross_tick_info}", file=file)

        # Print ID in a more compact way
        print(f"{indent}{'│ ' if event_prefix == '└─' else '  '}ID: {event.id}", file=file)

    def _print_event_data(
        self, event: Event, indent: str, event_prefix: str, file=sys.stdout
    ) -> None:
        """Print the event data if available.

        Args:
            event: The event to print data for
            indent: Current indentation string
            event_prefix: Symbol used before event type (for continuation lines)
            file: File-like object to print to
        """
        if not event.data:
            return

        data_indent = f"{indent}{'│ ' if event_prefix == '└─' else '  '}"

        if isinstance(event.data, dict) and len(event.data) > 0:
            print(f"{data_indent}Data:", file=file)
            for k, v in event.data.items():
                print(f"{data_indent}  {k}: {v}", file=file)
        else:
            print(f"{data_indent}Data: {event.data}", file=file)

    def _get_sorted_children(
        self, event: Event, tick_events: List[Event], known_children: Set[str]
    ) -> List[Event]:
        """Find and sort direct children within the same tick.

        Args:
            event: The parent event
            tick_events: All events for the current tick
            known_children: Set of event IDs that are children of other events

        Returns:
            Sorted list of child events
        """
        children = [
            e for e in tick_events if e.parent_id == event.id and e.id in known_children
        ]

        # Sort children by type and sequence
        children.sort(key=lambda e: (e.type, int(e.id.split("-")[2])))
        return children

    def _print_future_triggers(
        self, event: Event, indent: str, event_prefix: str, file=sys.stdout
    ) -> None:
        """Print information about future events triggered by this event.

        Args:
            event: The event to check for future triggers
            indent: Current indentation string
            event_prefix: Symbol used before event type (for continuation lines)
            file: File-like object to print to
        """
        # Find events in future ticks that are triggered by this event
        future_children = [
            e for e in self.events if e.parent_id == event.id and e.tick > event.tick
        ]

        if not future_children:
            return

        # Group future children by tick
        future_by_tick: Dict[int, List[Event]] = {}
        for child in future_children:
            if child.tick not in future_by_tick:
                future_by_tick[child.tick] = []
            future_by_tick[child.tick].append(child)

        # Format the trigger information
        triggers_indent = f"{indent}{'│ ' if event_prefix == '└─' else '  '}"
        tick_strs: List[str] = []

        for child_tick in sorted(future_by_tick.keys()):
            tick_children = future_by_tick[child_tick]
            event_count = len(tick_children)
            tick_strs.append(f"tick {child_tick} ({event_count})")

        # Print the trigger information
        if tick_strs:
            if len(tick_strs) == 1:
                print(f"{triggers_indent}↓ Triggers events in {tick_strs[0]}", file=file)
            else:
                print(
                    f"{triggers_indent}↓ Triggers events in: {', '.join(tick_strs)}",
                    file=file,
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
