# Eventick

A Python library providing a robust, type-safe event system for game development and simulation. Eventick offers event tracking, time-based event management, and a powerful event bus with wildcard subscription support.

## Features

- **Event Class**: Immutable events with tick, timestamp, type, and data attributes
- **EventLog**: Track, save, and replay sequences of events
- **EventBus**: Decouple event producers from consumers
- **Wildcard Subscriptions**: Subscribe to event patterns like `user.*` or global `*`
- **JSON Serialization**: Save and load events for persistence or network transmission
- **Type Safety**: Strong typing throughout the API
- **Zero Dependencies**: Pure Python implementation

## Installation

```bash
uv pip install eventick
```

## Quick Start

```python
from eventick import EventBus, EventLog, Event

# Create an event log to track game state
event_log = EventLog()

# Create an event bus connected to the log
event_bus = EventBus(event_log)

# Subscribe to specific events
def handle_user_created(event):
    print(f"User created at tick {event.tick}: {event.data}")

unsubscribe = event_bus.subscribe("user.created", handle_user_created)

# Subscribe to all user events with wildcard
event_bus.subscribe("user.*", lambda event: print(f"User event: {event.type}"))

# Publish an event (automatically uses current tick from event_log)
event = event_bus.publish("user.created", {"id": 1, "name": "John"})

# Advance the game tick
event_log.advance_tick()

# Events can be serialized to JSON
json_str = event.to_json()
print(json_str)

# And deserialized back
reconstructed_event = Event.from_json(json_str)

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
```

### EventLog

The `EventLog` manages sequences of events and provides replay capability:

- Tracks current tick number
- Records events with timestamps
- Provides persistence through save/load methods

### EventBus

The `EventBus` handles event publishing and subscription:

- Supports specific event type subscriptions
- Supports wildcard subscriptions (`user.*`)
- Supports global subscriptions (`*`)
- Automatically assigns current tick from EventLog

## Development

```bash
# Clone the repository
git clone https://github.com/enricostara/eventick.git
cd eventick

# Install development dependencies
uv sync --all-extras

# Run tests
just test
```

## License

MIT License - see LICENSE file for details