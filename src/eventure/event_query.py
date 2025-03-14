"""
Event query and visualization module for Eventure.

This module provides tools for querying and visualizing event logs,
including event cascade relationships and parent-child event tracking.
"""

import sys
from typing import Any, Dict, List, Optional, Set, TextIO, Tuple

from .event import Event
from .event_bus import EventLog


class EventQuery:
    """Provides query and visualization capabilities for event logs.

    This class offers methods to analyze and display event relationships,
    helping with debugging and understanding complex event cascades.
    """

    def __init__(self, event_log: EventLog):
        """Initialize with an event log to query.

        Args:
            event_log: The event log to query and visualize
        """
        self.event_log = event_log

    def print_event_cascade(self, file: TextIO = sys.stdout, show_data: bool = True) -> None:
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
        for event in self.event_log.events:
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
                parent = self.event_log.get_event_by_id(event.parent_id)
                if parent and parent.tick == event.tick:
                    # This is a child of an event in the same tick
                    child_events.add(event.id)

        # Second pass: collect root events (not in child_events)
        for event in tick_events:
            if event.id not in child_events:
                root_events.append(event)

        # Sort root events by timestamp for chronological order
        root_events.sort(key=lambda e: e.timestamp)

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
        for event in root_events:
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
            parent = self.event_log.get_event_by_id(event.parent_id)
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
        print(f"{indent}│" if event_prefix == "└─" else "│", file=file)
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

        # Sort children by timestamp for chronological order
        children.sort(key=lambda e: e.timestamp)
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
            e for e in self.event_log.events if e.parent_id == event.id and e.tick > event.tick
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

    # Public API methods for event querying

    def get_events_by_type(self, event_type: str) -> List[Event]:
        """Get all events matching a specific type.

        Args:
            event_type: Event type to filter by

        Returns:
            List of matching events
        """
        return [e for e in self.event_log.events if e.type == event_type]

    def get_events_by_data(self, key: str, value: Any) -> List[Event]:
        """Get all events with matching data key-value pair.

        Args:
            key: Key in event data to match
            value: Value to match against

        Returns:
            List of matching events
        """
        return [e for e in self.event_log.events if key in e.data and e.data[key] == value]

    def get_child_events(self, parent_event: Event) -> List[Event]:
        """Get all events that are direct children of the given event.

        Args:
            parent_event: Parent event to find children for

        Returns:
            List of child events
        """
        return [e for e in self.event_log.events if e.parent_id == parent_event.id]

    def get_cascade_events(self, root_event: Event) -> List[Event]:
        """Get all events in the cascade starting from the given root event.
        This includes the root event, its children, their children, etc.

        Args:
            root_event: Root event to find cascade for

        Returns:
            List of events in the cascade (including the root)
        """
        # Start with the root event
        cascade = [root_event]
        processed_ids = {root_event.id}

        # Process each event in the cascade
        i = 0
        while i < len(cascade):
            # Get children of the current event
            current = cascade[i]
            children = self.get_child_events(current)

            # Add unprocessed children to the cascade
            for child in children:
                if child.id not in processed_ids:
                    cascade.append(child)
                    processed_ids.add(child.id)

            i += 1

        return cascade

    def print_event_details(
        self, event: Event, file: TextIO = sys.stdout, show_data: bool = True
    ) -> None:
        """Print details of a single event.

        Args:
            event: Event to print details for
            file: File-like object to print to
            show_data: Whether to show event data
        """
        # Get display info
        event_prefix, cross_tick_info = self._get_event_display_info(event)

        # Print event header
        print(f"● {event.type}{cross_tick_info}", file=file)
        print(f"  ID: {event.id}", file=file)

        # Print data if requested
        if show_data and event.data:
            print("  Data:", file=file)
            for key, value in event.data.items():
                print(f"    {key}: {value}", file=file)

    def print_single_cascade(
        self, root_event: Event, file: TextIO = sys.stdout, show_data: bool = True
    ) -> None:
        """Print a single event cascade starting from the root event.

        Args:
            root_event: Root event to start cascade from
            file: File-like object to print to
            show_data: Whether to show event data
        """
        # Get all events for the tick containing the root event
        tick_events = [e for e in self.event_log.events if e.tick == root_event.tick]

        # Identify child events
        _, child_events = self._identify_root_and_child_events(tick_events)

        # Print the cascade
        self._print_root_events([root_event], tick_events, set(child_events), file, show_data)

    def count_events_by_type(self) -> Dict[str, int]:
        """Count events by type.

        Returns:
            Dictionary mapping event types to counts
        """
        counts = {}
        for event in self.event_log.events:
            counts[event.type] = counts.get(event.type, 0) + 1
        return counts

    def get_events_at_tick(self, tick: int) -> List[Event]:
        """Get all events that occurred at a specific tick.

        Args:
            tick: Tick number to filter by

        Returns:
            List of events at the specified tick
        """
        return [e for e in self.event_log.events if e.tick == tick]

    def get_root_events(self, tick: Optional[int] = None) -> List[Event]:
        """Get all root events, optionally filtered by tick.

        Root events are those with no parent or whose parent is in a previous tick.

        Args:
            tick: Optional tick to filter by

        Returns:
            List of root events
        """
        # Get events for the specified tick, or all events if tick is None
        events_to_check = (
            self.get_events_at_tick(tick) if tick is not None else self.event_log.events
        )

        # Group events by tick for efficient processing
        events_by_tick = {}
        for event in events_to_check:
            if event.tick not in events_by_tick:
                events_by_tick[event.tick] = []
            events_by_tick[event.tick].append(event)

        # Find root events for each tick
        root_events = []
        for _tick_num, tick_events in events_by_tick.items():
            tick_roots, _ = self._identify_root_and_child_events(tick_events)
            root_events.extend(tick_roots)

        return root_events
