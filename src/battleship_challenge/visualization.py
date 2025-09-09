"""
Battleship game visualization module.

This module handles the display of game boards with colors and in-place updates.
"""

import os
import sys
import time
from typing import List, Tuple, Set
from .interface import ShotResult, ShotResponse


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Foreground colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # Cursor control
    CLEAR_SCREEN = '\033[2J'
    MOVE_CURSOR_HOME = '\033[H'
    HIDE_CURSOR = '\033[?25l'
    SHOW_CURSOR = '\033[?25h'


class BattleshipVisualizer:
    """Handles visualization of battleship games with colors and in-place updates."""
    
    def __init__(self, board_size: Tuple[int, int] = (10, 10)):
        """Initialize the visualizer.
        
        Args:
            board_size: Size of the game board (width, height)
        """
        self.board_size = board_size
        self.colors_supported = self._check_color_support()
        self.display_initialized = False
    
    def _check_color_support(self) -> bool:
        """Check if the terminal supports colors."""
        return (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
            os.environ.get('TERM', '').lower() != 'dumb' and
            os.environ.get('NO_COLOR', '').lower() not in ('1', 'true', 'yes')
        )
    
    def init_display(self):
        """Initialize the display for in-place updates."""
        if not self.display_initialized and self.colors_supported:
            print(Colors.HIDE_CURSOR, end='')
            sys.stdout.flush()
            self.display_initialized = True
    
    def cleanup_display(self):
        """Cleanup display when visualization ends."""
        if self.display_initialized and self.colors_supported:
            print(Colors.SHOW_CURSOR, end='')
            sys.stdout.flush()
    
    def clear_screen(self):
        """Clear the console screen and move cursor to home."""
        if self.colors_supported:
            print('\033[2J\033[H', end='', flush=True)
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_ship_squares(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get all squares occupied by a ship."""
        start_x, start_y = start_pos
        end_x, end_y = end_pos
        
        if start_x == end_x:  # Vertical ship
            min_y, max_y = min(start_y, end_y), max(start_y, end_y)
            return [(start_x, y) for y in range(min_y, max_y + 1)]
        else:  # Horizontal ship
            min_x, max_x = min(start_x, end_x), max(start_x, end_x)
            return [(x, start_y) for x in range(min_x, max_x + 1)]
    
    def calculate_ship_stats(self, ships: List[Tuple[Tuple[int, int], Tuple[int, int]]], 
                           hits: Set[Tuple[int, int]]) -> Tuple[int, int, int]:
        """Calculate ship statistics.
        
        Returns:
            Tuple of (total_hits, ships_sunk, total_ship_squares)
        """
        total_hits = 0
        ships_sunk = 0
        total_ship_squares = 0
        
        for ship_start, ship_end in ships:
            ship_squares = self.get_ship_squares(ship_start, ship_end)
            total_ship_squares += len(ship_squares)
            
            ship_hits = sum(1 for pos in ship_squares if pos in hits)
            total_hits += ship_hits
            
            if ship_hits == len(ship_squares):
                ships_sunk += 1
        
        return total_hits, ships_sunk, total_ship_squares
    
    def display_board(self, player_name: str, ships: List[Tuple[Tuple[int, int], Tuple[int, int]]], 
                     hits: Set[Tuple[int, int]], shots_taken: List[Tuple[int, int]], 
                     show_ships: bool = True, stats_title: str = "Stats"):
        """Display a player's board state with colors and statistics.
        
        Args:
            player_name: Name of the player
            ships: List of ship positions
            hits: Set of positions that have been hit
            shots_taken: List of all shots taken at this board
            show_ships: Whether to show ship positions (for debugging/spectator view)
            stats_title: Title for the statistics section
        """
        # Color setup
        if self.colors_supported:
            title_color = Colors.BOLD + Colors.CYAN
            water_color = Colors.BLUE
            ship_color = Colors.GRAY
            hit_color = Colors.RED + Colors.BOLD
            miss_color = Colors.YELLOW
            reset = Colors.RESET
        else:
            title_color = ship_color = hit_color = miss_color = water_color = reset = ""
        
        print(f"\n{title_color}{player_name}'s Board:{reset}")
        
        # Get all ship squares
        ship_squares = set()
        if show_ships:
            for ship_start, ship_end in ships:
                ship_squares.update(self.get_ship_squares(ship_start, ship_end))
        
        # Calculate statistics
        total_hits, ships_sunk, total_ship_squares = self.calculate_ship_stats(ships, hits)
        total_shots = len(shots_taken)
        accuracy = (total_hits / total_shots * 100) if total_shots > 0 else 0
        
        # Prepare statistics lines
        stats_lines = [
            f"{stats_title}:",
            f"Shots: {total_shots}",
            f"Hits: {total_hits}",
            f"Ships Sunk: {ships_sunk}/{len(ships)}",
            f"Accuracy: {accuracy:.1f}%"
        ]
        
        # Create header with column numbers
        print("   ", end="")
        for x in range(self.board_size[0]):
            print(f"{x:2}", end="")
        print("    " + stats_lines[0] if len(stats_lines) > 0 else "")
        
        # Display each row with stats on the right
        for y in range(self.board_size[1]):
            print(f"{y:2} ", end="")
            for x in range(self.board_size[0]):
                pos = (x, y)
                if pos in hits:
                    if pos in ship_squares:
                        print(f" {hit_color}X{reset}", end="")  # Hit ship
                    else:
                        print(f" {miss_color}M{reset}", end="")  # Miss (shouldn't happen with proper game logic)
                elif pos in shots_taken:
                    print(f" {miss_color}M{reset}", end="")  # Miss
                elif show_ships and pos in ship_squares:
                    print(f" {ship_color}S{reset}", end="")  # Ship
                else:
                    print(f" {water_color}.{reset}", end="")  # Water
            
            # Add statistics on the right side
            if y + 1 < len(stats_lines):
                print(f"    {stats_lines[y + 1]}", end="")
            print()
    
    def display_game_state(self, bot1_name: str, bot2_name: str,
                          bot1_ships: List[Tuple[Tuple[int, int], Tuple[int, int]]],
                          bot2_ships: List[Tuple[Tuple[int, int], Tuple[int, int]]],
                          bot1_hits: Set[Tuple[int, int]], bot2_hits: Set[Tuple[int, int]],
                          bot1_shots: List[Tuple[int, int]], bot2_shots: List[Tuple[int, int]],
                          current_player: str, last_shot: Tuple[int, int] = None, 
                          last_result: ShotResponse = None):
        """Display the current game state with both boards."""
        if not self.display_initialized:
            self.init_display()
        self.clear_screen()
        
        # Color setup
        if self.colors_supported:
            header_color = Colors.BOLD + Colors.MAGENTA
            separator_color = Colors.CYAN
            legend_color = Colors.GRAY
            result_color = Colors.GREEN if last_result and last_result.result == ShotResult.HIT else Colors.YELLOW
            reset = Colors.RESET
        else:
            header_color = separator_color = legend_color = result_color = reset = ""
        
        print(f"{header_color}{'=' * 60}")
        print("BATTLESHIP GAME")
        print(f"{'=' * 60}{reset}")
        
        if last_shot and last_result:
            result_text = last_result.result.value.upper()
            if last_result.result == ShotResult.SUNK:
                result_text += f" (Ship length: {last_result.sunk_ship_length})"
            print(f"\n{current_player} shot at {last_shot}: {result_color}{result_text}{reset}")
        
        print(f"\n{legend_color}Legend: . = Water, S = Ship, X = Hit, M = Miss{reset}")
        
        # Display both boards side by side
        print(f"\n{separator_color}{'=' * 30} vs {'=' * 30}{reset}")
        
        # Bot1's board (what Bot2 is shooting at)
        self.display_board(bot1_name, bot1_ships, bot2_hits, bot2_shots, show_ships=True, 
                          stats_title=f"{bot2_name}'s Attack")
        
        print()
        
        # Bot2's board (what Bot1 is shooting at)  
        self.display_board(bot2_name, bot2_ships, bot1_hits, bot1_shots, show_ships=True,
                          stats_title=f"{bot1_name}'s Attack")
        
        print(f"\n{separator_color}{'=' * 60}{reset}")
        sys.stdout.flush()
    
    def display_winner(self, winner_name: str):
        """Display the game winner with celebration."""
        if self.colors_supported:
            winner_color = Colors.GREEN + Colors.BOLD
            reset = Colors.RESET
        else:
            winner_color = reset = ""
        
        print(f"\n{winner_color}🎉 Game Over! Winner: {winner_name} 🎉{reset}")
        sys.stdout.flush()
    
    def pause(self, duration: float = 1.0):
        """Pause for a specified duration to allow viewing of the current state."""
        time.sleep(duration)
    
    def __enter__(self):
        """Context manager entry."""
        self.init_display()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_display()