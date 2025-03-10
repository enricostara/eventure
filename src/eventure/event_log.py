"""
Event logging module for Eventure.

This module provides the EventLog class for managing and storing events in the game.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from eventure.event import Event


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

    def create_query(self):
        """Create an EventQuery instance for this event log.

        Returns:
            An EventQuery instance that can be used to visualize and analyze this event log.
        """
        # Import here to avoid circular imports
        from eventure.event_query import EventQuery

        return EventQuery(self)

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
