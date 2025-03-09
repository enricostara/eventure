# Eventure

A Python library providing a robust, type-safe event system for game development and simulation. Eventure offers event tracking, time-based event management, a powerful event bus with wildcard subscription support, unique event IDs, and cascade event tracking.

## Features

- **Event Class**: Immutable events with tick, timestamp, type, data, and unique ID attributes
- **EventLog**: Track, save, and replay sequences of events
- **EventBus**: Decouple event producers from consumers
- **Wildcard Subscriptions**: Subscribe to event patterns like `user.*` or global `*`
- **JSON Serialization**: Save and load events for persistence or network transmission
- **Type Safety**: Strong typing throughout the API
- **Zero Dependencies**: Pure Python implementation
- **Unique Event IDs**: Structured IDs in the format `{tick}-{typeHash}-{sequence}`
- **Cascade Event Tracking**: Track parent-child relationships between events

## Installation

```bash
# Using pip
pip install eventure

# Using uv
uv add eventure
```

### Quick Start

```python
from eventure import EventBus, EventLog, Event

# Create an event log to track game state
event_log = EventLog()

# Create an event bus connected to the log
event_bus = EventBus(event_log)

# Subscribe to specific events
def handle_user_created(event):
    print(f"User created at tick {event.tick}: {event.data}")
    print(f"Event ID: {event.id}")  # Each event has a unique ID

unsubscribe = event_bus.subscribe("user.created", handle_user_created)

# Subscribe to all user events with wildcard
event_bus.subscribe("user.*", lambda event: print(f"User event: {event.type}"))

# Publish an event (automatically uses current tick from event_log)
event = event_bus.publish("user.created", {"id": 1, "name": "John"})

# Advance the game tick
event_log.advance_tick()

# Publish a child event that references the parent event
child_event = event_bus.publish(
    "user.updated", 
    {"id": 1, "name": "John Doe"}, 
    parent_event=event
)

# Events can be serialized to JSON
json_str = event.to_json()
print(json_str)

# And deserialized back
reconstructed_event = Event.from_json(json_str)

# Get all events in a cascade starting from a root event
cascade = event_log.get_event_cascade(event.id)
for cascade_event in cascade:
    print(f"Cascade event: {cascade_event.type} (ID: {cascade_event.id})")

# Save event history to file
event_log.save_to_file("game_events.json")

# Later, load event history
new_log = EventLog.load_from_file("game_events.json")

# Unsubscribe when done
unsubscribe()
```

## Event System Architecture

### Event

The `Event` class represents an immutable record of something that happened in your application:

```python
@dataclass
class Event:
    tick: int               # Game tick when event occurred
    timestamp: float        # UTC timestamp
    type: str               # Event type identifier
    data: Dict[str, Any]    # Event-specific data
    id: str = None          # Unique event ID (auto-generated if None)
    parent_id: str = None   # Optional reference to parent event ID
```

#### Event IDs

Each event has a unique ID in the format `{tick}-{typeHash}-{sequence}` where:
- `tick` is the game tick when the event occurred
- `typeHash` is a 4-character alpha hash of the event type
- `sequence` is a counter that increments for each event of the same type within the same tick

This structured ID format makes events easily identifiable and traceable.

### EventLog

The `EventLog` manages sequences of events and provides replay capability:

- Tracks current tick number
- Records events with timestamps
- Provides persistence through save/load methods
- Retrieves events by their unique ID
- Tracks cascades of related events through parent-child relationships

### EventBus

The `EventBus` handles event publishing and subscription:

- Supports specific event type subscriptions
- Supports wildcard subscriptions (`user.*`)
- Supports global subscriptions (`*`)
- Automatically assigns current tick from EventLog
- Supports creating events with parent references for cascade tracking

## Development

```bash
# Clone the repository
git clone https://github.com/enricostara/eventure.git
cd eventure

# Install development dependencies
uv sync --all-extras

# Run tests
just test
```

## Cascade Event Tracking

Eventure supports tracking cascades of related events through parent-child relationships:

```python
# Create a root event
root_event = event_log.add_event("user.created", {"id": 1})

# Create a child event that references the parent
child_event = event_log.add_event(
    "user.verified", 
    {"id": 1, "verified": True}, 
    parent_event=root_event
)

# Get all events in the cascade
cascade = event_log.get_event_cascade(root_event.id)

# This returns both the root event and all its descendants
# in a properly ordered list (by tick, type, and sequence)
```

This feature is useful for:
- Tracing the cause-and-effect relationships between events
- Debugging complex event chains
- Analyzing event propagation through your system
- Building audit trails of related actions

## License

MIT License - see LICENSE file for details