"""
AdaptiveMetaBot (size-agnostic, posterior-consistent)

Improvements included:
- Posterior-consistent heatmap (S2): score only placements consistent with all
  known misses, and nudge alignments consistent with the current target cluster.
- Non-standard board support: P7 (spaced non-touch) works on any board/fleet,
  with robust edge/center fallbacks.
- Class votes + selection from JSON: optional coarse opponent classes (C1..C6)
  bias arm selection; state lives in .adaptive_meta_state.json.
- Frontier-aware tie-break in hunt: in S1 hunt mode, prefer cells along the
  current "frontier" ridge for faster cleanup.

Notes:
- Coordinates are zero-based (x,y); (0,0) top-left.
- Hand-crafted placements are used on 10x10 with the classic [5,4,3,3,2] fleet.
  On any other board/fleet we use generic placers (edge-biased greedy, center-heavy
  fallback, spaced non-touch).
- Minimal JSON writers are exposed as static helpers for your game runner:
    AdaptiveMetaBot.record_game_result(won: bool, opponent_class: Optional[str]=None)
    AdaptiveMetaBot.add_opponent_class_vote("C2", weight=2)
    AdaptiveMetaBot.infer_and_vote_class_from_shots(shots: List[(x,y)], board_size=(W,H))
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ..interface import BattleshipBot, ShotResponse, ShotResult

Coord = Tuple[int, int]
Placement = List[Tuple[Coord, Coord]]


# ======================= Persistence (JSON) =======================
@dataclass
class ArmStats:
    success: int = 1  # Beta(1,1)
    failure: int = 1

    def sample_score(self) -> float:
        # Use Python's built-in Beta sampler for Thompson Sampling
        return random.betavariate(max(1, int(self.success)), max(1, int(self.failure)))

    def update(self, won: bool):
        if won:
            self.success += 1
        else:
            self.failure += 1


class Persist:
    """Tiny JSON persistence to learn across games."""
    FNAME = ".adaptive_meta_state.json"

    def __init__(self):
        self.state = {
            "arms": {},                 # "P{pid}_S{sid}": {"success": int, "failure": int}
            "games_played": 0,
            "opponent_class_votes": {}, # {"C1": int, ...}
            "last_choice": None,
            "last_board_key": None,
        }
        self._load()

    def _load(self):
        if os.path.exists(self.FNAME):
            try:
                with open(self.FNAME, "r") as f:
                    data = json.load(f)
                # Merge keys defensively
                for k, v in data.items():
                    self.state[k] = v
            except Exception:
                pass

    def save(self):
        try:
            with open(self.FNAME, "w") as f:
                json.dump(self.state, f)
        except Exception:
            pass

    def get_arm(self, key: str) -> ArmStats:
        arms = self.state["arms"]
        if key not in arms:
            arms[key] = {"success": 1, "failure": 1}
        a = arms[key]
        return ArmStats(int(a.get("success", 1)), int(a.get("failure", 1)))

    def put_arm(self, key: str, stats: ArmStats):
        self.state["arms"][key] = {"success": int(stats.success), "failure": int(stats.failure)}


# ======================= Strategy portfolio =======================
class Portfolio:
    """Placement generators and shooter modes; selects an arm with Thompson sampling."""

    # Shooter IDs
    S1_PARITY_TARGET = 1
    S2_HEATMAP_TARGET = 2

    # Placement IDs
    P1_EDGE_SKIRT = 1
    P2_RING_1IN = 2
    P3_TOUCHING_L = 3
    P4_DOUBLE_EDGE = 4
    P5_RANDOM_SHUFFLED = 5
    P6_CENTER_HEAVY = 6
    P7_SPACED_NONTOUCH = 7
    P8_CORNER_SCATTER = 8

    DEFAULT_ARMS: List[Tuple[int, int]] = [
        (P1_EDGE_SKIRT, S1_PARITY_TARGET),
        (P2_RING_1IN,   S1_PARITY_TARGET),
        (P3_TOUCHING_L, S1_PARITY_TARGET),
        (P4_DOUBLE_EDGE,S2_HEATMAP_TARGET),
        (P5_RANDOM_SHUFFLED, S1_PARITY_TARGET),
        (P6_CENTER_HEAVY, S2_HEATMAP_TARGET),
        (P7_SPACED_NONTOUCH, S1_PARITY_TARGET),
        (P8_CORNER_SCATTER, S2_HEATMAP_TARGET),
    ]

    def __init__(self, board_size: Tuple[int, int], ships: List[int], persist: Persist):
        self.w, self.h = board_size
        self.ships = sorted(ships, reverse=True)
        self.persist = persist

    def select_arm(self, opponent_hint: Optional[str] = None) -> Tuple[int, int, str]:
        """Return (placement_id, shooter_id, arm_key), biased by optional class hint."""
        arms = self.DEFAULT_ARMS[:]

        # Lightweight bias by opponent class (votes are coarse, so keep a few options)
        if opponent_hint == "C1":  # parity/heatmap hunter, center-hot
            arms = [(self.P1_EDGE_SKIRT, self.S1_PARITY_TARGET),
                    (self.P4_DOUBLE_EDGE, self.S2_HEATMAP_TARGET),
                    (self.P2_RING_1IN,   self.S1_PARITY_TARGET),
                    (self.P8_CORNER_SCATTER, self.S2_HEATMAP_TARGET)]
        elif opponent_hint == "C2":  # posterior-ish
            arms = [(self.P4_DOUBLE_EDGE, self.S2_HEATMAP_TARGET),
                    (self.P8_CORNER_SCATTER, self.S2_HEATMAP_TARGET),
                    (self.P1_EDGE_SKIRT, self.S2_HEATMAP_TARGET)]
        elif opponent_hint == "C3":  # no-adjacency heuristic
            arms = [(self.P7_SPACED_NONTOUCH, self.S1_PARITY_TARGET),
                    (self.P3_TOUCHING_L, self.S1_PARITY_TARGET),
                    (self.P1_EDGE_SKIRT, self.S1_PARITY_TARGET)]
        elif opponent_hint == "C4":  # edge hunter
            arms = [(self.P6_CENTER_HEAVY, self.S2_HEATMAP_TARGET),
                    (self.P5_RANDOM_SHUFFLED, self.S1_PARITY_TARGET)]
        elif opponent_hint == "C5":  # greedy target / weak hunt
            arms = [(self.P3_TOUCHING_L, self.S1_PARITY_TARGET),
                    (self.P8_CORNER_SCATTER, self.S2_HEATMAP_TARGET)]
        elif opponent_hint == "C6":  # random/noisy
            arms = [(self.P6_CENTER_HEAVY, self.S2_HEATMAP_TARGET),
                    (self.P5_RANDOM_SHUFFLED, self.S1_PARITY_TARGET)]

        # Thompson sampling across chosen arms
        scored: List[Tuple[float, int, int, str]] = []
        for pid, sid in arms:
            key = f"P{pid}_S{sid}"
            stats = self.persist.get_arm(key)
            scored.append((stats.sample_score(), pid, sid, key))
        scored.sort(reverse=True)
        _, pid, sid, key = scored[0]

        self.persist.state["last_choice"] = key
        self.persist.save()
        return pid, sid, key

    # ---------- Placement generation ----------
    def generate_placement(self, placement_id: int) -> Placement:
        standard = (self.w, self.h) == (10, 10) and self.ships == [5, 4, 3, 3, 2]

        if not standard:
            # On any non-standard board/fleet:
            if placement_id == self.P6_CENTER_HEAVY:
                return self._center_heavy_fallback()
            if placement_id == self.P7_SPACED_NONTOUCH:
                return self._spaced_non_touch()
            # Otherwise, robust default
            return self._edge_biased_greedy()

        # Hand-crafted templates for standard 10x10
        templates = {
            self.P1_EDGE_SKIRT: [
                [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0)],  # 5
                [(4, 9), (5, 9), (6, 9), (7, 9)],          # 4
                [(9, 1), (9, 2), (9, 3)],                  # 3
                [(0, 5), (1, 5), (2, 5)],                  # 3
                [(1, 8), (2, 8)],                          # 2
            ],
            self.P2_RING_1IN: [
                [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)],
                [(6, 0), (7, 0), (8, 0), (9, 0)],
                [(2, 8), (3, 8), (4, 8)],
                [(8, 2), (8, 3), (8, 4)],
                [(5, 9), (6, 9)],
            ],
            self.P3_TOUCHING_L: [
                [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)],
                [(5, 2), (5, 3), (5, 4), (5, 5)],
                [(8, 2), (8, 3), (8, 4)],
                [(0, 7), (1, 7), (2, 7)],
                [(5, 0), (6, 0)],
            ],
            self.P4_DOUBLE_EDGE: [
                [(1, 9), (2, 9), (3, 9), (4, 9), (5, 9)],
                [(1, 4), (2, 4), (3, 4), (4, 4)],
                [(0, 8), (1, 8), (2, 8)],
                [(7, 8), (8, 8), (9, 8)],
                [(3, 0), (4, 0)],
            ],
            self.P8_CORNER_SCATTER: [
                [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
                [(6, 9), (7, 9), (8, 9), (9, 9)],
                [(0, 2), (0, 3), (0, 4)],
                [(9, 1), (9, 2), (9, 3)],
                [(8, 1), (8, 2)],
            ],
        }

        if placement_id == self.P5_RANDOM_SHUFFLED:
            return self._random_well_shuffled()
        if placement_id == self.P6_CENTER_HEAVY:
            return self._center_heavy()
        if placement_id == self.P7_SPACED_NONTOUCH:
            return self._spaced_non_touch()

        runs = templates.get(placement_id)
        if not runs:
            return self._edge_biased_greedy()

        runs = self._random_transform(runs)
        placements = self._runs_to_segments(runs)
        if not self._validate(placements):
            return self._edge_biased_greedy()
        return placements

    # ---------- Helpers for placements ----------
    def _random_transform(self, runs: List[List[Coord]]) -> List[List[Coord]]:
        def rot(c: Coord, k: int) -> Coord:
            x, y = c
            if k == 0: return (x, y)
            if k == 1: return (self.h - 1 - y, x)
            if k == 2: return (self.w - 1 - x, self.h - 1 - y)
            return (y, self.w - 1 - x)

        k = random.randint(0, 3)
        mx = random.choice([False, True])
        my = random.choice([False, True])

        out = []
        for run in runs:
            rr = [rot(c, k) for c in run]
            if mx:
                rr = [(self.w - 1 - x, y) for (x, y) in rr]
            if my:
                rr = [(x, self.h - 1 - y) for (x, y) in rr]
            out.append(rr)
        return out

    def _runs_to_segments(self, runs: List[List[Coord]]) -> Placement:
        segs: Placement = []
        for run in runs:
            s = sorted(run)
            segs.append((s[0], s[-1]))
        return segs

    def _validate(self, placements: Placement) -> bool:
        occ: Set[Coord] = set()
        for (x0, y0), (x1, y1) in placements:
            if not (0 <= x0 < self.w and 0 <= y0 < self.h and 0 <= x1 < self.w and 0 <= y1 < self.h):
                return False
            if x0 != x1 and y0 != y1:
                return False
            if x0 == x1:
                for y in range(min(y0, y1), max(y0, y1) + 1):
                    c = (x0, y)
                    if c in occ: return False
                    occ.add(c)
            else:
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    c = (x, y0)
                    if c in occ: return False
                    occ.add(c)
        return True

    def _edge_biased_greedy(self) -> Placement:
        """Edge/1-in ring bias; robust on any board/fleet."""
        W, H = self.w, self.h
        occ: Set[Coord] = set()
        out: Placement = []

        # Ring width scales with min size (keeps behavior sensible on larger boards)
        ring = 1 if min(W, H) <= 8 else max(1, min(3, min(W, H) // 6))
        candidate_rows = [0, H - 1] + ([ring, H - 1 - ring] if H - 1 - ring > ring else [])
        candidate_cols = [0, W - 1] + ([ring, W - 1 - ring] if W - 1 - ring > ring else [])

        def fits(run: List[Coord]) -> bool:
            for (x, y) in run:
                if not (0 <= x < W and 0 <= y < H) or (x, y) in occ:
                    return False
            return True

        def commit(run: List[Coord]):
            for c in run: occ.add(c)
            rs = sorted(run)
            out.append((rs[0], rs[-1]))

        # Prefer lanes that cover edges & ring rows/cols
        lanes: List[List[Coord]] = []
        for y in candidate_rows:
            lanes.append([(x, y) for x in range(W)])
        for x in candidate_cols:
            lanes.append([(x, y) for y in range(H)])
        random.shuffle(lanes)

        for L in self.ships:
            placed = False
            for lane in lanes:
                # horizontal lane
                if len(lane) >= L and all(y == lane[0][1] for (_, y) in lane):
                    idxs = list(range(0, len(lane) - L + 1))
                    random.shuffle(idxs)
                    for i in idxs:
                        run = lane[i:i + L]
                        if fits(run): commit(run); placed = True; break
                if placed: break
                # vertical lane
                if len(lane) >= L and all(x == lane[0][0] for (x, _) in lane):
                    idxs = list(range(0, len(lane) - L + 1))
                    random.shuffle(idxs)
                    for i in idxs:
                        run = lane[i:i + L]
                        if fits(run): commit(run); placed = True; break
                if placed: break

            if not placed:
                # last resort: scan entire board (edge-first)
                cells = [(x, y) for y in range(H) for x in range(W)]
                cells.sort(key=lambda c: min(c[0], W - 1 - c[0]) + min(c[1], H - 1 - c[1]))
                for (x, y) in cells:
                    run_h = [(x + k, y) for k in range(L)]
                    if fits(run_h): commit(run_h); placed = True; break
                    run_v = [(x, y + k) for k in range(L)]
                    if fits(run_v): commit(run_v); placed = True; break
        return out

    def _random_well_shuffled(self) -> Placement:
        occ: Set[Coord] = set()
        out: Placement = []
        for L in self.ships:
            trials = 0
            placed = False
            while trials < 200 and not placed:
                trials += 1
                if random.random() < 0.5:
                    y = random.randrange(self.h)
                    x = random.randrange(self.w - L + 1)
                    run = [(x + k, y) for k in range(L)]
                else:
                    x = random.randrange(self.w)
                    y = random.randrange(self.h - L + 1)
                    run = [(x, y + k) for k in range(L)]
                if any(c in occ for c in run):
                    continue
                for c in run: occ.add(c)
                rs = sorted(run)
                out.append((rs[0], rs[-1]))
                placed = True
            if not placed:
                return self._edge_biased_greedy()
        return out

    def _center_heavy(self) -> Placement:
        if self.w != 10 or self.h != 10 or self.ships != [5, 4, 3, 3, 2]:
            return self._center_heavy_fallback()
        runs = [
            [(3, 4), (4, 4), (5, 4), (6, 4), (7, 4)],  # 5
            [(2, 5), (3, 5), (4, 5), (5, 5)],          # 4
            [(6, 5), (7, 5), (8, 5)],                  # 3
            [(5, 6), (5, 7), (5, 8)],                  # 3
            [(4, 6), (4, 7)],                          # 2
        ]
        runs = self._random_transform(runs)
        placements = self._runs_to_segments(runs)
        if not self._validate(placements):
            return self._center_heavy_fallback()
        return placements

    def _center_heavy_fallback(self) -> Placement:
        """Prefer central windows; robust for larger boards."""
        W, H = self.w, self.h
        occ: Set[Coord] = set()
        out: Placement = []

        def fits(run: List[Coord]) -> bool:
            return all(0 <= x < W and 0 <= y < H and (x, y) not in occ for (x, y) in run)

        def commit(run):
            for c in run: occ.add(c)
            rs = sorted(run)
            out.append((rs[0], rs[-1]))

        def centrality(c: Coord) -> int:
            x, y = c
            return abs(x - W // 2) + abs(y - H // 2)

        for L in self.ships:
            candidates: List[List[Coord]] = []
            for y in range(H):
                for x in range(W - L + 1):
                    candidates.append([(x + k, y) for k in range(L)])
            for x in range(W):
                for y in range(H - L + 1):
                    candidates.append([(x, y + k) for k in range(L)])
            candidates.sort(key=lambda run: sum(centrality(c) for c in run))
            for run in candidates:
                if fits(run):
                    commit(run); break
        return out

    def _spaced_non_touch(self) -> Placement:
        """Place with a 1-cell moat (diagonals may touch). Works on any board."""
        W, H = self.w, self.h
        occ: Set[Coord] = set()
        blocked: Set[Coord] = set()
        out: Placement = []

        def neighborsK(x, y, k=1):
            for dx in range(-k, k + 1):
                for dy in range(-k, k + 1):
                    if dx == 0 and dy == 0: continue
                    yield (x + dx, y + dy)

        def fits(run: List[Coord]) -> bool:
            for (x, y) in run:
                if not (0 <= x < W and 0 <= y < H): return False
                if (x, y) in occ or (x, y) in blocked: return False
            return True

        def commit(run: List[Coord]):
            for c in run:
                occ.add(c)
                for nx, ny in neighborsK(*c, 1):
                    if 0 <= nx < W and 0 <= ny < H:
                        blocked.add((nx, ny))
            rs = sorted(run)
            out.append((rs[0], rs[-1]))

        # Favor edges/1-in lanes for initial anchors
        lanes: List[List[Coord]] = []
        if H >= 1:
            lanes += [[(x, 0) for x in range(W)], [(x, H - 1) for x in range(W)]]
        if W >= 1:
            lanes += [[(0, y) for y in range(H)], [(W - 1, y) for y in range(H)]]
        if W >= 4 and H >= 4:
            lanes += [[(x, 1) for x in range(W)], [(x, H - 2) for x in range(W)]]
            lanes += [[(1, y) for y in range(H)], [(W - 2, y) for y in range(H)]]

        for L in self.ships:
            placed = False
            random.shuffle(lanes)
            for lane in lanes:
                # horizontal
                if len(lane) >= L and all(y == lane[0][1] for (_, y) in lane):
                    for i in range(0, len(lane) - L + 1):
                        run = lane[i:i + L]
                        if fits(run): commit(run); placed = True; break
                if placed: break
                # vertical
                if len(lane) >= L and all(x == lane[0][0] for (x, _) in lane):
                    for i in range(0, len(lane) - L + 1):
                        run = lane[i:i + L]
                        if fits(run): commit(run); placed = True; break
                if placed: break
            if not placed:
                return self._random_well_shuffled()
        return out


# ======================= Opponent profiler (optional) =======================
class OpponentProfiler:
    """Collects opponent shots (if available) to hint an archetype (C1..C6)."""

    def __init__(self, board_size: Tuple[int, int]):
        self.w, self.h = board_size
        self.enemy_shots: List[Coord] = []

    def record_shot(self, c: Coord):
        self.enemy_shots.append(c)

    def parity_adherence(self) -> float:
        if not self.enemy_shots:
            return 0.0
        color0 = sum((x + y) % 2 == 0 for (x, y) in self.enemy_shots)
        color1 = len(self.enemy_shots) - color0
        return max(color0, color1) / max(1, len(self.enemy_shots))

    def center_bias(self) -> float:
        if not self.enemy_shots:
            return 0.0
        cx0, cx1 = self.w // 5, self.w - self.w // 5 - 1
        cy0, cy1 = self.h // 5, self.h - self.h // 5 - 1
        n_eval = min(24, len(self.enemy_shots))
        in_center = sum(1 for (x, y) in self.enemy_shots[:n_eval] if cx0 <= x <= cx1 and cy0 <= y <= cy1)
        return in_center / max(1, n_eval)

    def class_hint(self) -> Optional[str]:
        n = min(24, len(self.enemy_shots))
        if n < 12:
            return None
        r_parity = self.parity_adherence()
        r_center = self.center_bias()
        if r_parity >= 0.85 and r_center >= 0.55:
            return "C1"  # parity+prob, center-hot
        if r_parity >= 0.8 and 0.35 <= r_center <= 0.65:
            return "C2"  # posterior-ish
        if r_parity <= 0.55 and r_center <= 0.30:
            return "C4"  # edge hunter
        if r_parity <= 0.60 and 0.30 < r_center < 0.55:
            return "C6"  # noisy/randomish
        return "C5"      # greedy target / weak hunt


# ======================= The Bot =======================
class AdaptiveMetaBot2(BattleshipBot):
    """Meta-bot that selects counter strategies and learns between games via JSON."""

    def __init__(self, player_id: str, board_size: Tuple[int, int], ships: List[int]):
        super().__init__(player_id, board_size, ships)
        self.persist = Persist()
        self.portfolio = Portfolio(board_size, ships, self.persist)
        self.profiler = OpponentProfiler(board_size)

        # Optional class hint from JSON votes
        votes: Dict[str, int] = self.persist.state.get("opponent_class_votes", {})
        hint = max(votes.items(), key=lambda kv: kv[1])[0] if votes else None

        # Select arm for THIS game (biased by votes)
        self.placement_id, self.shooter_id, self.arm_key = self.portfolio.select_arm(hint)

        # Avoid repeating exact same layout
        self._last_board_key = self.persist.state.get("last_board_key")

        # Shooting state
        self._shots_taken: Set[Coord] = set()
        self._hits: Set[Coord] = set()
        self._misses: Set[Coord] = set()

        self._target_cluster: Set[Coord] = set()
        self._orientation: Optional[str] = None
        self._frontiers: List[Coord] = []
        self._remaining_ships: List[int] = sorted(ships, reverse=True)

    @property
    def name(self) -> str:
        return "AdaptiveMetaBot"

    # -------- Placement --------
    def place_ships(self) -> List[Tuple[Coord, Coord]]:
        # Try to avoid repeating the same layout
        for _ in range(12):
            placement = self.portfolio.generate_placement(self.placement_id)
            key = self._placement_key(placement)
            if key != self._last_board_key:
                self.persist.state["last_board_key"] = key
                self.persist.save()
                return placement
        # Fallback
        self.persist.state["last_board_key"] = self._placement_key(placement)
        self.persist.save()
        return placement

    def _placement_key(self, placement: Placement) -> str:
        # Include board size to avoid cross-board collisions
        cells: List[Coord] = []
        for (a, b) in placement:
            if a[0] == b[0]:
                y0, y1 = sorted([a[1], b[1]])
                cells.extend([(a[0], y) for y in range(y0, y1 + 1)])
            else:
                x0, x1 = sorted([a[0], b[0]])
                cells.extend([(x, a[1]) for x in range(x0, x1 + 1)])
        cells.sort()
        sz = f"{self.board_size[0]}x{self.board_size[1]}"
        return sz + "|" + "|".join(f"{x},{y}" for (x, y) in cells)

    # -------- Shooting --------
    def take_shot(self) -> Coord:
        # Targeting first
        while self._frontiers:
            c = self._frontiers.pop()
            if c not in self._shots_taken and self._in_bounds(c):
                self._shots_taken.add(c)
                return c

        # Hunt mode
        if self.shooter_id == Portfolio.S1_PARITY_TARGET:
            # Classic parity hunt with a frontier-aware tie-break
            parity = 2 if any(L >= 2 for L in self._remaining_ships) else 1
            order = self._hunt_candidates(parity)

            # Frontier-aware ranking: prefer cells whose 8-neighborhood has fewer shots
            def frontier_score(c: Coord) -> int:
                x, y = c
                neigh = [(x+dx, y+dy) for dx in (-1,0,1) for dy in (-1,0,1)]
                return -sum(1 for z in neigh if z in self._shots_taken)

            order.sort(key=lambda c: (self._centrality(c), frontier_score(c)))
            for c in order:
                if c not in self._shots_taken:
                    self._shots_taken.add(c)
                    return c
        else:
            c = self._best_heatmap_shot()
            self._shots_taken.add(c)
            return c

        # Fallback
        for y in range(self.board_size[1]):
            for x in range(self.board_size[0]):
                if (x, y) not in self._shots_taken:
                    self._shots_taken.add((x, y))
                    return (x, y)
        return (0, 0)

    def receive_shot_result(self, shot: Coord, result: ShotResponse):
        if result.result == ShotResult.MISS:
            self._misses.add(shot)
            return

        if result.result == ShotResult.HIT:
            self._hits.add(shot)
            self._absorb_hit(shot)
            return

        if result.result == ShotResult.SUNK:
            self._hits.add(shot)
            if result.sunk_ship_length is not None:
                try:
                    self._remaining_ships.remove(result.sunk_ship_length)
                except ValueError:
                    pass
            self._absorb_hit(shot)
            self._target_cluster.clear()
            self._orientation = None
            self._frontiers.clear()

    # Optional (call during game if you can; not required for JSON learning)
    def observe_opponent_shot(self, coord: Coord):
        self.profiler.record_shot(coord)

    # ----- Internals: target mode & hunt -----
    def _absorb_hit(self, shot: Coord):
        self._target_cluster.add(shot)
        if self._orientation is None and len(self._target_cluster) >= 2:
            xs = {x for x, _ in self._target_cluster}
            ys = {y for _, y in self._target_cluster}
            if len(xs) == 1:
                self._orientation = 'v'
            elif len(ys) == 1:
                self._orientation = 'h'
        self._frontiers = self._build_frontiers()

    def _build_frontiers(self) -> List[Coord]:
        cl = sorted(self._target_cluster)
        out: List[Coord] = []
        if not cl:
            return out
        if self._orientation == 'h':
            y = cl[0][1]
            xs = sorted(x for x, _ in cl)
            for p in [(xs[-1] + 1, y), (xs[0] - 1, y)]:
                if self._in_bounds(p) and p not in self._shots_taken:
                    out.append(p)
        elif self._orientation == 'v':
            x = cl[0][0]
            ys = sorted(y for _, y in cl)
            for p in [(x, ys[-1] + 1), (x, ys[0] - 1)]:
                if self._in_bounds(p) and p not in self._shots_taken:
                    out.append(p)
        else:
            last = cl[-1]
            nbrs = [(last[0] + 1, last[1]), (last[0] - 1, last[1]),
                    (last[0], last[1] + 1), (last[0], last[1] - 1)]
            for p in nbrs:
                if self._in_bounds(p) and p not in self._shots_taken:
                    out.append(p)
        return out

    def _hunt_candidates(self, parity: int) -> List[Coord]:
        out: List[Coord] = []
        W, H = self.board_size
        for y in range(H):
            for x in range(W):
                if (x + y) % parity == 0:
                    out.append((x, y))
        for y in range(H):
            for x in range(W):
                if (x + y) % parity != 0:
                    out.append((x, y))
        return out

    # ===== Posterior-consistent heatmap (S2) with frontier-aware tie-break =====
    def _best_heatmap_shot(self) -> Coord:
        W, H = self.board_size
        scores = [[0 for _ in range(W)] for _ in range(H)]
        misses = self._misses

        def placement_ok(x0, y0, L, horiz) -> bool:
            # In-bounds and consistent with all known misses.
            if horiz:
                if x0 + L > W: return False
                cells = [(x0 + k, y0) for k in range(L)]
            else:
                if y0 + L > H: return False
                cells = [(x0, y0 + k) for k in range(L)]
            if any(c in misses for c in cells):
                return False
            # Consistency nudge for current oriented cluster: reject contradictions.
            if self._target_cluster:
                xs = {x for x, _ in self._target_cluster}
                ys = {y for _, y in self._target_cluster}
                if len(xs) == 1 and horiz:
                    # vertical target → horizontal placement unlikely to explain
                    return False
                if len(ys) == 1 and not horiz:
                    # horizontal target → vertical placement unlikely to explain
                    return False
            return True

        remaining = self._remaining_ships[:] if self._remaining_ships else [2]

        for L in remaining:
            # horizontal placements
            for y in range(H):
                for x in range(W - L + 1):
                    if placement_ok(x, y, L, True):
                        for k in range(L):
                            c = (x + k, y)
                            if c not in self._shots_taken:
                                scores[y][x + k] += 1
            # vertical placements
            for x in range(W):
                for y in range(H - L + 1):
                    if placement_ok(x, y, L, False):
                        for k in range(L):
                            c = (x, y + k)
                            if c not in self._shots_taken:
                                scores[y + k][x] += 1

        # Frontier-aware tie-break (prefer ridge cells)
        def frontier_bonus(x: int, y: int) -> int:
            neigh = [(x+dx, y+dy) for dx in (-1,0,1) for dy in (-1,0,1)]
            return -sum(1 for z in neigh if z in self._shots_taken)

        best = None
        best_score = -1
        best_fb = -10**9
        for y in range(H):
            for x in range(W):
                if (x, y) in self._shots_taken:
                    continue
                sc = scores[y][x]
                fb = frontier_bonus(x, y)
                if sc > best_score or (sc == best_score and fb > best_fb):
                    best_score, best_fb, best = sc, fb, (x, y)

        if best is None:
            for y in range(H):
                for x in range(W):
                    if (x, y) not in self._shots_taken:
                        return (x, y)
            return (0, 0)
        return best

    def _centrality(self, c: Optional[Coord]) -> int:
        if c is None: return 10**9
        x, y = c
        dx = min(x, self.board_size[0] - 1 - x)
        dy = min(y, self.board_size[1] - 1 - y)
        return dx + dy

    def _in_bounds(self, c: Coord) -> bool:
        x, y = c
        return 0 <= x < self.board_size[0] and 0 <= y < self.board_size[1]

    # ================= Static JSON writers (call from your game manager) =================
    @staticmethod
    def record_game_result(won: bool, opponent_class: Optional[str] = None, json_path: str = ".adaptive_meta_state.json"):
        """
        After the game finishes, call once:
        - Updates the arm recorded in 'last_choice' with win/loss
        - Increments games_played
        - Optionally records an opponent class vote ('C1'..'C6')
        """
        default_state = {
            "arms": {},
            "games_played": 0,
            "opponent_class_votes": {},
            "last_choice": None,
            "last_board_key": None,
        }

        # Load
        try:
            with open(json_path, "r") as f:
                state = json.load(f)
        except Exception:
            state = default_state.copy()

        # Ensure keys
        for k, v in default_state.items():
            if k not in state:
                state[k] = v if not isinstance(v, dict) else v.copy()

        # Update last arm
        arm_key = state.get("last_choice")
        if arm_key:
            arm = state["arms"].get(arm_key, {"success": 1, "failure": 1})
            if won:
                arm["success"] = int(arm.get("success", 1)) + 1
            else:
                arm["failure"] = int(arm.get("failure", 1)) + 1
            state["arms"][arm_key] = arm

        # Bump counter
        state["games_played"] = int(state.get("games_played", 0)) + 1

        # Optional: class vote
        if opponent_class:
            votes = state.get("opponent_class_votes", {})
            votes[opponent_class] = int(votes.get(opponent_class, 0)) + 1
            state["opponent_class_votes"] = votes

        # Save
        try:
            with open(json_path, "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    @staticmethod
    def add_opponent_class_vote(opponent_class: str, weight: int = 1, json_path: str = ".adaptive_meta_state.json"):
        """Add a class vote (e.g., 'C2') with integer weight."""
        try:
            with open(json_path, "r") as f:
                state = json.load(f)
        except Exception:
            state = {"opponent_class_votes": {}}

        votes = state.get("opponent_class_votes", {})
        votes[opponent_class] = int(votes.get(opponent_class, 0)) + int(weight)
        state["opponent_class_votes"] = votes

        try:
            with open(json_path, "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    @staticmethod
    def infer_and_vote_class_from_shots(
        shots: List[Tuple[int, int]],
        board_size: Tuple[int, int] = (10, 10),
        json_path: str = ".adaptive_meta_state.json"
    ) -> Optional[str]:
        """
        If you captured the opponent's early shots at your board, call this once post-game.
        It infers a coarse class and records a vote. Returns the inferred class or None.
        """
        if not shots:
            return None

        W, H = board_size

        # Parity adherence
        color0 = sum((x + y) % 2 == 0 for (x, y) in shots)
        r_parity = max(color0, len(shots) - color0) / max(1, len(shots))

        # Center bias over first ~24 shots
        cx0, cx1 = W // 5, W - W // 5 - 1
        cy0, cy1 = H // 5, H - H // 5 - 1
        n_eval = min(24, len(shots))
        in_center = sum(1 for (x, y) in shots[:n_eval] if cx0 <= x <= cx1 and cy0 <= y <= cy1)
        r_center = in_center / max(1, n_eval)

        if r_parity >= 0.85 and r_center >= 0.55:
            cls = "C1"
        elif r_parity >= 0.8 and 0.35 <= r_center <= 0.65:
            cls = "C2"
        elif r_parity <= 0.55 and r_center <= 0.30:
            cls = "C4"
        elif r_parity <= 0.60 and 0.30 < r_center < 0.55:
            cls = "C6"
        else:
            cls = "C5"

        AdaptiveMetaBot.add_opponent_class_vote(cls, weight=1, json_path=json_path)
        return cls
