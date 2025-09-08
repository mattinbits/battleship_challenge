"""
Battleship bot interface for coding challenge.

This module defines the interface that competing bots must implement
to participate in the battleship challenge.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Tuple, Optional
from dataclasses import dataclass


class ShotResult(Enum):
    """Result of a shot fired at the opponent's board."""
    MISS = "miss"
    HIT = "hit" 
    SUNK = "sunk"  # hit + ship completely destroyed


@dataclass
class ShotResponse:
    """Response containing the result of a shot."""
    result: ShotResult
    sunk_ship_length: Optional[int] = None  # only if result == SUNK


class BattleshipBot(ABC):
    """Abstract base class for battleship bots.
    
    Competing teams must implement this interface for their bot.
    """
    
    def __init__(self, player_id: str, board_size: Tuple[int, int], ships: List[int]):
        """Initialize the bot.
        
        Args:
            player_id: Unique identifier for this bot
            board_size: (width, height) of the game board
            ships: List of ship lengths to place (e.g., [5, 4, 3, 3, 2])
        """
        self.player_id = player_id
        self.board_size = board_size
        self.ships = ships
    
    @abstractmethod
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Place ships on the board.
        
        Returns:
            List of ships as (start_pos, end_pos) tuples
            e.g., [((0,0), (0,4)), ((2,1), (5,1))] for vertical 5-ship and horizontal 4-ship
        """
        pass
    
    @abstractmethod
    def take_shot(self) -> Tuple[int, int]:
        """Choose where to shoot.
        
        Returns:
            (x, y) coordinates to shoot at
        """
        pass
    
    @abstractmethod
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        """Receive the result of your shot.
        
        Use this to update your tracking/probability maps.
        
        Args:
            shot: The (x, y) coordinates you shot at
            result: The result of your shot
        """
        pass