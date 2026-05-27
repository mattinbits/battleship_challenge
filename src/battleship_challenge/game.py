"""
Battleship game controller.

This module contains the game engine that manages matches between bots.
"""

import time
from typing import List, Tuple, Set
from .interface import BattleshipBot, ShotResult, ShotResponse
from .visualization import BattleshipVisualizer


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
        self._visualizer = BattleshipVisualizer(board_size) if visualize else None
        
        # Create display names with collision handling
        self.bot1_display_name = bot1.name
        self.bot2_display_name = bot2.name
        if self.bot1_display_name == self.bot2_display_name:
            self.bot1_display_name += " (1)"
            self.bot2_display_name += " (2)"
    
    def play_game(self) -> str:
        """Play a complete game between the two bots.
        
        Returns:
            The player_id of the winning bot
        """
        # Get ship placements from both bots with error handling
        try:
            self._bot1_ships = self.bot1.place_ships()
        except Exception as e:
            print(f"Bot {self.bot1.player_id} failed during ship placement: {e}")
            return self.bot2.player_id
            
        try:
            self._bot2_ships = self.bot2.place_ships()
        except Exception as e:
            print(f"Bot {self.bot2.player_id} failed during ship placement: {e}")
            return self.bot1.player_id
        
        # Validate ship placements
        try:
            self._validate_ship_placement(self._bot1_ships, self.bot1.player_id)
        except (ValueError, TypeError) as e:
            print(f"Bot {self.bot1.player_id} made illegal ship placement: {e}")
            return self.bot2.player_id
            
        try:
            self._validate_ship_placement(self._bot2_ships, self.bot2.player_id)
        except (ValueError, TypeError) as e:
            print(f"Bot {self.bot2.player_id} made illegal ship placement: {e}")
            return self.bot1.player_id
        
        # Initialize display and show initial board state
        if self.visualize:
            self._visualizer.init_display()
            self._display_game_state("Game Start")
            time.sleep(1.0)
        
        # Play the game by alternating shots
        current_bot = self.bot1
        current_ships = self._bot2_ships
        current_hits = self._bot1_hits
        current_shots = self._bot1_shots_taken
        
        while True:
            # Take shot with error handling
            try:
                shot = current_bot.take_shot()
            except Exception as e:
                print(f"Bot {current_bot.player_id} failed during shot selection: {e}")
                # Current bot loses, return the other bot's id
                if current_bot == self.bot1:
                    return self.bot2.player_id
                else:
                    return self.bot1.player_id
            
            # Validate shot coordinates
            try:
                self._validate_shot(shot, current_shots)
            except (ValueError, TypeError) as e:
                print(f"Bot {current_bot.player_id} made illegal shot {shot}: {e}")
                # Current bot loses, return the other bot's id
                if current_bot == self.bot1:
                    return self.bot2.player_id
                else:
                    return self.bot1.player_id
                    
            current_shots.append(shot)
            
            # Calculate result
            result = self._calculate_shot_result(shot, current_ships, current_hits)
            
            # Display the move
            if self.visualize:
                current_display_name = self.bot1_display_name if current_bot == self.bot1 else self.bot2_display_name
                self._display_game_state(current_display_name, shot, result)
                time.sleep(0.5)
            
            # Send result back to shooting bot with error handling
            try:
                current_bot.receive_shot_result(shot, result)
            except Exception as e:
                print(f"Bot {current_bot.player_id} failed during result processing: {e}")
                # Current bot loses, return the other bot's id
                if current_bot == self.bot1:
                    return self.bot2.player_id
                else:
                    return self.bot1.player_id
            
            # Check for game over
            if self._is_game_over(current_hits, current_ships):
                if self.visualize:
                    winner_display_name = self.bot1_display_name if current_bot == self.bot1 else self.bot2_display_name
                    self._visualizer.display_winner(winner_display_name)
                    self._visualizer.cleanup_display()
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
    
    def _validate_shot(self, shot: Tuple[int, int], shots_taken: list = None):
        """Validate that a shot is legal."""
        if not isinstance(shot, tuple) or len(shot) != 2:
            raise ValueError("Shot must be a tuple of two integers")

        x, y = shot

        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("Shot coordinates must be integers")

        if not (0 <= x < self.board_size[0]):
            raise ValueError(f"Shot x-coordinate {x} is out of bounds (0-{self.board_size[0]-1})")

        if not (0 <= y < self.board_size[1]):
            raise ValueError(f"Shot y-coordinate {y} is out of bounds (0-{self.board_size[1]-1})")

        if shots_taken is not None and shot in shots_taken:
            raise ValueError(f"Shot at {shot} has already been fired")
    
    def _validate_ship_placement(self, ships: List[Tuple[Tuple[int, int], Tuple[int, int]]], player_id: str):
        """Validate that ship placements are legal."""
        if len(ships) != len(self.ships):
            raise ValueError(f"Player {player_id} must place exactly {len(self.ships)} ships")

        occupied_squares = set()
        ship_lengths = []

        for i, ((start_x, start_y), (end_x, end_y)) in enumerate(ships):
            # Check bounds
            if not (0 <= start_x < self.board_size[0] and 0 <= start_y < self.board_size[1]):
                raise ValueError(f"Player {player_id} ship {i} start position out of bounds")
            if not (0 <= end_x < self.board_size[0] and 0 <= end_y < self.board_size[1]):
                raise ValueError(f"Player {player_id} ship {i} end position out of bounds")

            # Check ship is horizontal or vertical
            if start_x != end_x and start_y != end_y:
                raise ValueError(f"Player {player_id} ship {i} must be horizontal or vertical")

            # Calculate ship squares
            if start_x == end_x:  # Vertical ship
                min_y, max_y = min(start_y, end_y), max(start_y, end_y)
                ship_squares = [(start_x, y) for y in range(min_y, max_y + 1)]
            else:  # Horizontal ship
                min_x, max_x = min(start_x, end_x), max(start_x, end_x)
                ship_squares = [(x, start_y) for x in range(min_x, max_x + 1)]

            ship_lengths.append(len(ship_squares))

            # Check for overlaps
            for square in ship_squares:
                if square in occupied_squares:
                    raise ValueError(f"Player {player_id} ships overlap at {square}")
                occupied_squares.add(square)

        # Validate ship lengths as a multiset (order-independent)
        if sorted(ship_lengths) != sorted(self.ships):
            raise ValueError(
                f"Player {player_id} ship lengths {sorted(ship_lengths)} do not match required {sorted(self.ships)}"
            )
    
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
    
    def _display_game_state(self, current_player: str, last_shot: Tuple[int, int] = None, 
                           last_result: ShotResponse = None):
        """Display the current game state with both boards."""
        if not self.visualize:
            return
            
        self._visualizer.display_game_state(
            self.bot1_display_name, self.bot2_display_name,
            self._bot1_ships, self._bot2_ships,
            self._bot1_hits, self._bot2_hits,
            self._bot1_shots_taken, self._bot2_shots_taken,
            current_player, last_shot, last_result
        )