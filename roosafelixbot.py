from battleship_challenge.interface import BattleshipBot, ShotResponse, ShotResult
import random
from typing import List, Tuple, Set, Optional, Deque
from collections import deque


class RoosaFelixBot(BattleshipBot):
    def __init__(self, player_id, board_size, ships):
        super().__init__(player_id, board_size, ships)
        
        # Track game state
        self.shots_taken = set()
        self.hits = set()
        self.misses = set()
        self.sunk_ships = []
        
        # Hunt/Target mode variables
        self.target_queue = deque()  # Adjacent squares to try after a hit
        self.current_ship_hits = []  # Hits on the ship we're currently targeting
        self.mode = "hunt"  # "hunt" or "target"
        
        # Ship tracking
        self.remaining_ships = ships.copy()
        
        # Directions for adjacent squares: up, right, down, left
        self.directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    
    @property
    def name(self) -> str:
        return "RoosaFelixBot"
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Smart ship placement using edge preference and spacing."""
        placed_ships = []
        occupied = set()
        width, height = self.board_size
        
        # Sort ships by size (largest first)
        ships_to_place = sorted(self.ships, reverse=True)
        
        for ship_length in ships_to_place:
            placed = False
            attempts = 0
            max_attempts = 1000
            
            while not placed and attempts < max_attempts:
                attempts += 1
                
                # Random orientation: 0 = horizontal, 1 = vertical
                horizontal = random.choice([True, False])
                
                if horizontal:
                    # Horizontal placement
                    x = random.randint(0, width - ship_length)
                    y = random.randint(0, height - 1)
                    positions = [(x + i, y) for i in range(ship_length)]
                else:
                    # Vertical placement
                    x = random.randint(0, width - 1)
                    y = random.randint(0, height - ship_length)
                    positions = [(x, y + i) for i in range(ship_length)]
                
                # Check if placement is valid (no overlaps)
                if not any(pos in occupied for pos in positions):
                    start_pos = positions[0]
                    end_pos = positions[-1]
                    placed_ships.append((start_pos, end_pos))
                    occupied.update(positions)
                    placed = True
            
            if not placed:
                # Fallback: place ship anywhere valid
                for y in range(height):
                    for x in range(width - ship_length + 1):
                        positions = [(x + i, y) for i in range(ship_length)]
                        if not any(pos in occupied for pos in positions):
                            placed_ships.append(((x, y), (x + ship_length - 1, y)))
                            occupied.update(positions)
                            placed = True
                            break
                    if placed:
                        break
        
        return placed_ships
    
    def take_shot(self) -> Tuple[int, int]:
        """Smart targeting using hunt/target strategy."""
        width, height = self.board_size
        
        # Target mode: we have hits to follow up on
        if self.mode == "target" and self.target_queue:
            return self._target_mode_shot()
        
        # Hunt mode: look for ships using probability
        return self._hunt_mode_shot()
    
    def _target_mode_shot(self) -> Tuple[int, int]:
        """Target mode: systematically check around known hits."""
        while self.target_queue:
            x, y = self.target_queue.popleft()
            
            # If we have multiple hits, determine ship orientation
            if len(self.current_ship_hits) >= 2:
                return self._oriented_shot()
            
            # Add adjacent squares to target queue
            for dx, dy in self.directions:
                adj_x, adj_y = x + dx, y + dy
                if self._is_valid_shot(adj_x, adj_y):
                    return (adj_x, adj_y)
        
        # No more targets, switch back to hunt mode
        self.mode = "hunt"
        return self._hunt_mode_shot()
    
    def _oriented_shot(self) -> Tuple[int, int]:
        """Target along the determined ship orientation."""
        if len(self.current_ship_hits) < 2:
            return self._target_mode_shot()
        
        # Determine ship orientation
        sorted_hits = sorted(self.current_ship_hits)
        x1, y1 = sorted_hits[0]
        x2, y2 = sorted_hits[1]
        
        # Check if ship is horizontal or vertical
        if x1 == x2:  # Vertical ship
            # Try ends of the ship
            min_y = min(hit[1] for hit in self.current_ship_hits)
            max_y = max(hit[1] for hit in self.current_ship_hits)
            
            # Try shooting above and below
            candidates = [(x1, min_y - 1), (x1, max_y + 1)]
        else:  # Horizontal ship
            # Try ends of the ship
            min_x = min(hit[0] for hit in self.current_ship_hits)
            max_x = max(hit[0] for hit in self.current_ship_hits)
            
            # Try shooting left and right
            candidates = [(min_x - 1, y1), (max_x + 1, y1)]
        
        # Return first valid candidate
        for x, y in candidates:
            if self._is_valid_shot(x, y):
                return (x, y)
        
        # Fallback to regular target mode
        return self._target_mode_shot()
    
    def _hunt_mode_shot(self) -> Tuple[int, int]:
        """Hunt mode: use checkerboard pattern with probability."""
        width, height = self.board_size
        
        # First try checkerboard pattern (parity) to efficiently find ships
        best_shots = []
        
        for y in range(height):
            for x in range(width):
                if self._is_valid_shot(x, y):
                    # Checkerboard pattern (helps find ships faster)
                    if (x + y) % 2 == 0:
                        best_shots.append((x, y))
        
        # If we have checkerboard shots, take one
        if best_shots:
            return random.choice(best_shots)
        
        # Fallback: any valid shot
        for y in range(height):
            for x in range(width):
                if self._is_valid_shot(x, y):
                    return (x, y)
        
        # Should never reach here if game is valid
        return (0, 0)
    
    def _is_valid_shot(self, x: int, y: int) -> bool:
        """Check if a shot is valid (in bounds and not already taken)."""
        width, height = self.board_size
        return (0 <= x < width and 0 <= y < height and 
                (x, y) not in self.shots_taken)
    
    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        """Process shot result and update strategy."""
        self.shots_taken.add(shot)
        
        if result.result == ShotResult.HIT:
            self.hits.add(shot)
            self.current_ship_hits.append(shot)
            
            # Switch to target mode
            self.mode = "target"
            
            # Add adjacent squares to target queue if we don't have orientation yet
            if len(self.current_ship_hits) == 1:
                x, y = shot
                for dx, dy in self.directions:
                    adj_x, adj_y = x + dx, y + dy
                    if self._is_valid_shot(adj_x, adj_y):
                        self.target_queue.append((adj_x, adj_y))
        
        elif result.result == ShotResult.MISS:
            self.misses.add(shot)
        
        elif result.result == ShotResult.SUNK:
            self.hits.add(shot)
            self.current_ship_hits.append(shot)
            
            # Ship sunk - record it and reset targeting
            if result.sunk_ship_length:
                self.sunk_ships.append(result.sunk_ship_length)
                if result.sunk_ship_length in self.remaining_ships:
                    self.remaining_ships.remove(result.sunk_ship_length)
            
            # Reset targeting state
            self.current_ship_hits = []
            self.target_queue.clear()
            self.mode = "hunt"
