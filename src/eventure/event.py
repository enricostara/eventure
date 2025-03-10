"""
Event handling module for Eventure.

This module provides the core Event and EventBus classes for implementing
a robust event system with type-safe event handling and wildcard subscriptions.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Optional


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
