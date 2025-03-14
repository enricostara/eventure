# Table of Contents

* [eventure](#eventure)
* [eventure.event](#eventure.event)
  * [Event](#eventure.event.Event)
    * [timestamp](#eventure.event.Event.timestamp)
    * [id](#eventure.event.Event.id)
    * [parent\_id](#eventure.event.Event.parent_id)
    * [to\_json](#eventure.event.Event.to_json)
    * [from\_json](#eventure.event.Event.from_json)
* [eventure.event\_log](#eventure.event_log)
  * [EventLog](#eventure.event_log.EventLog)
    * [current\_tick](#eventure.event_log.EventLog.current_tick)
    * [advance\_tick](#eventure.event_log.EventLog.advance_tick)
    * [add\_event](#eventure.event_log.EventLog.add_event)
    * [get\_events\_at\_tick](#eventure.event_log.EventLog.get_events_at_tick)
    * [get\_event\_by\_id](#eventure.event_log.EventLog.get_event_by_id)
    * [get\_event\_cascade](#eventure.event_log.EventLog.get_event_cascade)
    * [create\_query](#eventure.event_log.EventLog.create_query)
    * [save\_to\_file](#eventure.event_log.EventLog.save_to_file)
    * [load\_from\_file](#eventure.event_log.EventLog.load_from_file)
* [eventure.event\_bus](#eventure.event_bus)
  * [EventBus](#eventure.event_bus.EventBus)
    * [\_\_init\_\_](#eventure.event_bus.EventBus.__init__)
    * [subscribe](#eventure.event_bus.EventBus.subscribe)
    * [publish](#eventure.event_bus.EventBus.publish)
    * [dispatch](#eventure.event_bus.EventBus.dispatch)
* [eventure.event\_query](#eventure.event_query)
  * [EventQuery](#eventure.event_query.EventQuery)
    * [\_\_init\_\_](#eventure.event_query.EventQuery.__init__)
    * [print\_event\_cascade](#eventure.event_query.EventQuery.print_event_cascade)
    * [get\_events\_by\_type](#eventure.event_query.EventQuery.get_events_by_type)
    * [get\_events\_by\_data](#eventure.event_query.EventQuery.get_events_by_data)
    * [get\_child\_events](#eventure.event_query.EventQuery.get_child_events)
    * [get\_cascade\_events](#eventure.event_query.EventQuery.get_cascade_events)
    * [print\_event\_details](#eventure.event_query.EventQuery.print_event_details)
    * [print\_single\_cascade](#eventure.event_query.EventQuery.print_single_cascade)
    * [count\_events\_by\_type](#eventure.event_query.EventQuery.count_events_by_type)
    * [get\_events\_at\_tick](#eventure.event_query.EventQuery.get_events_at_tick)
    * [get\_root\_events](#eventure.event_query.EventQuery.get_root_events)

<a id="eventure"></a>

# eventure

<a id="eventure.event"></a>

# eventure.event

Event handling module for Eventure.

This module provides the core Event and EventBus classes for implementing
a robust event system with type-safe event handling and wildcard subscriptions.

<a id="eventure.event.Event"></a>

## Event Objects

```python
@dataclass
class Event()
```

Represents a single game event that occurred at a specific tick.

Events are immutable records of state changes in the game. Each event:
- Is tied to a specific tick number
- Has a UTC timestamp for real-world time reference
- Contains a type identifier for different kinds of events
- Includes arbitrary data specific to the event type
- Has a unique event_id in the format tick-typeHash-sequence
- May reference a parent event that caused this event (for cascade tracking)

**Arguments**:

- `tick` - Game tick when the event occurred
- `timestamp` - UTC timestamp when the event occurred
- `type` - Event type from the EventType enum
- `data` - Dictionary containing event-specific data
- `id` - Optional explicit event ID (generated if not provided)
- `parent_id` - Optional ID of the parent event that caused this one

<a id="eventure.event.Event.timestamp"></a>

#### timestamp

UTC timestamp

<a id="eventure.event.Event.id"></a>

#### id

Will be set in __post_init__

<a id="eventure.event.Event.parent_id"></a>

#### parent\_id

Reference to parent event that caused this one

<a id="eventure.event.Event.to_json"></a>

#### to\_json

```python
def to_json() -> str
```

Convert event to JSON string for storage or transmission.

<a id="eventure.event.Event.from_json"></a>

#### from\_json

```python
@classmethod
def from_json(cls, json_str: str) -> "Event"
```

Create event from JSON string for loading or receiving.

<a id="eventure.event_log"></a>

# eventure.event\_log

Event logging module for Eventure.

This module provides the EventLog class for managing and storing events in the game.

<a id="eventure.event_log.EventLog"></a>

## EventLog Objects

```python
class EventLog()
```

Manages the sequence of game events and provides replay capability.

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

<a id="eventure.event_log.EventLog.current_tick"></a>

#### current\_tick

```python
@property
def current_tick() -> int
```

Current game tick number.

Ticks are the fundamental unit of game time. Each tick can
contain zero or more events that modify the game state.

<a id="eventure.event_log.EventLog.advance_tick"></a>

#### advance\_tick

```python
def advance_tick() -> None
```

Advance to next tick.

This should be called once per game update cycle. Multiple
events can occur within a single tick, but they will always
be processed in the order they were added.

<a id="eventure.event_log.EventLog.add_event"></a>

#### add\_event

```python
def add_event(type: str,
              data: Dict[str, Any],
              parent_event: Optional[Event] = None) -> Event
```

Add a new event at the current tick.

**Arguments**:

- `type` - Event type as a string
- `data` - Dictionary containing event-specific data
- `parent_event` - Optional parent event that caused this event (for cascade tracking)
  

**Returns**:

  The newly created and added Event
  

**Notes**:

  Events are immutable once created. To modify game state,
  create a new event rather than trying to modify existing ones.

<a id="eventure.event_log.EventLog.get_events_at_tick"></a>

#### get\_events\_at\_tick

```python
def get_events_at_tick(tick: int) -> List[Event]
```

Get all events that occurred at a specific tick.

This is useful for:
- Debugging what happened at a specific point in time
- Processing all state changes for a given tick
- Analyzing game history

<a id="eventure.event_log.EventLog.get_event_by_id"></a>

#### get\_event\_by\_id

```python
def get_event_by_id(event_id: str) -> Optional[Event]
```

Get an event by its unique ID.

**Arguments**:

- `event_id` - The unique ID of the event to find
  

**Returns**:

  The event with the given ID, or None if not found

<a id="eventure.event_log.EventLog.get_event_cascade"></a>

#### get\_event\_cascade

```python
def get_event_cascade(event_id: str) -> List[Event]
```

Get the cascade of events starting from the specified event ID.

This returns the event with the given ID and all events that have it
as an ancestor in their parent chain.

**Arguments**:

- `event_id` - The ID of the root event in the cascade
  

**Returns**:

  A list of events in the cascade, ordered by tick and sequence

<a id="eventure.event_log.EventLog.create_query"></a>

#### create\_query

```python
def create_query()
```

Create an EventQuery instance for this event log.

**Returns**:

  An EventQuery instance that can be used to visualize and analyze this event log.

<a id="eventure.event_log.EventLog.save_to_file"></a>

#### save\_to\_file

```python
def save_to_file(filename: str) -> None
```

Save event log to file.

The entire game state can be reconstructed from this file.
Each event is stored as a separate line of JSON for easy
parsing and appending.

<a id="eventure.event_log.EventLog.load_from_file"></a>

#### load\_from\_file

```python
@classmethod
def load_from_file(cls, filename: str) -> "EventLog"
```

Load event log from file.

Creates a new EventLog instance and populates it with
events from the saved file. The current tick is set to
the highest tick found in the loaded events.

<a id="eventure.event_bus"></a>

# eventure.event\_bus

Event bus module for Eventure.

This module provides the EventBus class for publishing events and subscribing to them.

<a id="eventure.event_bus.EventBus"></a>

## EventBus Objects

```python
class EventBus()
```

Central event bus for publishing events and subscribing to them.

The EventBus decouples event producers from event consumers, allowing
components to communicate without direct references to each other.

Features:
- Subscribe to specific event types
- Publish events to all interested subscribers
- Automatic event creation with current tick and timestamp
- Support for event cascade tracking through parent-child relationships

<a id="eventure.event_bus.EventBus.__init__"></a>

#### \_\_init\_\_

```python
def __init__(event_log: EventLog)
```

Initialize the event bus.

**Arguments**:

- `event_log` - Reference to an EventLog for event creation and tick information

<a id="eventure.event_bus.EventBus.subscribe"></a>

#### subscribe

```python
def subscribe(event_type: str, handler: Callable[[Event],
                                                 None]) -> Callable[[], None]
```

Subscribe a handler to a specific event type.

**Arguments**:

- `event_type` - The type of event to subscribe to as a string
- `handler` - Function to call when an event of this type is published
  

**Returns**:

  A function that can be called to unsubscribe the handler

<a id="eventure.event_bus.EventBus.publish"></a>

#### publish

```python
def publish(event_type: str,
            data: Dict[str, Any],
            parent_event: Optional[Event] = None) -> Event
```

Publish an event to all subscribers.

**Arguments**:

- `event_type` - The type of event to publish as a string
- `data` - Dictionary containing event-specific data
- `parent_event` - Optional parent event that caused this event (for cascade tracking)
  

**Returns**:

  The created event
  

**Notes**:

  This method adds the event to the event log.
  It also dispatches the event to all subscribers.

<a id="eventure.event_bus.EventBus.dispatch"></a>

#### dispatch

```python
def dispatch(event: Event) -> None
```

Dispatch the event to all interested subscribers.

**Arguments**:

- `event` - The event to dispatch
  

**Notes**:

  This method supports two types of wildcard subscriptions:
  1. Global wildcard "*" which will receive all events regardless of type
  2. Prefix wildcard "prefix.*" which will receive all events with the given prefix
  
  The event is dispatched to handlers in this order:
  1. Exact type match subscribers
  2. Prefix wildcard subscribers
  3. Global wildcard subscribers

<a id="eventure.event_query"></a>

# eventure.event\_query

Event query and visualization module for Eventure.

This module provides tools for querying and visualizing event logs,
including event cascade relationships and parent-child event tracking.

<a id="eventure.event_query.EventQuery"></a>

## EventQuery Objects

```python
class EventQuery()
```

Provides query and visualization capabilities for event logs.

This class offers methods to analyze and display event relationships,
helping with debugging and understanding complex event cascades.

<a id="eventure.event_query.EventQuery.__init__"></a>

#### \_\_init\_\_

```python
def __init__(event_log: EventLog)
```

Initialize with an event log to query.

**Arguments**:

- `event_log` - The event log to query and visualize

<a id="eventure.event_query.EventQuery.print_event_cascade"></a>

#### print\_event\_cascade

```python
def print_event_cascade(file: TextIO = sys.stdout,
                        show_data: bool = True) -> None
```

Print events organized by tick with clear cascade relationships.
Optimized for showing parent-child relationships within the same tick.

This method provides a visual representation of the event log, showing
how events relate to each other across ticks and within the same tick.
It's especially useful for debugging complex event sequences and understanding
cause-effect relationships between events.

**Arguments**:

- `file` - File-like object to print to (defaults to stdout).
- `show_data` - Whether to show event data (defaults to True).

<a id="eventure.event_query.EventQuery.get_events_by_type"></a>

#### get\_events\_by\_type

```python
def get_events_by_type(event_type: str) -> List[Event]
```

Get all events matching a specific type.

**Arguments**:

- `event_type` - Event type to filter by
  

**Returns**:

  List of matching events

<a id="eventure.event_query.EventQuery.get_events_by_data"></a>

#### get\_events\_by\_data

```python
def get_events_by_data(key: str, value: Any) -> List[Event]
```

Get all events with matching data key-value pair.

**Arguments**:

- `key` - Key in event data to match
- `value` - Value to match against
  

**Returns**:

  List of matching events

<a id="eventure.event_query.EventQuery.get_child_events"></a>

#### get\_child\_events

```python
def get_child_events(parent_event: Event) -> List[Event]
```

Get all events that are direct children of the given event.

**Arguments**:

- `parent_event` - Parent event to find children for
  

**Returns**:

  List of child events

<a id="eventure.event_query.EventQuery.get_cascade_events"></a>

#### get\_cascade\_events

```python
def get_cascade_events(root_event: Event) -> List[Event]
```

Get all events in the cascade starting from the given root event.
This includes the root event, its children, their children, etc.

**Arguments**:

- `root_event` - Root event to find cascade for
  

**Returns**:

  List of events in the cascade (including the root)

<a id="eventure.event_query.EventQuery.print_event_details"></a>

#### print\_event\_details

```python
def print_event_details(event: Event,
                        file: TextIO = sys.stdout,
                        show_data: bool = True) -> None
```

Print details of a single event.

**Arguments**:

- `event` - Event to print details for
- `file` - File-like object to print to
- `show_data` - Whether to show event data

<a id="eventure.event_query.EventQuery.print_single_cascade"></a>

#### print\_single\_cascade

```python
def print_single_cascade(root_event: Event,
                         file: TextIO = sys.stdout,
                         show_data: bool = True) -> None
```

Print a single event cascade starting from the root event.

**Arguments**:

- `root_event` - Root event to start cascade from
- `file` - File-like object to print to
- `show_data` - Whether to show event data

<a id="eventure.event_query.EventQuery.count_events_by_type"></a>

#### count\_events\_by\_type

```python
def count_events_by_type() -> Dict[str, int]
```

Count events by type.

**Returns**:

  Dictionary mapping event types to counts

<a id="eventure.event_query.EventQuery.get_events_at_tick"></a>

#### get\_events\_at\_tick

```python
def get_events_at_tick(tick: int) -> List[Event]
```

Get all events that occurred at a specific tick.

**Arguments**:

- `tick` - Tick number to filter by
  

**Returns**:

  List of events at the specified tick

<a id="eventure.event_query.EventQuery.get_root_events"></a>

#### get\_root\_events

```python
def get_root_events(tick: Optional[int] = None) -> List[Event]
```

Get all root events, optionally filtered by tick.

Root events are those with no parent or whose parent is in a previous tick.

**Arguments**:

- `tick` - Optional tick to filter by
  

**Returns**:

  List of root events

