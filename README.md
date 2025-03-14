# Eventure

A powerful event-driven framework for simulations, games, and complex systems with comprehensive event tracking, querying, and analysis capabilities.

## Features

- **Event Management**
  - Immutable events with tick, timestamp, type, data, and unique ID attributes
  - Parent-child relationships between events for cascade tracking
  - JSON serialization for persistence and network transmission

- **Event Log & Bus**
  - EventLog: Track, save, and replay sequences of events
  - EventBus: Decouple event producers from consumers with wildcard subscriptions
  - Game state reconstruction through deterministic event replay

- **Advanced Event Querying**
  - Filter events by type, data content, or relationships
  - Analyze event cascades and parent-child structures
  - Count, group, and visualize events with detailed formatting
  - Query events by tick, root events, and other criteria

- **Ready-to-Use Examples**
  - Cryptocurrency Trading Bot: Financial simulation with market events
  - Adventure Game: Complete game state management through events

- **Developer-Friendly**
  - Type-safe API with comprehensive type hints
  - Zero dependencies (pure Python implementation)
  - Extensive test coverage
  - Detailed documentation

## Installation

```bash
# Using pip
pip install eventure

# Using uv (recommended)
uv add eventure
```

## Core Components

### Event

The fundamental unit representing something that happened:

```python
from eventure import Event

# Create an event
event = Event(
    tick=0, 
    timestamp=time.time(), 
    type="user.login", 
    data={"user_id": 123, "ip": "192.168.1.1"}
)

# Events have unique IDs and can be serialized
print(f"Event ID: {event.id}")  # Format: {tick}-{typeHash}-{sequence}
json_str = event.to_json()
```

### EventLog

Tracks, stores, and manages events in a time-ordered sequence:

```python
from eventure import EventLog

# Create an event log
log = EventLog()

# Add events to the log
event = log.add_event("user.login", {"user_id": 123})
log.advance_tick()  # Move to next discrete time step
log.add_event("user.action", {"user_id": 123, "action": "view_profile"})

# Create child events (establishing causal relationships)
parent = log.add_event("combat.start", {"player": "hero", "enemy": "dragon"})
child = log.add_event("combat.attack", {"damage": 15}, parent_event=parent)

# Save and load event history
log.save_to_file("game_events.json")
new_log = EventLog.load_from_file("game_events.json")
```

### EventBus

Manages event publication and subscription:

```python
from eventure import EventBus

# Create an event bus connected to a log
bus = EventBus(log)

# Subscribe to specific events
def on_login(event):
    print(f"User {event.data['user_id']} logged in")
    
unsubscribe = bus.subscribe("user.login", on_login)

# Subscribe with wildcards
bus.subscribe("user.*", lambda e: print(f"User event: {e.type}"))
bus.subscribe("*.error", lambda e: print(f"Error: {e.data['message']}"))

# Publish events
bus.publish("user.login", {"user_id": 456})

# Unsubscribe when done
unsubscribe()
```

### EventQuery

Powerful API for querying, analyzing, and visualizing events:

```python
from eventure import EventQuery

# Create a query interface for an event log
query = EventQuery(log)

# Filter events
combat_events = query.get_events_by_type("combat.attack")
dragon_events = query.get_events_by_data("enemy", "dragon")

# Analyze relationships
child_events = query.get_child_events(parent_event)
cascade = query.get_cascade_events(root_event)

# Count and group
type_counts = query.count_events_by_type()
print(f"Combat events: {type_counts.get('combat.attack', 0)}")

# Get events by tick or relationship
tick5_events = query.get_events_at_tick(5)
root_events = query.get_root_events()

# Visualize events and cascades
query.print_event_cascade()  # All events organized by tick
query.print_single_cascade(root_event)  # Show a specific cascade
query.print_event_details(event)  # Show details of a single event
```

## Example Applications

Eventure includes two complete example applications demonstrating real-world usage:

### Cryptocurrency Trading Bot

A simulated trading system showing market events, trading signals, and order execution:

```python
from examples.crypto_trading_bot import CryptoTradingBot

# Create and run a trading simulation
bot = CryptoTradingBot()
bot.run_simulation()

# Query interesting patterns from the event log
query = EventQuery(bot.event_log)
buy_signals = query.get_events_by_data("signal", "BUY")
```

Key features demonstrated:
- Market simulation with price and volume updates
- Trading strategy implementation via events
- Order creation and execution
- Portfolio tracking
- Event-based system analysis

### Adventure Game

A text-based adventure game showing game state management:

```python
from examples.adventure_game import AdventureGame

# Create and run a game
game = AdventureGame()
game.run_game()

# Analyze game events
query = EventQuery(game.event_log)
combat_events = query.get_events_by_type("combat.start")
treasure_events = query.get_events_by_type("treasure.found")
```

Key features demonstrated:
- Room navigation and discovery
- Item collection and inventory management
- Enemy encounters and combat
- Event cascades (e.g., entering a room triggers discoveries)
- Game state derivation from events

## EventQuery API in Detail

The EventQuery API provides a consistent set of methods for analyzing and visualizing events:

### Filtering Events

```python
# By event type
strategy_signals = query.get_events_by_type("strategy.signal")

# By data content
buy_signals = query.get_events_by_data("signal", "BUY")
dragon_encounters = query.get_events_by_data("enemy", "dragon")

# By tick
tick_3_events = query.get_events_at_tick(3)

# Root events (with no parent or parent in previous tick)
root_events = query.get_root_events()
```

### Relationship Queries

```python
# Direct children of an event
children = query.get_child_events(parent_event)

# Complete cascade (parent, children, grandchildren, etc.)
full_cascade = query.get_cascade_events(root_event)
```

### Analysis Methods

```python
# Count events by type
counts = query.count_events_by_type()
print(f"Total combat events: {sum(counts.get(t, 0) for t in counts if t.startswith('combat.'))}")
```

### Visualization

```python
# Print all events organized by tick
query.print_event_cascade()

# Print a specific event cascade
query.print_single_cascade(root_event)

# Print details of a specific event
query.print_event_details(event)
```

## Advanced Usage

### Event Replay and State Reconstruction

One of Eventure's most powerful features is the ability to reconstruct state by replaying events:

```python
# State can be derived entirely from events
def derive_game_state(events):
    state = {"health": 100, "inventory": [], "location": "start"}
    
    for event in events:
        if event.type == "player.damage":
            state["health"] -= event.data["amount"]
        elif event.type == "item.pickup":
            state["inventory"].append(event.data["item"])
        elif event.type == "player.move":
            state["location"] = event.data["destination"]
            
    return state

# Current state from all events
current_state = derive_game_state(log.events)

# Historical state (state at tick 5)
tick_5_events = [e for e in log.events if e.tick <= 5]
historical_state = derive_game_state(tick_5_events)
```

### Custom Event Handlers with EventBus

```python
# Create specialized handlers
def combat_handler(event):
    if event.data.get("enemy_health", 0) <= 0:
        # Generate a cascade event
        bus.publish("enemy.defeated", 
                   {"enemy": event.data["enemy"]},
                   parent_event=event)

# Subscribe to events
bus.subscribe("combat.attack", combat_handler)
```

## API Reference

For the complete API documentation, see the [API Reference](src/README.md).

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/eventure.git
cd eventure

# Install development dependencies
uv venv
. .venv/bin/activate
uv install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_event_query.py
```

### Building Documentation

```bash
# Generate API documentation
just doc
```

## License

[MIT License](LICENSE)