#!/usr/bin/env python3
"""
Adventure Game Simulation Example

This example demonstrates the eventure library's capabilities by simulating
a text-based adventure game where player actions trigger cascading events.
"""

import random
from typing import Any, Dict, List, Optional

from eventure import Event, EventBus, EventLog, EventQuery


class AdventureGame:
    """A simple text-based adventure game simulation using eventure."""

    def __init__(self) -> None:
        """Initialize the adventure game with event system."""
        self.event_log: EventLog = EventLog()
        self.event_bus: EventBus = EventBus(self.event_log)

        # Game state
        self.player_location: str = "entrance"
        self.player_health: int = 100
        self.player_inventory: List[str] = []
        self.enemies_defeated: int = 0
        self.treasure_found: int = 0
        self.game_over: bool = False

        # Subscribe to events
        self.event_bus.subscribe("player.move", self._handle_player_move)
        self.event_bus.subscribe("player.pickup_item", self._handle_pickup_item)
        self.event_bus.subscribe("room.enter", self._handle_room_enter)
        self.event_bus.subscribe("enemy.encounter", self._handle_enemy_encounter)
        self.event_bus.subscribe("combat.round", self._handle_combat_round)
        self.event_bus.subscribe("treasure.found", self._handle_treasure_found)
        self.event_bus.subscribe("player.health_change", self._handle_health_change)
        self.event_bus.subscribe("game.end", self._handle_game_end)

        # Subscribe to all events to log them

        # Game map: room_id -> {description, connections, items, enemies, treasures}
        self.game_map: Dict[str, Dict[str, Any]] = {
            "entrance": {
                "description": "You stand at the entrance of a dark dungeon.",
                "connections": ["hallway"],
                "items": ["torch"],
                "enemies": [],
                "treasures": [],
            },
            "hallway": {
                "description": "A long, dimly lit hallway stretches before you.",
                "connections": ["entrance", "chamber", "library"],
                "items": ["key"],
                "enemies": ["rat"],
                "treasures": [],
            },
            "chamber": {
                "description": "A large chamber with ancient markings on the walls.",
                "connections": ["hallway", "treasury"],
                "items": ["shield"],
                "enemies": ["skeleton"],
                "treasures": ["silver_coin"],
            },
            "library": {
                "description": "Dusty bookshelves line the walls of this forgotten library.",
                "connections": ["hallway", "laboratory"],
                "items": ["spell_book"],
                "enemies": ["ghost"],
                "treasures": ["ancient_scroll"],
            },
            "treasury": {
                "description": "Glittering treasures fill this heavily guarded room.",
                "connections": ["chamber"],
                "items": [],
                "enemies": ["dragon"],
                "treasures": ["golden_chalice", "jeweled_crown"],
            },
            "laboratory": {
                "description": "Strange apparatus and bubbling potions fill "
                + "this alchemist's lab.",
                "connections": ["library"],
                "items": ["health_potion"],
                "enemies": ["alchemist"],
                "treasures": ["magic_amulet"],
            },
        }

    def start_game(self) -> None:
        """Start the adventure game."""
        # Start the game - this will trigger the subscribed handler
        self.event_bus.publish("game.start", {"message": "Welcome to the Adventure Game!"})

        # Player starts at the entrance - this will trigger the subscribed handler
        self.event_bus.publish(
            "player.move", {"destination": "entrance", "message": "You enter the dungeon..."}
        )

        # Advance a few ticks to simulate game progression
        self._simulate_game_actions()

        # Print the final event cascade
        query: EventQuery = EventQuery(self.event_log)
        query.print_event_cascade()

        # Print game summary
        self._print_game_summary()

    def _simulate_game_actions(self) -> None:
        """Simulate a series of player actions to demonstrate event cascades."""
        # Force random seed for consistent results
        random.seed(42)

        # Move to hallway
        self.event_bus.publish(
            "player.move",
            {"destination": "hallway", "message": "You cautiously move into the hallway."},
        )

        # Pick up key
        self.event_bus.publish(
            "player.pickup_item", {"item": "key", "message": "You found a rusty key!"}
        )

        # Move to chamber
        self.event_bus.publish(
            "player.move",
            {"destination": "chamber", "message": "You enter the ancient chamber."},
        )

        # Move to treasury (triggers future events due to key)
        self.event_bus.publish(
            "player.move",
            {
                "destination": "treasury",
                "message": "You use the key to unlock the treasury door.",
            },
        )

        # End game - this should be the final event
        self.event_bus.publish(
            "game.end", {"message": "You've completed your adventure!", "outcome": "victory"}
        )

    def _handle_player_move(self, event: Event) -> None:
        """Handle player movement events."""
        self.event_log.advance_tick()
        destination: str = event.data["destination"]
        self.player_location = destination

        # Publish a room enter event through the event bus
        # The event bus will automatically dispatch to the subscribed handler
        self.event_bus.publish(
            "room.enter",
            {"room": destination, "description": self.game_map[destination]["description"]},
            parent_event=event,
        )

    def _handle_room_enter(self, event: Event) -> None:
        """Handle room entry events, potentially triggering discoveries."""
        room: str = event.data["room"]
        room_data: Dict[str, Any] = self.game_map[room]

        # Check for items in the room
        for item in room_data["items"]:
            # 50% chance to discover each item
            if random.random() > 0.5:
                self.event_bus.publish(
                    "item.discover",
                    {"item": item, "message": f"You spot a {item} in the room."},
                    parent_event=event,
                )
                # Add item to inventory
                self.player_inventory.append(item)

        # Check for enemies in the room
        for enemy in room_data["enemies"]:
            # 70% chance to encounter each enemy
            if random.random() > 0.3:
                self.event_bus.publish(
                    "enemy.encounter",
                    {"enemy": enemy, "message": f"A {enemy} appears before you!"},
                    parent_event=event,
                )

        # Check for treasures in the room
        for treasure in room_data["treasures"]:
            # 30% chance to find each treasure
            if random.random() > 0.7:
                self.event_bus.publish(
                    "treasure.found",
                    {"treasure": treasure, "message": f"You discovered a {treasure}!"},
                    parent_event=event,
                )

        # If this is the treasury and player has the key, schedule a special event
        if room == "treasury" and "key" in self.player_inventory:
            # Add a special treasure discovery
            self.event_bus.publish(
                "treasure.found",
                {
                    "treasure": "ancient_artifact",
                    "message": "The key unlocks a hidden compartment revealing "
                    + "an ancient artifact!",
                    "value": 1000,
                },
                parent_event=event,
            )

    def _handle_pickup_item(self, event: Event) -> None:
        """Handle item pickup events."""
        item: str = event.data["item"]
        self.player_inventory.append(item)

        # Special items have additional effects
        if item == "health_potion":
            self.event_bus.publish(
                "player.health_change",
                {"amount": 20, "reason": "Used health potion"},
                parent_event=event,
            )
        elif item == "torch":
            # Torch improves visibility, add future discoveries
            self.event_bus.publish(
                "item.discover",
                {
                    "item": "hidden_map",
                    "message": "With the torch light, you notice a hidden map on the wall!",
                },
                parent_event=event,
            )
            # Add to inventory
            self.player_inventory.append("hidden_map")

    def _handle_enemy_encounter(self, event: Event) -> None:
        """Handle enemy encounter events."""
        self.event_log.advance_tick()
        enemy: str = event.data["enemy"]

        # Start combat with the enemy
        self.event_bus.publish(
            "combat.start",
            {
                "enemy": enemy,
                "enemy_health": self._get_enemy_health(enemy),
                "message": f"Combat with {enemy} begins!",
            },
            parent_event=event,
        )

        # First combat round happens immediately
        self.event_bus.publish(
            "combat.round",
            {"enemy": enemy, "round": 1, "message": f"Round 1 against {enemy}!"},
            parent_event=event,
        )

        # Add two more combat rounds if game is not over yet
        if not self.game_over:
            self.event_bus.publish(
                "combat.round",
                {"enemy": enemy, "round": 2, "message": f"Round 2 against {enemy}!"},
                parent_event=event,
            )

            # Only proceed with round 3 if game is not over
            if not self.game_over:
                self.event_bus.publish(
                    "combat.round",
                    {"enemy": enemy, "round": 3, "message": f"Round 3 against {enemy}!"},
                    parent_event=event,
                )

    def _handle_combat_round(self, event: Event) -> None:
        """Handle combat round events."""
        enemy: str = event.data["enemy"]
        round_num: int = event.data["round"]

        # Determine damage dealt and taken
        damage_dealt: int = random.randint(10, 20)
        damage_taken: int = random.randint(5, 15)

        # Publish damage events
        self.event_bus.publish(
            "combat.damage_dealt",
            {
                "enemy": enemy,
                "amount": damage_dealt,
                "message": f"You hit the {enemy} for {damage_dealt} damage!",
            },
            parent_event=event,
        )

        self.event_bus.publish(
            "combat.damage_taken",
            {
                "enemy": enemy,
                "amount": damage_taken,
                "message": f"The {enemy} hits you for {damage_taken} damage!",
            },
            parent_event=event,
        )

        # Update player health
        self.event_bus.publish(
            "player.health_change",
            {"amount": -damage_taken, "reason": f"Damage from {enemy}"},
            parent_event=event,
        )
        self.event_log.advance_tick()

        # Stop processing if the game is over after health change
        if self.game_over:
            return

        # If final round, enemy is defeated
        if round_num == 3:
            self.event_bus.publish(
                "enemy.defeated",
                {"enemy": enemy, "message": f"You defeated the {enemy}!"},
                parent_event=event,
            )
            self.enemies_defeated += 1

    def _handle_treasure_found(self, event: Event) -> None:
        """Handle treasure discovery events."""
        treasure: str = event.data["treasure"]
        self.treasure_found += 1

        # Add treasure to inventory
        self.player_inventory.append(treasure)

        # Some treasures have special effects
        if treasure == "magic_amulet":
            self.event_bus.publish(
                "player.health_change",
                {"amount": 50, "reason": "Magic amulet's healing power"},
                parent_event=event,
            )

    def _handle_health_change(self, event: Event) -> None:
        """Handle player health change events."""
        amount: int = event.data["amount"]
        self.player_health += amount

        # Ensure health stays within bounds
        self.player_health = max(0, min(100, self.player_health))

        # Check for player death
        if self.player_health <= 0:
            # Publish player death event
            self.event_bus.publish(
                "player.death",
                {
                    "message": "You have been defeated!",
                    "reason": event.data.get("reason", "Unknown"),
                },
                parent_event=event,
            )

            # Game over
            self.event_bus.publish(
                "game.end", {"message": "Game Over!", "outcome": "defeat"}, parent_event=event
            )

    def _handle_game_end(self, event: Event) -> None:
        """Handle game end events."""
        # Set game_over flag to prevent further events
        self.game_over = True

        outcome: str = event.data["outcome"]

        # Publish final score event
        score: int = (
            (self.enemies_defeated * 100) + (self.treasure_found * 200) + self.player_health
        )

        self.event_bus.publish(
            "game.final_score",
            {
                "score": score,
                "enemies_defeated": self.enemies_defeated,
                "treasures_found": self.treasure_found,
                "health_remaining": self.player_health,
                "outcome": outcome,
            },
            parent_event=event,
        )

    def _get_enemy_health(self, enemy: str) -> int:
        """Get the health value for a given enemy type."""
        enemy_health: Dict[str, int] = {
            "rat": 20,
            "skeleton": 40,
            "ghost": 30,
            "dragon": 100,
            "alchemist": 50,
        }
        return enemy_health.get(enemy, 30)

    def _print_game_summary(self) -> None:
        """Print a summary of the game results."""
        print("\n" + "=" * 50)
        print("ADVENTURE GAME SUMMARY")
        print("=" * 50)
        print(f"Final Location: {self.player_location}")
        print(f"Health Remaining: {self.player_health}")
        print(f"Items Collected: {', '.join(self.player_inventory)}")
        print(f"Enemies Defeated: {self.enemies_defeated}")
        print(f"Treasures Found: {self.treasure_found}")

        # Calculate final score
        score: int = (
            (self.enemies_defeated * 100) + (self.treasure_found * 200) + self.player_health
        )
        print(f"Final Score: {score}")
        print("=" * 50)

        # Show how to query specific events
        self._demonstrate_event_queries()

    def _demonstrate_event_queries(self) -> None:
        """Demonstrate various ways to query the event log."""
        print("\n" + "=" * 50)
        print("EVENT QUERY DEMONSTRATIONS")
        print("=" * 50)

        # Create an event query
        query: EventQuery = EventQuery(self.event_log)

        # Get all combat-related events using the new API
        combat_events: List[Event] = [
            e
            for e in query.get_events_by_type("combat.start")
            + query.get_events_by_type("combat.attack")
            + query.get_events_by_type("combat.end")
        ]
        print(f"Total Combat Events: {len(combat_events)}")

        # Get all treasure events using the new API
        treasure_events: List[Event] = query.get_events_by_type("treasure.found")
        print(f"Treasure Discovery Events: {len(treasure_events)}")

        # Get all events triggered by the first move event using the new API
        move_events: List[Event] = query.get_events_by_type("player.move")
        if move_events:
            first_move: Event = move_events[0]
            child_events: List[Event] = query.get_child_events(first_move)
            print(f"Events Triggered by First Move: {len(child_events)}")

        # Create a focused event query for the treasury room events
        print("\nAll events related to the treasury room:")

        # First get all room.enter events for the treasury
        treasury_enter_events: List[Event] = query.get_events_by_data("room", "treasury")

        # Then collect all child events of treasury room entry
        treasury_events: List[Event] = []
        for event in treasury_enter_events:
            treasury_events.append(event)
            treasury_events.extend(query.get_child_events(event))

        # Create a mini event log with just these events
        if treasury_events:
            focused_log: EventLog = EventLog()
            for event in treasury_events:
                # Add the event with its original parent
                parent: Optional[Event] = (
                    self.event_log.get_event_by_id(event.parent_id)
                    if event.parent_id
                    else None
                )
                focused_log.add_event(event.type, event.data, parent_event=parent)

            # Print the focused cascade
            print("\nTreasury Room Event Cascade:")
            focused_query: EventQuery = EventQuery(focused_log)
            focused_query.print_event_cascade()


if __name__ == "__main__":
    # Create and run the adventure game
    game: AdventureGame = AdventureGame()
    game.start_game()
