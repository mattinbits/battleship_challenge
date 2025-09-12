"""
A bot that intentionally fails to test error handling.
"""

from typing import List, Tuple
from ..interface import BattleshipBot, ShotResponse


class FailingBotBase(BattleshipBot):
    """Base class for failing bots."""
    
    def _get_valid_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Return valid ship placements."""
        return [
            ((0, 0), (0, 4)),  # 5-length ship
            ((2, 0), (2, 3)),  # 4-length ship
            ((4, 0), (4, 2)),  # 3-length ship
            ((6, 0), (6, 2)),  # 3-length ship
            ((8, 0), (8, 1)),  # 2-length ship
        ]


class ShipPlacementExceptionBot(FailingBotBase):
    """Bot that throws exception during ship placement."""
    
    @property
    def name(self) -> str:
        return "ShipPlacementExceptionBot"
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        raise RuntimeError("Ship placement failed!")
    
    def take_shot(self) -> Tuple[int, int]:
        return (0, 0)
    
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        pass


class IllegalShipPlacementBot(FailingBotBase):
    """Bot that makes illegal ship placements."""
    
    @property
    def name(self) -> str:
        return "IllegalShipPlacementBot"
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        # Return overlapping ships
        return [((0, 0), (0, 4)), ((0, 0), (0, 3)), ((0, 0), (0, 2)), ((0, 0), (0, 2)), ((0, 0), (0, 1))]
    
    def take_shot(self) -> Tuple[int, int]:
        return (0, 0)
    
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        pass


class ShotExceptionBot(FailingBotBase):
    """Bot that throws exception when taking shots."""
    
    @property
    def name(self) -> str:
        return "ShotExceptionBot"
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        return self._get_valid_ships()
    
    def take_shot(self) -> Tuple[int, int]:
        raise RuntimeError("Shot selection failed!")
    
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        pass


class IllegalShotBot(FailingBotBase):
    """Bot that makes illegal shots."""
    
    @property
    def name(self) -> str:
        return "IllegalShotBot"
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        return self._get_valid_ships()
    
    def take_shot(self) -> Tuple[int, int]:
        return (-1, -1)  # Out of bounds
    
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        pass


class ResultExceptionBot(FailingBotBase):
    """Bot that throws exception when receiving results."""
    
    @property
    def name(self) -> str:
        return "ResultExceptionBot"
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        return self._get_valid_ships()
    
    def take_shot(self) -> Tuple[int, int]:
        return (0, 0)
    
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        raise RuntimeError("Result processing failed!")