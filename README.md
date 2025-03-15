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

## Core Concepts

### Tick-Based Architecture

Eventure uses a tick-based architecture that provides several key advantages:

1. **Deterministic Execution**
   - Events within a tick are processed in a consistent, predictable order
   - Eliminates race conditions and timing-related bugs
   - Makes debugging significantly easier with reproducible scenarios

2. **Perfect State Reconstruction**
   - Any historical state can be precisely reconstructed by replaying events
   - Enables powerful debugging, testing, and analysis capabilities
   - Simplifies save/load functionality - just save events up to the current tick

3. **Simplified Testing**
   - Tests become deterministic and reproducible
   - Easy to write assertions about the state at specific ticks
   - Test complex event cascades with confidence

4. **Performance Optimization**
   - Events can be batched and processed efficiently within ticks
   - Natural support for parallel processing of events
   - Reduced overhead compared to continuous time systems

5. **Flexible Simulation Control**
   - Easily implement pause, step-forward, or fast-forward functionality
   - Run simulations at different speeds without affecting logic
   - Perfect for debugging complex scenarios or analyzing specific moments

```python
# Example: Using ticks for deterministic ordering
log.add_event("market.price_update", {"price": 100})  # Tick 1
log.advance_tick()
log.add_event("trading.buy_order", {"amount": 10})    # Tick 2

# Example: Getting state at a specific point in time
events_at_tick_5 = query.get_events_at_tick(5)
state_at_tick_5 = derive_game_state([e for e in log.events if e.tick <= 5])
```

### Event Cascade System

Eventure's event cascade system tracks relationships between events, providing several powerful capabilities:

1. **Causal Tracking**
   - Every event can have a parent event that triggered it
   - Complete traceability from cause to effect
   - Understand complex chains of interactions

2. **Debugging and Analysis**
   - Trace the root cause of any system behavior
   - Visualize complete event cascades
   - Identify unexpected side effects or event chains

3. **Rich Query Capabilities**
   - Filter events by their relationships
   - Find all events triggered by a specific root event
   - Analyze patterns in event propagation

4. **System Understanding**
   - Map complex interactions between system components
   - Document emergent behaviors
   - Improve system design through relationship analysis

```python
# Creating related events
def on_enemy_defeated(event):
    # This event will be linked to the parent event
    bus.publish("treasure.drop", {"item": "gold_coins"}, parent_event=event)
    bus.publish("experience.gain", {"amount": 100}, parent_event=event)

# Querying related events
root_event = query.get_event_by_id("0-ABCD-1")
cascade = query.get_cascade(root_event)  # All events triggered by this event
query.print_single_cascade(root_event)   # Visualize the cascade
```

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
bus.subscribe("*", lambda e: print(f"Any event: {e.type}"))

# Publish events
bus.publish("user.login", {"user_id": 456})

# Unsubscribe when done
unsubscribe()
```

#### Wildcard Event Subscriptions

Eventure supports three powerful wildcard subscription patterns that allow handlers to receive multiple types of events:

```python
# Exact match subscription
bus.subscribe("player.move", on_player_move)

# Prefix wildcard - receives all events with a specific prefix
bus.subscribe("player.*", on_any_player_event)  # player.move, player.attack, etc.

# Suffix wildcard - receives all events with a specific suffix
bus.subscribe("*.error", on_any_error_event)  # network.error, auth.error, etc.

# Global wildcard - receives ALL events
bus.subscribe("*", on_any_event)
```

When multiple handlers match an event, they are called in order of specificity:
1. Exact match handlers
2. Prefix wildcard handlers
3. Suffix wildcard handlers
4. Global wildcard handlers

This hierarchical dispatch system allows for both specific and general event handling, making it easy to implement logging, debugging, or cross-cutting concerns.

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

## Event Visualization Examples

The EventQuery API provides powerful visualization capabilities for event cascades. Here are some examples from the included Adventure Game example:

#### Room Entry and Combat Sequence

```
┌─── TICK 4 ───┐
│
  ↓ room.enter (caused by: player.move @ tick 3)
    ID: 4-FADA-1
    Data:
      room: treasury
      description: Glittering treasures fill this heavily guarded room.
    │
    └─ enemy.encounter
    │ ID: 4-ADCF-1
    │ Data:
    │   enemy: dragon
    │   message: A dragon appears before you!
└───────────────┘

┌─── TICK 5 ───┐
│
  ↓ combat.start (caused by: enemy.encounter @ tick 4)
    ID: 5-ABAA-1
    Data:
      enemy: dragon
      enemy_health: 100
      message: Combat with dragon begins!
│
  ↓ combat.round (caused by: enemy.encounter @ tick 4)
    ID: 5-BDBB-1
    Data:
      enemy: dragon
      round: 1
      message: Round 1 against dragon!
    │
    └─ combat.damage_dealt
    │ ID: 5-DDDF-1
    │ Data:
    │   enemy: dragon
    │   amount: 18
    │   message: You hit the dragon for 18 damage!
└───────────────┘
```

This visualization shows:
- Events organized by tick
- Parent-child relationships with indentation
- Causal connections between events (shown with arrows)
- Complete event data for analysis

To generate these visualizations in your code:

```python
# Print all events in the log organized by tick
query.print_event_cascade()

# Print a specific cascade starting from a root event
query.print_single_cascade(root_event)

# Print details of a single event
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

### Event Cascading with Parent References

```python
# Create a handler that triggers follow-up events
def combat_handler(event):
    if event.data.get("enemy_health", 0) <= 0:
        # Generate a cascade event based on the original event
        bus.publish("enemy.defeated", 
                   {"enemy": event.data["enemy"]},
                   parent_event=event)  # Parent reference maintains event chain

# Subscribe to combat events
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
uv sync --all-extras
```

### Running Tests

```bash
# Run all tests
just test
```

## License

[MIT License](LICENSE)