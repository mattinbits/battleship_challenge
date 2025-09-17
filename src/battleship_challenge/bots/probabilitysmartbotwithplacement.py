import random
from typing import List, Tuple, Set, Optional
from ..interface import BattleshipBot, ShotResponse, ShotResult

class ProbabilitySmartBotWithPlacement(BattleshipBot):
    """
    Battleship bot that uses:
    1. Probability density search in hunting mode.
    2. Directional targeting in destroy mode.
    3. Ship-size-based elimination of impossible cells.
    """

    def __init__(self, player_id: str, board_size: Tuple[int, int], ships: List[int]):
        super().__init__(player_id, board_size, ships)

        self.shots_taken: Set[Tuple[int, int]] = set()
        self.known_hits: Set[Tuple[int, int]] = set()
        self.known_misses: Set[Tuple[int, int]] = set()

        self.mode = "search"
        self.current_hits: List[Tuple[int, int]] = []
        self.target_candidates: List[Tuple[int, int]] = []
        self.destroy_direction: Optional[Tuple[int, int]] = None

        self.remaining_ships = list(self.ships)

    @property
    def name(self) -> str:
        return "ProbabilitySmartBotWithPlacement"

    def place_ships(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Place ships using anti-parity + spread-out strategy."""
        placed_ships = []
        occupied = set()

        # Slight bias toward placing bigger ships first
        ships_sorted = sorted(self.ships, reverse=True)

        for ship_length in ships_sorted:
            best_positions = self._generate_candidate_positions(ship_length)

            # Try to pick one that maximizes distance to other ships
            placed = False
            random.shuffle(best_positions)
            best_positions.sort(key=lambda pos: self._min_distance_to_existing(pos, occupied), reverse=True)

            for start_pos, end_pos in best_positions:
                squares = self._get_ship_squares(start_pos, end_pos)
                if not any(s in occupied for s in squares):
                    placed_ships.append((start_pos, end_pos))
                    occupied.update(squares)
                    placed = True
                    break

            if not placed:
                # fallback to default random placement if something fails
                placed_ships.append(self._random_fallback(ship_length, occupied))

        return placed_ships

    def _generate_candidate_positions(self, length: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Generate candidate positions matching anti-parity + orientation rules."""
        candidates = []
        orientations = ["H"] * 6 + ["V"] * 4  # ~60/40 split
        for orient in orientations:
            for _ in range(100):  # sample positions
                if orient == "H":
                    # Place so it crosses both parities
                    start_x = random.randint(0, self.board_size[0] - length)
                    start_y = random.randint(0, self.board_size[1] - 1)
                    # Ensure mix of edges and middle
                    if random.random() < 0.5:
                        start_y = random.choice([0, self.board_size[1] - 1])
                    end_x = start_x + length - 1
                    end_y = start_y
                else:
                    start_x = random.randint(0, self.board_size[0] - 1)
                    start_y = random.randint(0, self.board_size[1] - length)
                    if random.random() < 0.5:
                        start_x = random.choice([0, self.board_size[0] - 1])
                    end_x = start_x
                    end_y = start_y + length - 1

                squares = self._get_ship_squares((start_x, start_y), (end_x, end_y))
                # parity break: make sure we don't sit fully inside one parity color
                parities = {(x + y) % 2 for x, y in squares}
                if len(parities) > 1:
                    candidates.append(((start_x, start_y), (end_x, end_y)))
        return candidates

    def _min_distance_to_existing(self, placement: Tuple[Tuple[int, int], Tuple[int, int]], occupied: set) -> float:
        """Measure the min Manhattan distance from this placement to existing ships."""
        ship_cells = self._get_ship_squares(placement[0], placement[1])
        min_dist = 999
        for x, y in ship_cells:
            for ox, oy in occupied:
                dist = abs(x - ox) + abs(y - oy)
                if dist < min_dist:
                    min_dist = dist
        return min_dist if occupied else 999

    def _random_fallback(self, ship_length: int, occupied: set):
        """Fallback random placement for emergencies."""
        while True:
            horizontal = random.choice([True, False])
            if horizontal:
                start_x = random.randint(0, self.board_size[0] - ship_length)
                start_y = random.randint(0, self.board_size[1] - 1)
                end_x = start_x + ship_length - 1
                end_y = start_y
            else:
                start_x = random.randint(0, self.board_size[0] - 1)
                start_y = random.randint(0, self.board_size[1] - ship_length)
                end_x = start_x
                end_y = start_y + ship_length - 1
            squares = self._get_ship_squares((start_x, start_y), (end_x, end_y))
            if not any(s in occupied for s in squares):
                occupied.update(squares)
                return ((start_x, start_y), (end_x, end_y))

    def take_shot(self) -> Tuple[int, int]:
        if self.mode == "search":
            shot = self._best_probability_shot()
            self.shots_taken.add(shot)
            return shot

        elif self.mode == "target":
            while self.target_candidates:
                shot = self.target_candidates.pop(0)
                if self._is_valid_shot(shot):
                    self.shots_taken.add(shot)
                    return shot
            self.mode = "search"
            return self.take_shot()

        elif self.mode == "destroy":
            shot = self._next_in_destroy_direction()
            if shot:
                self.shots_taken.add(shot)
                return shot
            self.mode = "target"
            return self.take_shot()

        return self._random_unshot_square()

    def receive_shot_result(self, shot: Tuple[int, int], result: ShotResponse):
        if result.result == ShotResult.HIT:
            self.known_hits.add(shot)
            self.current_hits.append(shot)
            if self.mode == "search":
                self.mode = "target"
                self.target_candidates = self._get_neighbours(shot)
            elif self.mode == "target" and len(self.current_hits) >= 2:
                self.destroy_direction = self._find_direction()
                self.mode = "destroy"
        elif result.result == ShotResult.SUNK:
            self.known_hits.add(shot)
            self._remove_sunk_ship(result.sunk_ship_length)
            self.current_hits.clear()
            self.destroy_direction = None
            self.target_candidates.clear()
            self.mode = "search"
        elif result.result == ShotResult.MISS:
            self.known_misses.add(shot)
            if self.mode == "destroy":
                if self.destroy_direction:
                    dx, dy = self.destroy_direction
                    self.destroy_direction = (-dx, -dy)
                else:
                    self.mode = "target"

    # -------------------------------------------------------------------------
    # Probability Calculation
    # -------------------------------------------------------------------------
    def _best_probability_shot(self) -> Tuple[int, int]:
        """Choose unshot cell with highest probability given remaining ships."""
        prob_map = [[0] * self.board_size[1] for _ in range(self.board_size[0])]
        for length in self.remaining_ships:
            # Horizontal placements
            for x in range(self.board_size[0] - length + 1):
                for y in range(self.board_size[1]):
                    coords = [(x + i, y) for i in range(length)]
                    if self._placement_valid(coords):
                        for cx, cy in coords:
                            prob_map[cx][cy] += 1
            # Vertical placements
            for x in range(self.board_size[0]):
                for y in range(self.board_size[1] - length + 1):
                    coords = [(x, y + i) for i in range(length)]
                    if self._placement_valid(coords):
                        for cx, cy in coords:
                            prob_map[cx][cy] += 1
        # Pick max prob cell
        best_cells = []
        max_prob = 0
        for x in range(self.board_size[0]):
            for y in range(self.board_size[1]):
                if (x, y) not in self.shots_taken and prob_map[x][y] > max_prob:
                    max_prob = prob_map[x][y]
                    best_cells = [(x, y)]
                elif (x, y) not in self.shots_taken and prob_map[x][y] == max_prob:
                    best_cells.append((x, y))
        if best_cells:
            return random.choice(best_cells)
        return self._random_unshot_square()

    def _placement_valid(self, coords: List[Tuple[int, int]]) -> bool:
        """Check if all coords are free (valid for placing hypothetical ship)."""
        for c in coords:
            if c in self.known_misses:
                return False
            if c in self.shots_taken and c not in self.known_hits:
                # we already shot here and it was a miss
                return False
        return True

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _remove_sunk_ship(self, length: Optional[int]):
        """Remove sunk ship length from remaining list."""
        if length and length in self.remaining_ships:
            self.remaining_ships.remove(length)

    def _is_valid_shot(self, coord: Tuple[int, int]) -> bool:
        x, y = coord
        return (0 <= x < self.board_size[0] and
                0 <= y < self.board_size[1] and
                coord not in self.shots_taken)

    def _random_unshot_square(self) -> Tuple[int, int]:
        candidates = [(x, y)
                      for x in range(self.board_size[0])
                      for y in range(self.board_size[1])
                      if (x, y) not in self.shots_taken]
        return random.choice(candidates) if candidates else (0, 0)

    def _get_neighbours(self, coord: Tuple[int, int]) -> List[Tuple[int, int]]:
        x, y = coord
        neighbours = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        return [n for n in neighbours if self._is_valid_shot(n)]

    def _find_direction(self) -> Optional[Tuple[int, int]]:
        if len(self.current_hits) < 2:
            return None
        (x1, y1), (x2, y2) = self.current_hits[-2], self.current_hits[-1]
        dx = x2 - x1
        dy = y2 - y1
        if dx != 0: dx //= abs(dx)
        if dy != 0: dy //= abs(dy)
        return (dx, dy)

    def _next_in_destroy_direction(self) -> Optional[Tuple[int, int]]:
        if not self.destroy_direction or not self.current_hits:
            return None
        dx, dy = self.destroy_direction
        last_x, last_y = self.current_hits[-1]
        next_shot = (last_x + dx, last_y + dy)
        if self._is_valid_shot(next_shot):
            return next_shot
        return None

    def _get_ship_squares(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        start_x, start_y = start_pos
        end_x, end_y = end_pos
        if start_x == end_x:
            min_y, max_y = min(start_y, end_y), max(start_y, end_y)
            return [(start_x, y) for y in range(min_y, max_y + 1)]
        else:
            min_x, max_x = min(start_x, end_x), max(start_x, end_x)
            return [(x, start_y) for x in range(min_x, max_x + 1)]

    def _place_ship_fallback(self, ship_length: int, occupied_squares: Set[Tuple[int, int]]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        for y in range(self.board_size[1]):
            for x in range(self.board_size[0] - ship_length + 1):
                ship_squares = [(x + i, y) for i in range(ship_length)]
                if not any(square in occupied_squares for square in ship_squares):
                    occupied_squares.update(ship_squares)
                    return ((x, y), (x + ship_length - 1, y))
        for x in range(self.board_size[0]):
            for y in range(self.board_size[1] - ship_length + 1):
                ship_squares = [(x, y + i) for i in range(ship_length)]
                if not any(square in occupied_squares for square in ship_squares):
                    occupied_squares.update(ship_squares)
                    return ((x, y), (x, y + ship_length - 1))
        raise RuntimeError(f"Unable to place ship of length {ship_length}")