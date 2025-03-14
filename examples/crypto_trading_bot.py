"""
Cryptocurrency Trading Bot example for Eventure.

This example demonstrates how to use Eventure to build a simulated
cryptocurrency trading bot with market data events, trading strategies,
and portfolio management.
"""

import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List

from eventure.event import Event
from eventure.event_bus import EventBus, EventLog
from eventure.event_query import EventQuery


class OrderSide(Enum):
    """Enum for order side (buy or sell)."""

    BUY = auto()
    SELL = auto()


class OrderStatus(Enum):
    """Enum for order status."""

    PENDING = auto()
    FILLED = auto()
    CANCELED = auto()


@dataclass
class MarketData:
    """Class to hold market data for a specific asset."""

    symbol: str
    price: float
    volume: float
    timestamp: float


class CryptoTradingBot:
    """A cryptocurrency trading bot simulation using eventure.

    This bot simulates market data, implements trading strategies,
    executes orders, and manages a portfolio.
    """

    def __init__(self) -> None:
        """Initialize the trading bot with event system."""
        self.event_log: EventLog = EventLog()
        self.event_bus: EventBus = EventBus(self.event_log)

        # Market data
        self.market_data: Dict[str, MarketData] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.short_ma: Dict[str, float] = {}  # 5-period moving average
        self.long_ma: Dict[str, float] = {}  # 20-period moving average

        # Portfolio state
        self.portfolio: Dict[str, float] = {"USD": 10000.0}  # Start with $10,000
        self.open_orders: Dict[str, Dict] = {}  # Order ID -> Order details
        self.trade_history: List[Dict] = []

        # Trading parameters
        self.trading_pairs: List[str] = ["BTC/USD", "ETH/USD"]
        self.short_ma_period: int = 5
        self.long_ma_period: int = 20
        self.order_id_counter: int = 0

        # Initialize price history for each trading pair
        for pair in self.trading_pairs:
            self.price_history[pair] = []

        # Set up event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Set up event handlers for the trading bot."""
        # Market data handlers
        self.event_bus.subscribe("market.price_update", self._handle_price_update)
        self.event_bus.subscribe("market.volume_update", self._handle_volume_update)

        # Strategy handlers
        self.event_bus.subscribe("strategy.signal", self._handle_strategy_signal)

        # Order handlers
        self.event_bus.subscribe("order.created", self._handle_order_created)
        self.event_bus.subscribe("order.filled", self._handle_order_filled)
        self.event_bus.subscribe("order.canceled", self._handle_order_canceled)

        # Portfolio handlers
        self.event_bus.subscribe("portfolio.updated", self._handle_portfolio_updated)

    def start_simulation(self) -> None:
        """Start the trading bot simulation."""
        print("Starting Cryptocurrency Trading Bot simulation...")
        print(f"Initial portfolio: {self.portfolio}")
        print()

        # Simulate market data for 100 ticks
        for _tick in range(100):
            self.event_log.advance_tick()

            # Generate market data events
            for pair in self.trading_pairs:
                self._generate_market_data(pair)

            # Small delay for readability
            time.sleep(0.1)

        # Display final results
        self._display_results()

    def _generate_market_data(self, pair: str) -> None:
        """Generate simulated market data for a trading pair.

        Args:
            pair: Trading pair symbol (e.g., "BTC/USD")
        """
        # Get current price or generate initial price
        if pair in self.market_data:
            current_price = self.market_data[pair].price
            # Generate random price movement (-2% to +2%)
            price_change = current_price * (random.uniform(-0.02, 0.02))
            new_price = max(0.01, current_price + price_change)
        else:
            # Initial prices
            if pair == "BTC/USD":
                new_price = 50000.0
            elif pair == "ETH/USD":
                new_price = 3000.0
            else:
                new_price = 100.0

        # Generate random volume
        volume = random.uniform(0.5, 10.0)

        # Create market data event
        self.event_bus.publish(
            "market.price_update",
            {"symbol": pair, "price": new_price, "timestamp": time.time()},
        )

        self.event_bus.publish(
            "market.volume_update",
            {"symbol": pair, "volume": volume, "timestamp": time.time()},
        )

    def _calculate_moving_averages(self, pair: str) -> None:
        """Calculate moving averages for a trading pair.

        Args:
            pair: Trading pair symbol
        """
        prices = self.price_history[pair]

        # Only calculate if we have enough data points
        if len(prices) >= self.long_ma_period:
            # Calculate short MA
            short_window = prices[-self.short_ma_period :]
            self.short_ma[pair] = sum(short_window) / len(short_window)

            # Calculate long MA
            long_window = prices[-self.long_ma_period :]
            self.long_ma[pair] = sum(long_window) / len(long_window)

            # Check for crossovers
            self._check_for_crossovers(pair)

    def _check_for_crossovers(self, pair: str) -> None:
        """Check for moving average crossovers and generate signals.

        Args:
            pair: Trading pair symbol
        """
        # Get previous values (if they exist)
        prices = self.price_history[pair]
        if len(prices) <= self.long_ma_period:
            return

        # Check if we have at least 2 data points to detect a crossover
        if pair in self.short_ma and pair in self.long_ma:
            # Get current values
            short_ma = self.short_ma[pair]
            long_ma = self.long_ma[pair]

            # Calculate previous short MA
            prev_short_window = prices[-(self.short_ma_period + 1) : -1]
            prev_short_ma = sum(prev_short_window) / len(prev_short_window)

            # Calculate previous long MA
            prev_long_window = prices[-(self.long_ma_period + 1) : -1]
            prev_long_ma = sum(prev_long_window) / len(prev_long_window)

            # Check for bullish crossover (short MA crosses above long MA)
            if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                self.event_bus.publish(
                    "strategy.signal",
                    {
                        "symbol": pair,
                        "signal": "BUY",
                        "strategy": "MA_CROSSOVER",
                        "short_ma": short_ma,
                        "long_ma": long_ma,
                    },
                )

            # Check for bearish crossover (short MA crosses below long MA)
            elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
                self.event_bus.publish(
                    "strategy.signal",
                    {
                        "symbol": pair,
                        "signal": "SELL",
                        "strategy": "MA_CROSSOVER",
                        "short_ma": short_ma,
                        "long_ma": long_ma,
                    },
                )

    def _create_order(
        self, symbol: str, side: OrderSide, quantity: float, price: float
    ) -> str:
        """Create a new order.

        Args:
            symbol: Trading pair symbol
            side: Buy or sell
            quantity: Amount to buy/sell
            price: Limit price

        Returns:
            Order ID
        """
        # Generate order ID
        self.order_id_counter += 1
        order_id = f"order-{self.order_id_counter}"

        # Create order event
        self.event_bus.publish(
            "order.created",
            {
                "order_id": order_id,
                "symbol": symbol,
                "side": side.name,
                "quantity": quantity,
                "price": price,
                "status": OrderStatus.PENDING.name,
            },
        )

        return order_id

    def _execute_order(self, order_id: str) -> None:
        """Execute a pending order.

        Args:
            order_id: Order ID to execute
        """
        if order_id not in self.open_orders:
            print(f"Warning: Order {order_id} not found")
            return

        order = self.open_orders[order_id]

        # Create filled order event
        self.event_bus.publish(
            "order.filled",
            {
                "order_id": order_id,
                "symbol": order["symbol"],
                "side": order["side"],
                "quantity": order["quantity"],
                "price": order["price"],
                "timestamp": time.time(),
            },
        )

    def _update_portfolio(self, symbol: str, amount: float) -> None:
        """Update portfolio with a new balance.

        Args:
            symbol: Asset symbol
            amount: New amount (not delta)
        """
        self.event_bus.publish("portfolio.updated", {"symbol": symbol, "amount": amount})

    def _handle_price_update(self, event: Event) -> None:
        """Handle price update events.

        Args:
            event: Price update event
        """
        symbol = event.data["symbol"]
        price = event.data["price"]
        timestamp = event.data["timestamp"]

        # Update market data
        self.market_data[symbol] = MarketData(
            symbol=symbol,
            price=price,
            volume=self.market_data.get(
                symbol, MarketData(symbol, price, 0, timestamp)
            ).volume,
            timestamp=timestamp,
        )

        # Update price history
        self.price_history[symbol].append(price)

        # Calculate moving averages
        self._calculate_moving_averages(symbol)

        # Execute any pending orders that match the price
        for order_id, order in list(self.open_orders.items()):
            if order["symbol"] == symbol and order["status"] == OrderStatus.PENDING.name:
                # For simplicity, execute all orders immediately
                self._execute_order(order_id)

    def _handle_volume_update(self, event: Event) -> None:
        """Handle volume update events.

        Args:
            event: Volume update event
        """
        symbol = event.data["symbol"]
        volume = event.data["volume"]
        timestamp = event.data["timestamp"]

        # Update market data
        if symbol in self.market_data:
            self.market_data[symbol].volume = volume
            self.market_data[symbol].timestamp = timestamp
        else:
            # Create with default price if we don't have it yet
            self.market_data[symbol] = MarketData(symbol, 0.0, volume, timestamp)

    def _handle_strategy_signal(self, event: Event) -> None:
        """Handle strategy signal events.

        Args:
            event: Strategy signal event
        """
        symbol = event.data["symbol"]
        signal = event.data["signal"]

        # Skip if we don't have market data yet
        if symbol not in self.market_data:
            return

        # Get current price
        current_price = self.market_data[symbol].price

        # Parse the symbol to get the base and quote currencies
        base, quote = symbol.split("/")

        # Handle buy signal
        if signal == "BUY":
            # Check if we have enough quote currency (e.g., USD)
            quote_balance = self.portfolio.get(quote, 0)
            if quote_balance > 100:  # Keep some reserve
                # Calculate quantity based on 20% of available balance
                investment_amount = quote_balance * 0.2
                quantity = investment_amount / current_price

                # Create buy order
                self._create_order(symbol, OrderSide.BUY, quantity, current_price)

        # Handle sell signal
        elif signal == "SELL":
            # Check if we have any of the base currency (e.g., BTC)
            base_balance = self.portfolio.get(base, 0)
            if base_balance > 0:
                # Sell 50% of holdings
                quantity = base_balance * 0.5

                # Create sell order
                self._create_order(symbol, OrderSide.SELL, quantity, current_price)

    def _handle_order_created(self, event: Event) -> None:
        """Handle order created events.

        Args:
            event: Order created event
        """
        order_id = event.data["order_id"]

        # Store order details
        self.open_orders[order_id] = event.data

        print(
            f"Order created: {event.data['side']} {event.data['quantity']} "
            f"{event.data['symbol']} @ {event.data['price']}"
        )

    def _handle_order_filled(self, event: Event) -> None:
        """Handle order filled events.

        Args:
            event: Order filled event
        """
        order_id = event.data["order_id"]
        symbol = event.data["symbol"]
        side = event.data["side"]
        quantity = event.data["quantity"]
        price = event.data["price"]

        # Update order status
        if order_id in self.open_orders:
            self.open_orders[order_id]["status"] = OrderStatus.FILLED.name

        # Parse the symbol to get the base and quote currencies
        base, quote = symbol.split("/")

        # Update portfolio based on trade
        if side == OrderSide.BUY.name:
            # Decrease quote currency (e.g., USD)
            quote_amount = self.portfolio.get(quote, 0) - (quantity * price)
            self._update_portfolio(quote, quote_amount)

            # Increase base currency (e.g., BTC)
            base_amount = self.portfolio.get(base, 0) + quantity
            self._update_portfolio(base, base_amount)

        elif side == OrderSide.SELL.name:
            # Increase quote currency (e.g., USD)
            quote_amount = self.portfolio.get(quote, 0) + (quantity * price)
            self._update_portfolio(quote, quote_amount)

            # Decrease base currency (e.g., BTC)
            base_amount = self.portfolio.get(base, 0) - quantity
            self._update_portfolio(base, base_amount)

        # Add to trade history
        self.trade_history.append(
            {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "timestamp": time.time(),
            }
        )

        print(f"Order filled: {side} {quantity} {symbol} @ {price}")
        print(f"Updated portfolio: {self.portfolio}")
        print()

    def _handle_order_canceled(self, event: Event) -> None:
        """Handle order canceled events.

        Args:
            event: Order canceled event
        """
        order_id = event.data["order_id"]

        # Update order status
        if order_id in self.open_orders:
            self.open_orders[order_id]["status"] = OrderStatus.CANCELED.name

    def _handle_portfolio_updated(self, event: Event) -> None:
        """Handle portfolio updated events.

        Args:
            event: Portfolio updated event
        """
        symbol = event.data["symbol"]
        amount = event.data["amount"]

        # Update portfolio
        self.portfolio[symbol] = amount

    def _display_results(self) -> None:
        """Display the results of the simulation."""
        print("\n=== Simulation Results ===")
        print(f"Final portfolio: {self.portfolio}")

        # Calculate profit/loss
        initial_usd = 10000.0
        final_usd = self.portfolio.get("USD", 0)

        # Add value of cryptocurrencies
        for symbol, amount in self.portfolio.items():
            if symbol != "USD" and f"{symbol}/USD" in self.market_data:
                price = self.market_data[f"{symbol}/USD"].price
                final_usd += amount * price

        profit_loss = final_usd - initial_usd
        profit_percent = (profit_loss / initial_usd) * 100

        print(f"Profit/Loss: ${profit_loss:.2f} ({profit_percent:.2f}%)")
        print(f"Total trades: {len(self.trade_history)}")

        # Display event statistics
        print("\n=== Event Statistics ===")
        event_types = {}
        for event in self.event_log.events:
            event_types[event.type] = event_types.get(event.type, 0) + 1

        for event_type, count in event_types.items():
            print(f"{event_type}: {count} events")

        # Demonstrate event queries
        self._demonstrate_event_queries()

    def _demonstrate_event_queries(self) -> None:
        """Demonstrate event query capabilities."""
        print("\n=== Event Query Examples ===")

        # Create event query
        query = EventQuery(self.event_log)

        # Query for all strategy signals using the new API
        strategy_events = query.get_events_by_type("strategy.signal")
        print(f"Strategy Signals: {len(strategy_events)}")

        # Get the first buy signal using the new API
        buy_signals = query.get_events_by_data("signal", "BUY")
        if buy_signals:
            first_buy = buy_signals[0]
            print("\nFirst BUY signal and its cascade:")

            # Print the cascade using the new API
            query.print_single_cascade(first_buy)

            # Find orders triggered by this signal using the new API
            print("\nOrders triggered by first BUY signal:")
            child_events = query.get_child_events(first_buy)
            for child in child_events:
                print(f"  {child.type}: {child.data}")

        # Query for all filled orders using the new API
        filled_orders = query.get_events_by_type("order.filled")
        print(f"\nFilled Orders: {len(filled_orders)}")

        # Calculate average buy price for BTC
        btc_buys = [
            e
            for e in filled_orders
            if e.data["symbol"] == "BTC/USD" and e.data["side"] == "BUY"
        ]

        if btc_buys:
            total_btc = sum(e.data["quantity"] for e in btc_buys)
            total_usd = sum(e.data["quantity"] * e.data["price"] for e in btc_buys)
            avg_price = total_usd / total_btc
            print(f"\nAverage BTC buy price: ${avg_price:.2f}")


def main() -> None:
    """Run the cryptocurrency trading bot example."""
    # Set random seed for reproducibility
    random.seed(42)

    # Create and run the trading bot
    bot = CryptoTradingBot()
    bot.start_simulation()


if __name__ == "__main__":
    main()
