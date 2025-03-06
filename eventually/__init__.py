"""
Eventually - A robust, type-safe event bus implementation.

This package provides a simple yet powerful event bus system with support for
wildcard subscriptions and type-safe event handling.
"""

from .event import Event, EventBus

__version__ = "0.1.0"
__all__ = ["Event", "EventBus"]
