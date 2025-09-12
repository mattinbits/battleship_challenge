from battleship_challenge.interface import BattleshipBot, ShotResponse, ShotResult
import random
from typing import List, Tuple, Set, Optional, Deque
from collections import deque


class RoosaFelixBot(BattleshipBot):
    def __init__(self, player_id, board_size, ships):
        super().__init__(player_id, board_size, ships)
        
        # ===== TUNABLE PARAMETERS FOR EXPERIMENTATION =====
        
        # Hunt Strategy Parameters
        self.HUNT_PARITY = 0  # 0 or 1 for checkerboard pattern (try both!)
        self.USE_PROBABILITY_DENSITY = True  # Weight shots by ship probability
        self.MIN_SHIP_SIZE_FILTER = True  # Only target areas fitting remaining ships
        
        # Ship Placement Parameters  
        self.EDGE_BIAS = 0.5  # 0.0=center bias, 1.0=edge bias (try 0.3, 0.7)
        self.SPACING_BUFFER = 0  # Minimum squares between ships (try 1, 2)
        self.ORIENTATION_BIAS = 0.5  # 0.0=horizontal bias, 1.0=vertical bias
        
        # Target Strategy Parameters
        self.DIRECTION_PRIORITY = "smart"  # "sequential", "random", "smart"
        self.TARGET_QUEUE_STRATEGY = "depth_first"  # "breadth_first", "depth_first"
        self.AGGRESSIVE_TARGETING = True  # Prioritize completing ships over hunting new ones
        self.MAX_TARGET_ATTEMPTS = 8  # Max shots to try around a hit before giving up
        self.SMART_DIRECTION_BIAS = True  # Bias toward center/open areas when targeting
        self.PERSIST_ON_LINE = True  # Keep shooting in same direction after multiple hits
        
        # ===== END TUNABLE PARAMETERS =====
        
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
    
    def tune_parameters(self, **kwargs):
        """Tune bot parameters for experimentation.
        
        Usage examples:
        bot.tune_parameters(HUNT_PARITY=1, EDGE_BIAS=0.3)
        bot.tune_parameters(USE_PROBABILITY_DENSITY=True, MIN_SHIP_SIZE_FILTER=False)
        """
        for param, value in kwargs.items():
            if hasattr(self, param):
                setattr(self, param, value)
                print(f"Set {param} = {value}")
            else:
                print(f"Warning: Parameter {param} not found")
    
    def get_current_parameters(self) -> dict:
        """Get current parameter settings for analysis."""
        return {
            'HUNT_PARITY': self.HUNT_PARITY,
            'USE_PROBABILITY_DENSITY': self.USE_PROBABILITY_DENSITY,
            'MIN_SHIP_SIZE_FILTER': self.MIN_SHIP_SIZE_FILTER,
            'EDGE_BIAS': self.EDGE_BIAS,
            'SPACING_BUFFER': self.SPACING_BUFFER,
            'ORIENTATION_BIAS': self.ORIENTATION_BIAS,
            'DIRECTION_PRIORITY': self.DIRECTION_PRIORITY,
            'TARGET_QUEUE_STRATEGY': self.TARGET_QUEUE_STRATEGY,
            'AGGRESSIVE_TARGETING': self.AGGRESSIVE_TARGETING,
            'MAX_TARGET_ATTEMPTS': self.MAX_TARGET_ATTEMPTS,
            'SMART_DIRECTION_BIAS': self.SMART_DIRECTION_BIAS,
            'PERSIST_ON_LINE': self.PERSIST_ON_LINE,
        }
    
    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Smart ship placement using configurable edge preference and spacing."""
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
                
                # Use orientation bias
                horizontal = random.random() < (1.0 - self.ORIENTATION_BIAS)
                
                if horizontal:
                    # Horizontal placement with edge bias
                    if random.random() < self.EDGE_BIAS:
                        # Prefer edges
                        y = random.choice([0, height - 1]) if random.random() < 0.5 else random.randint(1, height - 2)
                    else:
                        y = random.randint(0, height - 1)
                    x = random.randint(0, width - ship_length)
                    positions = [(x + i, y) for i in range(ship_length)]
                else:
                    # Vertical placement with edge bias
                    if random.random() < self.EDGE_BIAS:
                        # Prefer edges
                        x = random.choice([0, width - 1]) if random.random() < 0.5 else random.randint(1, width - 2)
                    else:
                        x = random.randint(0, width - 1)
                    y = random.randint(0, height - ship_length)
                    positions = [(x, y + i) for i in range(ship_length)]
                
                # Check if placement is valid (no overlaps + spacing buffer)
                valid = True
                for pos in positions:
                    if pos in occupied:
                        valid = False
                        break
                    
                    # Check spacing buffer
                    if self.SPACING_BUFFER > 0:
                        for dx in range(-self.SPACING_BUFFER, self.SPACING_BUFFER + 1):
                            for dy in range(-self.SPACING_BUFFER, self.SPACING_BUFFER + 1):
                                check_pos = (pos[0] + dx, pos[1] + dy)
                                if check_pos in occupied:
                                    valid = False
                                    break
                            if not valid:
                                break
                    if not valid:
                        break
                
                if valid:
                    start_pos = positions[0]
                    end_pos = positions[-1]
                    placed_ships.append((start_pos, end_pos))
                    occupied.update(positions)
                    placed = True
            
            if not placed:
                # Fallback: place ship anywhere valid (ignore spacing for fallback)
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
        
        # If we have multiple hits and persistence is enabled, try line continuation first
        if len(self.current_ship_hits) >= 2 and self.PERSIST_ON_LINE:
            oriented_shot = self._oriented_shot()
            if oriented_shot:
                return oriented_shot
        
        # Use target queue with proper strategy
        if self.target_queue:
            if self.TARGET_QUEUE_STRATEGY == "depth_first":
                x, y = self.target_queue.pop()  # Take from end (last added)
            else:  # breadth_first
                x, y = self.target_queue.popleft()  # Take from front (first added)
            
            if self._is_valid_shot(x, y):
                return (x, y)
            # If shot invalid, try next in queue
            return self._target_mode_shot()
        
        # No more targets, switch back to hunt mode
        self.mode = "hunt"
        return self._hunt_mode_shot()
    
    def _get_prioritized_directions(self) -> List[Tuple[int, int]]:
        """Get directions based on priority strategy."""
        base_directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # up, right, down, left
        
        if self.DIRECTION_PRIORITY == "random":
            directions = base_directions.copy()
            random.shuffle(directions)
            return directions
        elif self.DIRECTION_PRIORITY == "smart":
            # Prioritize directions toward center of board
            width, height = self.board_size
            center_x, center_y = width // 2, height // 2
            # For now, just use sequential - could add center-seeking logic
            return base_directions
        else:  # "sequential"
            return base_directions
    
    def _oriented_shot(self) -> Optional[Tuple[int, int]]:
        """Target along the determined ship orientation with improved logic."""
        if len(self.current_ship_hits) < 2:
            return None
        
        # Determine ship orientation
        sorted_hits = sorted(self.current_ship_hits)
        
        # Check if all hits are in a line (horizontal or vertical)
        is_horizontal = all(hit[1] == sorted_hits[0][1] for hit in self.current_ship_hits)
        is_vertical = all(hit[0] == sorted_hits[0][0] for hit in self.current_ship_hits)
        
        if not (is_horizontal or is_vertical):
            # Hits not in a line - fall back to target queue
            return None
            
        candidates = []
        
        if is_vertical:  # Vertical ship
            x = sorted_hits[0][0]
            min_y = min(hit[1] for hit in self.current_ship_hits)
            max_y = max(hit[1] for hit in self.current_ship_hits)
            
            # Prioritize extending the line
            candidates = [(x, min_y - 1), (x, max_y + 1)]
            
        elif is_horizontal:  # Horizontal ship
            y = sorted_hits[0][1]
            min_x = min(hit[0] for hit in self.current_ship_hits)
            max_x = max(hit[0] for hit in self.current_ship_hits)
            
            # Prioritize extending the line
            candidates = [(min_x - 1, y), (max_x + 1, y)]
        
        # Apply smart direction bias if enabled
        if self.SMART_DIRECTION_BIAS:
            candidates = self._bias_toward_open_area(candidates)
        
        # Return first valid candidate
        for x, y in candidates:
            if self._is_valid_shot(x, y):
                return (x, y)
        
        return None

    def _bias_toward_open_area(self, candidates: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Bias candidate shots toward more open areas of the board."""
        width, height = self.board_size
        center_x, center_y = width // 2, height // 2
        
        # Sort by distance from center (closer to center = more open area typically)
        def distance_from_center(pos):
            x, y = pos
            return abs(x - center_x) + abs(y - center_y)
        
        return sorted(candidates, key=distance_from_center)

    def _hunt_mode_shot(self) -> Tuple[int, int]:
        """Hunt mode: use configurable pattern with probability."""
        width, height = self.board_size
        
        # Try checkerboard pattern with configurable parity
        best_shots = []
        
        for y in range(height):
            for x in range(width):
                if self._is_valid_shot(x, y):
                    # Configurable checkerboard pattern
                    if (x + y) % 2 == self.HUNT_PARITY:
                        # Filter by minimum ship size if enabled
                        if not self.MIN_SHIP_SIZE_FILTER or self._can_fit_ship(x, y):
                            best_shots.append((x, y))
        
        # If we have pattern shots, take one
        if best_shots:
            if self.USE_PROBABILITY_DENSITY:
                return self._weighted_shot_selection(best_shots)
            else:
                return random.choice(best_shots)
        
        # Fallback: any valid shot
        for y in range(height):
            for x in range(width):
                if self._is_valid_shot(x, y):
                    return (x, y)
        
        # Should never reach here if game is valid
        return (0, 0)
    
    def _can_fit_ship(self, x: int, y: int) -> bool:
        """Check if any remaining ship can fit starting from this position."""
        if not self.remaining_ships:
            return True
            
        min_ship_size = min(self.remaining_ships)
        width, height = self.board_size
        
        # Check horizontal fit
        horizontal_fit = True
        for i in range(min_ship_size):
            if x + i >= width or (x + i, y) in self.shots_taken:
                horizontal_fit = False
                break
        
        # Check vertical fit  
        vertical_fit = True
        for i in range(min_ship_size):
            if y + i >= height or (x, y + i) in self.shots_taken:
                vertical_fit = False
                break
                
        return horizontal_fit or vertical_fit
    
    def _weighted_shot_selection(self, candidates: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Select shot based on probability density (placeholder for advanced logic)."""
        # For now, just return random - could implement heat map logic here
        return random.choice(candidates)
    
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
            
            # Add adjacent squares to target queue strategically
            if self.AGGRESSIVE_TARGETING:
                self._add_strategic_targets(shot)
            else:
                # Original simple logic
                if len(self.current_ship_hits) == 1:
                    self._add_adjacent_targets(shot)
        
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

    def _add_strategic_targets(self, shot: Tuple[int, int]):
        """Add targets around a hit using strategic prioritization."""
        x, y = shot
        
        # If this is our first hit on this ship, add all adjacent squares
        if len(self.current_ship_hits) == 1:
            self._add_adjacent_targets(shot)
        elif len(self.current_ship_hits) >= 2:
            # We have orientation info - prioritize line extension
            oriented_shot = self._oriented_shot()
            if oriented_shot and oriented_shot not in [pos for pos in self.target_queue]:
                # Add oriented shot to front of queue for immediate attention
                if self.TARGET_QUEUE_STRATEGY == "depth_first":
                    self.target_queue.append(oriented_shot)
                else:
                    self.target_queue.appendleft(oriented_shot)
    
    def _add_adjacent_targets(self, shot: Tuple[int, int]):
        """Add adjacent squares to target queue with direction priority."""
        x, y = shot
        directions = self._get_prioritized_directions()
        
        for dx, dy in directions:
            adj_x, adj_y = x + dx, y + dy
            if self._is_valid_shot(adj_x, adj_y):
                # Avoid duplicates
                if (adj_x, adj_y) not in self.target_queue:
                    self.target_queue.append((adj_x, adj_y))
