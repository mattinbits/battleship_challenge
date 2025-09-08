"""
Battleship game controller.

This module contains the game engine that manages matches between bots.
"""

import time
import os
from typing import List, Tuple, Set
from .interface import BattleshipBot, ShotResult, ShotResponse


class BattleshipGame:
    """Game controller that manages matches between two bots."""
    
    def __init__(self, bot1: BattleshipBot, bot2: BattleshipBot, 
                 board_size: Tuple[int, int] = (10, 10), 
                 ships: List[int] = [5, 4, 3, 3, 2],
                 visualize: bool = False):
        """Initialize a new battleship game.
        
        Args:
            bot1: First competing bot
            bot2: Second competing bot
            board_size: Size of the game board (width, height)
            ships: List of ship lengths for the game
            visualize: Whether to display the game visually
        """
        self.bot1 = bot1
        self.bot2 = bot2
        self.board_size = board_size
        self.ships = ships
        self.visualize = visualize
        self._bot1_ships = []
        self._bot2_ships = []
        self._bot1_hits = set()
        self._bot2_hits = set()
        self._bot1_shots_taken = []
        self._bot2_shots_taken = []
    
    def play_game(self) -> str:
        """Play a complete game between the two bots.
        
        Returns:
            The player_id of the winning bot
        """
        # Get ship placements from both bots
        self._bot1_ships = self.bot1.place_ships()
        self._bot2_ships = self.bot2.place_ships()
        
        # Validate ship placements
        self._validate_ship_placement(self._bot1_ships, self.bot1.player_id)
        self._validate_ship_placement(self._bot2_ships, self.bot2.player_id)
        
        # Show initial board state
        if self.visualize:
            self._display_game_state("Game Start")
            time.sleep(1.0)
        
        # Play the game by alternating shots
        current_bot = self.bot1
        current_ships = self._bot2_ships
        current_hits = self._bot1_hits
        current_shots = self._bot1_shots_taken
        
        while True:
            # Take shot
            shot = current_bot.take_shot()
            current_shots.append(shot)
            
            # Calculate result
            result = self._calculate_shot_result(shot, current_ships, current_hits)
            
            # Display the move
            if self.visualize:
                self._display_game_state(current_bot.player_id, shot, result)
                time.sleep(0.5)
            
            # Send result back to shooting bot
            current_bot.receive_shot_result(shot, result)
            
            # Check for game over
            if self._is_game_over(current_hits, current_ships):
                if self.visualize:
                    print(f"\n🎉 Game Over! Winner: {current_bot.player_id} 🎉")
                    time.sleep(2.0)
                return current_bot.player_id
            
            # Switch players
            if current_bot == self.bot1:
                current_bot = self.bot2
                current_ships = self._bot1_ships
                current_hits = self._bot2_hits
                current_shots = self._bot2_shots_taken
            else:
                current_bot = self.bot1
                current_ships = self._bot2_ships
                current_hits = self._bot1_hits
                current_shots = self._bot1_shots_taken
    
    def _validate_ship_placement(self, ships: List[Tuple[Tuple[int, int], Tuple[int, int]]], player_id: str):
        """Validate that ship placements are legal."""
        if len(ships) != len(self.ships):
            raise ValueError(f"Player {player_id} must place exactly {len(self.ships)} ships")
        
        occupied_squares = set()
        
        for i, ((start_x, start_y), (end_x, end_y)) in enumerate(ships):
            # Check bounds
            if not (0 <= start_x < self.board_size[0] and 0 <= start_y < self.board_size[1]):
                raise ValueError(f"Player {player_id} ship {i} start position out of bounds")
            if not (0 <= end_x < self.board_size[0] and 0 <= end_y < self.board_size[1]):
                raise ValueError(f"Player {player_id} ship {i} end position out of bounds")
            
            # Check ship is horizontal or vertical
            if start_x != end_x and start_y != end_y:
                raise ValueError(f"Player {player_id} ship {i} must be horizontal or vertical")
            
            # Calculate ship length and squares
            ship_squares = []
            if start_x == end_x:  # Vertical ship
                min_y, max_y = min(start_y, end_y), max(start_y, end_y)
                ship_squares = [(start_x, y) for y in range(min_y, max_y + 1)]
            else:  # Horizontal ship
                min_x, max_x = min(start_x, end_x), max(start_x, end_x)
                ship_squares = [(x, start_y) for x in range(min_x, max_x + 1)]
            
            # Check ship length
            expected_length = self.ships[i]
            if len(ship_squares) != expected_length:
                raise ValueError(f"Player {player_id} ship {i} has length {len(ship_squares)}, expected {expected_length}")
            
            # Check for overlaps
            for square in ship_squares:
                if square in occupied_squares:
                    raise ValueError(f"Player {player_id} ships overlap at {square}")
                occupied_squares.add(square)
    
    def _calculate_shot_result(self, shot: Tuple[int, int], target_ships: List[Tuple[Tuple[int, int], Tuple[int, int]]], hits: Set[Tuple[int, int]]) -> ShotResponse:
        """Calculate the result of a shot."""
        x, y = shot
        
        # Check if shot hits any ship
        for ship_start, ship_end in target_ships:
            ship_squares = self._get_ship_squares(ship_start, ship_end)
            if (x, y) in ship_squares:
                hits.add((x, y))
                
                # Check if ship is completely sunk
                if all(square in hits for square in ship_squares):
                    return ShotResponse(ShotResult.SUNK, len(ship_squares))
                else:
                    return ShotResponse(ShotResult.HIT)
        
        return ShotResponse(ShotResult.MISS)
    
    def _get_ship_squares(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get all squares occupied by a ship."""
        start_x, start_y = start_pos
        end_x, end_y = end_pos
        
        if start_x == end_x:  # Vertical ship
            min_y, max_y = min(start_y, end_y), max(start_y, end_y)
            return [(start_x, y) for y in range(min_y, max_y + 1)]
        else:  # Horizontal ship
            min_x, max_x = min(start_x, end_x), max(start_x, end_x)
            return [(x, start_y) for x in range(min_x, max_x + 1)]
    
    def _is_game_over(self, hits: Set[Tuple[int, int]], target_ships: List[Tuple[Tuple[int, int], Tuple[int, int]]]) -> bool:
        """Check if all ships have been sunk."""
        all_ship_squares = set()
        for ship_start, ship_end in target_ships:
            ship_squares = self._get_ship_squares(ship_start, ship_end)
            all_ship_squares.update(ship_squares)
        
        return all_ship_squares.issubset(hits)
    
    def _clear_screen(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _display_board(self, player_name: str, ships: List[Tuple[Tuple[int, int], Tuple[int, int]]], 
                      hits: Set[Tuple[int, int]], shots_taken: List[Tuple[int, int]], 
                      show_ships: bool = True):
        """Display a player's board state.
        
        Args:
            player_name: Name of the player
            ships: List of ship positions
            hits: Set of positions that have been hit
            shots_taken: List of all shots taken at this board
            show_ships: Whether to show ship positions (for debugging/spectator view)
        """
        print(f"\n{player_name}'s Board:")
        
        # Get all ship squares
        ship_squares = set()
        if show_ships:
            for ship_start, ship_end in ships:
                ship_squares.update(self._get_ship_squares(ship_start, ship_end))
        
        # Create header with column numbers
        print("   ", end="")
        for x in range(self.board_size[0]):
            print(f"{x:2}", end="")
        print()
        
        # Display each row
        for y in range(self.board_size[1]):
            print(f"{y:2} ", end="")
            for x in range(self.board_size[0]):
                pos = (x, y)
                if pos in hits:
                    if pos in ship_squares:
                        print(" X", end="")  # Hit ship
                    else:
                        print(" M", end="")  # Miss (shouldn't happen with proper game logic)
                elif pos in shots_taken:
                    print(" M", end="")  # Miss
                elif show_ships and pos in ship_squares:
                    print(" S", end="")  # Ship
                else:
                    print(" .", end="")  # Water
            print()
    
    def _display_game_state(self, current_player: str, last_shot: Tuple[int, int] = None, 
                           last_result: ShotResponse = None):
        """Display the current game state with both boards."""
        if not self.visualize:
            return
            
        self._clear_screen()
        print("=" * 60)
        print("BATTLESHIP GAME")
        print("=" * 60)
        
        if last_shot and last_result:
            result_text = last_result.result.value.upper()
            if last_result.result == ShotResult.SUNK:
                result_text += f" (Ship length: {last_result.sunk_ship_length})"
            print(f"\n{current_player} shot at {last_shot}: {result_text}")
        
        print("\nLegend: . = Water, S = Ship, X = Hit, M = Miss")
        
        # Display both boards side by side
        print("\n" + "=" * 30 + " vs " + "=" * 30)
        
        # Bot1's board (what Bot2 is shooting at)
        self._display_board(self.bot1.player_id, self._bot1_ships, self._bot2_hits, 
                           self._bot2_shots_taken, show_ships=True)
        
        print()
        
        # Bot2's board (what Bot1 is shooting at)  
        self._display_board(self.bot2.player_id, self._bot2_ships, self._bot1_hits,
                           self._bot1_shots_taken, show_ships=True)
        
        print("\n" + "=" * 60)