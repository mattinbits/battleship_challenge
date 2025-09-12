"""
Main entry point for the battleship challenge.

This script orchestrates games between competing bots.
"""

import argparse
import importlib
import inspect
import pkgutil
import sys
from typing import Type, Tuple
from .interface import BattleshipBot
from .game import BattleshipGame


def discover_bot_class(bot_name: str) -> Type[BattleshipBot]:
    """Discover and import a bot class by name.
    
    Args:
        bot_name: Name of the bot class to import
        
    Returns:
        The bot class
        
    Raises:
        ImportError: If the bot cannot be found or imported
        ValueError: If the imported class is not a valid BattleshipBot
    """
    # First try to import from the built-in bots modules
    try:
        from . import bots
        modules_to_search = []
        
        # Dynamically discover all modules in the bots package
        for _, modname, _ in pkgutil.iter_modules(bots.__path__, bots.__name__ + "."):
            try:
                module = importlib.import_module(modname)
                modules_to_search.append(module)
            except ImportError:
                continue
        
        # Look for the bot class in all discovered modules
        for module in modules_to_search:
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name == bot_name and issubclass(obj, BattleshipBot) and obj != BattleshipBot:
                    return obj
    except ImportError:
        pass
    
    # Try to import from external module
    try:
        # Try importing as a module path (e.g., "my_bots.smart_bot.SmartBot")
        if '.' in bot_name:
            module_path, class_name = bot_name.rsplit('.', 1)
            module = importlib.import_module(module_path)
            bot_class = getattr(module, class_name)
        else:
            # Try importing from current directory or Python path
            # Look for a module with lowercase version of class name
            module_name = bot_name.lower()
            try:
                module = importlib.import_module(module_name)
                bot_class = getattr(module, bot_name)
            except (ImportError, AttributeError):
                # Last resort: try importing from battleship_challenge.bots
                module = importlib.import_module(f'battleship_challenge.bots.{module_name}')
                bot_class = getattr(module, bot_name)
        
        # Validate that it's a proper BattleshipBot subclass
        if not (inspect.isclass(bot_class) and 
                issubclass(bot_class, BattleshipBot) and 
                bot_class != BattleshipBot):
            raise ValueError(f"{bot_name} is not a valid BattleshipBot subclass")
        
        return bot_class
        
    except (ImportError, AttributeError, ValueError) as e:
        raise ImportError(f"Could not find or import bot class '{bot_name}': {e}")


def create_bot_instances(bot1_class: Type[BattleshipBot], bot2_class: Type[BattleshipBot], 
                        board_size: Tuple[int, int], ships: list) -> Tuple[BattleshipBot, BattleshipBot]:
    """Create instances of both bot classes.
    
    Args:
        bot1_class: First bot class
        bot2_class: Second bot class
        board_size: Board dimensions
        ships: List of ship lengths
        
    Returns:
        Tuple of (bot1_instance, bot2_instance)
    """
    bot1 = bot1_class("Player1", board_size, ships)
    bot2 = bot2_class("Player2", board_size, ships)
    return bot1, bot2


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Run a battleship game between two bots")
    parser.add_argument("bot1", help="Name of the first bot class")
    parser.add_argument("bot2", help="Name of the second bot class")
    parser.add_argument("--board-size", default="10x10", 
                       help="Board size in format WIDTHxHEIGHT (default: 10x10)")
    parser.add_argument("--ships", default="5,4,3,3,2",
                       help="Comma-separated list of ship lengths (default: 5,4,3,3,2)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output during the game")
    parser.add_argument("--visualize", action="store_true",
                       help="Show the game board and moves in real-time")
    
    args = parser.parse_args()
    
    # Parse board size
    try:
        width, height = map(int, args.board_size.split('x'))
        board_size = (width, height)
    except ValueError:
        print(f"Error: Invalid board size format '{args.board_size}'. Use WIDTHxHEIGHT (e.g., 10x10)")
        sys.exit(1)
    
    # Parse ships
    try:
        ships = list(map(int, args.ships.split(',')))
    except ValueError:
        print(f"Error: Invalid ships format '{args.ships}'. Use comma-separated integers (e.g., 5,4,3,3,2)")
        sys.exit(1)
    
    print(f"Starting battleship game: {args.bot1} vs {args.bot2}")
    print(f"Board size: {board_size[0]}x{board_size[1]}")
    print(f"Ships: {ships}")
    print("-" * 50)
    
    try:
        # Discover and import bot classes
        if args.verbose:
            print(f"Loading {args.bot1}...")
        bot1_class = discover_bot_class(args.bot1)
        
        if args.verbose:
            print(f"Loading {args.bot2}...")
        bot2_class = discover_bot_class(args.bot2)
        
        # Create bot instances
        if args.verbose:
            print("Creating bot instances...")
        bot1, bot2 = create_bot_instances(bot1_class, bot2_class, board_size, ships)
        
        # Create and run the game
        if args.verbose:
            print("Starting game...")
        game = BattleshipGame(bot1, bot2, board_size, ships, visualize=args.visualize)
        winner = game.play_game()
        
        print(f"Game complete! Winner: {winner}")
        
    except ImportError as e:
        print(f"Error loading bots: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during game: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()