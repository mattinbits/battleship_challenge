#!/usr/bin/env python3
"""
Tournament command line interface for battleship challenge.

This script runs tournaments between multiple bots across different configurations.
"""

import argparse
import sys
from typing import List
from .tournament import Tournament, GameConfig


def parse_board_size(board_size_str: str) -> tuple[int, int]:
    """Parse board size from string format like '10x10'."""
    try:
        width, height = map(int, board_size_str.split('x'))
        return (width, height)
    except ValueError:
        raise ValueError(f"Invalid board size format '{board_size_str}'. Use WIDTHxHEIGHT (e.g., 10x10)")


def parse_ships(ships_str: str) -> List[int]:
    """Parse ship configuration from comma-separated string."""
    try:
        return list(map(int, ships_str.split(',')))
    except ValueError:
        raise ValueError(f"Invalid ships format '{ships_str}'. Use comma-separated integers (e.g., 5,4,3,3,2)")


def parse_config_file(config_file: str) -> List[GameConfig]:
    """Parse tournament configuration from a file.
    
    File format (one config per line):
    name:board_size:ships
    Example:
    Standard:10x10:5,4,3,3,2
    Large:15x15:6,5,4,4,3,3,2
    Small:8x8:4,3,3,2
    """
    configs = []
    
    try:
        with open(config_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    parts = line.split(':')
                    if len(parts) != 3:
                        raise ValueError("Expected format: name:board_size:ships")
                    
                    name, board_size_str, ships_str = parts
                    board_size = parse_board_size(board_size_str)
                    ships = parse_ships(ships_str)
                    
                    configs.append(GameConfig(
                        board_size=board_size,
                        ships=ships,
                        name=name
                    ))
                    
                except ValueError as e:
                    print(f"Error parsing line {line_num} in {config_file}: {e}")
                    sys.exit(1)
                    
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading configuration file '{config_file}': {e}")
        sys.exit(1)
    
    return configs


def main():
    """Main entry point for the tournament CLI."""
    parser = argparse.ArgumentParser(
        description="Run a battleship tournament between multiple bots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple tournament with default settings
  python -m battleship_challenge.tournament_cli RandomBot RandomBot RandomBot

  # Tournament with custom board and ships
  python -m battleship_challenge.tournament_cli RandomBot SmartBot --board-size 8x8 --ships 4,3,2

  # Tournament with multiple configurations from file
  python -m battleship_challenge.tournament_cli RandomBot SmartBot --config-file tournament.conf

  # Verbose output with fewer games per matchup
  python -m battleship_challenge.tournament_cli RandomBot SmartBot --games-per-matchup 5 --verbose

Configuration file format (one per line):
  name:board_size:ships
  Standard:10x10:5,4,3,3,2
  Large:15x15:6,5,4,4,3,3,2
        """
    )
    
    parser.add_argument("bots", nargs="+", 
                       help="Names of bot classes to compete (minimum 2)")
    parser.add_argument("--board-size", default="10x10",
                       help="Board size in format WIDTHxHEIGHT (default: 10x10)")
    parser.add_argument("--ships", default="5,4,3,3,2",
                       help="Comma-separated list of ship lengths (default: 5,4,3,3,2)")
    parser.add_argument("--config-file", 
                       help="File containing multiple game configurations (overrides --board-size and --ships)")
    parser.add_argument("--games-per-matchup", type=int, default=10,
                       help="Number of games each pair plays per configuration (default: 10)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output showing individual game results")
    
    args = parser.parse_args()
    
    # Validate minimum number of bots
    if len(args.bots) < 2:
        print("Error: At least 2 bots are required for a tournament")
        sys.exit(1)
    
    # Parse game configurations
    if args.config_file:
        configs = parse_config_file(args.config_file)
        if not configs:
            print(f"Error: No valid configurations found in {args.config_file}")
            sys.exit(1)
    else:
        # Single configuration from command line arguments
        try:
            board_size = parse_board_size(args.board_size)
            ships = parse_ships(args.ships)
            configs = [GameConfig(board_size=board_size, ships=ships)]
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    # Validate games per matchup
    if args.games_per_matchup < 1:
        print("Error: --games-per-matchup must be at least 1")
        sys.exit(1)
    
    # Print tournament setup
    print("BATTLESHIP TOURNAMENT")
    print("=" * 50)
    print(f"Bots: {', '.join(args.bots)}")
    print(f"Configurations: {len(configs)}")
    for config in configs:
        print(f"  - {config.name}: {config.board_size[0]}x{config.board_size[1]} board, ships {config.ships}")
    print(f"Games per matchup: {args.games_per_matchup}")
    
    try:
        # Create and run tournament
        tournament = Tournament(args.bots, configs, args.games_per_matchup)
        results = tournament.run_tournament(verbose=args.verbose)
        
        # Display results
        tournament.print_results(results)
        
    except ImportError as e:
        print(f"Error loading bots: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nTournament interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during tournament: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()