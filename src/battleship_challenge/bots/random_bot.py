"""
Random bot implementation for battleship.

This bot makes completely random but legal moves. It serves as a
baseline implementation and example for teams.
"""

import random
from typing import List, Tuple, Set
from ..interface import BattleshipBot, ShotResponse


class RandomBot(BattleshipBot):
    """A bot that makes random but legal moves."""
    
    def __init__(self, player_id: str, board_size: Tuple[int, int], ships: List[int]):
        super().__init__(player_id, board_size, ships)
        self.shots_taken: Set[Tuple[int, int]] = set()
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Place ships randomly on the board."""
        placed_ships = []
        occupied_squares = set()
        
        for ship_length in self.ships:
            attempts = 0
            max_attempts = 1000
            
            while attempts < max_attempts:
                # Choose random orientation
                horizontal = random.choice([True, False])
                
                if horizontal:
                    # Horizontal ship
                    start_x = random.randint(0, self.board_size[0] - ship_length)
                    start_y = random.randint(0, self.board_size[1] - 1)
                    end_x = start_x + ship_length - 1
                    end_y = start_y
                else:
                    # Vertical ship
                    start_x = random.randint(0, self.board_size[0] - 1)
                    start_y = random.randint(0, self.board_size[1] - ship_length)
                    end_x = start_x
                    end_y = start_y + ship_length - 1
                
                # Check if placement is valid (no overlaps)
                ship_squares = self._get_ship_squares((start_x, start_y), (end_x, end_y))
                if not any(square in occupied_squares for square in ship_squares):
                    # Valid placement
                    placed_ships.append(((start_x, start_y), (end_x, end_y)))
                    occupied_squares.update(ship_squares)
                    break
                
                attempts += 1
            
            if attempts >= max_attempts:
                # Fallback: place ship in first available horizontal position
                placed_ships.append(self._place_ship_fallback(ship_length, occupied_squares))
        
        return placed_ships
    
    def take_shot(self) -> Tuple[int, int]:
        """Take a random shot at an unshot square."""
        available_squares = []
        for x in range(self.board_size[0]):
            for y in range(self.board_size[1]):
                if (x, y) not in self.shots_taken:
                    available_squares.append((x, y))
        
        if not available_squares:
            # This shouldn't happen in a normal game, but just in case
            return (0, 0)
        
        shot = random.choice(available_squares)
        self.shots_taken.add(shot)
        return shot
    
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        """Receive shot result. Random bot doesn't use this information."""
        pass
    
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
    
    def _place_ship_fallback(self, ship_length: int, occupied_squares: Set[Tuple[int, int]]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Fallback method to place a ship when random placement fails."""
        # Try to find the first available horizontal position
        for y in range(self.board_size[1]):
            for x in range(self.board_size[0] - ship_length + 1):
                ship_squares = [(x + i, y) for i in range(ship_length)]
                if not any(square in occupied_squares for square in ship_squares):
                    occupied_squares.update(ship_squares)
                    return ((x, y), (x + ship_length - 1, y))
        
        # Try vertical if horizontal doesn't work
        for x in range(self.board_size[0]):
            for y in range(self.board_size[1] - ship_length + 1):
                ship_squares = [(x, y + i) for i in range(ship_length)]
                if not any(square in occupied_squares for square in ship_squares):
                    occupied_squares.update(ship_squares)
                    return ((x, y), (x, y + ship_length - 1))
        
        # This should never happen with proper board size and ship configuration
        raise RuntimeError(f"Unable to place ship of length {ship_length}")