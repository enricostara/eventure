# Eventually

A Python library providing a robust, type-safe event bus implementation with support for wildcard subscriptions and asynchronous event handling.

## Features

- Type-safe event handling using Python's type hints
- Support for wildcard event subscriptions
- Asynchronous event processing
- Simple and intuitive API
- Comprehensive test coverage
- Zero external dependencies

## Installation

```bash
uv pip install eventually
```

## Quick Start

```python
from eventually import EventBus, Event

# Create an event bus
event_bus = EventBus()

# Subscribe to events
unsubscribe = event_bus.subscribe("user.created", lambda event: print(f"User created: {event.data}"))

# Publish an event
event_bus.publish(Event("user.created", {"id": 1, "name": "John"}))

# Unsubscribe when done
unsubscribe()
```

## Development

```bash
# Clone the repository
git clone https://github.com/enricostara/eventually.git
cd eventually

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License - see LICENSE file for details