"""Bot validator utility for battleship challenge submissions."""

import sys
import traceback
from typing import List, Set, Tuple

from .interface import BattleshipBot, ShotResult, ShotResponse

BOARD_SIZE = (10, 10)
SHIPS = [5, 4, 3, 3, 2]
NUM_PLACEMENT_RUNS = 50


def _get_ship_squares(start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
    sx, sy = start
    ex, ey = end
    if sx == ex:
        return [(sx, y) for y in range(min(sy, ey), max(sy, ey) + 1)]
    return [(x, sy) for x in range(min(sx, ex), max(sx, ex) + 1)]


def _check_placement(ships, board_size, expected_ships) -> List[str]:
    """Return a list of error strings for an invalid placement, or empty list if valid."""
    errors = []
    lengths = []
    occupied: Set[Tuple[int, int]] = set()
    w, h = board_size

    for i, ship in enumerate(ships):
        if not (isinstance(ship, tuple) and len(ship) == 2):
            errors.append(f"ship {i}: not a 2-tuple of positions")
            continue
        start, end = ship
        if not (isinstance(start, tuple) and len(start) == 2 and
                isinstance(end, tuple) and len(end) == 2):
            errors.append(f"ship {i}: start/end must each be a 2-tuple")
            continue
        sx, sy = start
        ex, ey = end
        if not (0 <= sx < w and 0 <= sy < h):
            errors.append(f"ship {i}: start {start} out of bounds")
        if not (0 <= ex < w and 0 <= ey < h):
            errors.append(f"ship {i}: end {end} out of bounds")
        if sx != ex and sy != ey:
            errors.append(f"ship {i}: must be horizontal or vertical")
            continue
        squares = _get_ship_squares(start, end)
        lengths.append(len(squares))
        for sq in squares:
            if sq in occupied:
                errors.append(f"ship {i}: overlaps at {sq}")
                break
            occupied.add(sq)

    if sorted(lengths) != sorted(expected_ships):
        errors.append(
            f"ship lengths {sorted(lengths)} don't match required {sorted(expected_ships)}"
        )

    return errors


def run_checks(bot_name: str) -> int:
    """Run all validation checks for the named bot. Returns 0 on success, 1 on failure."""
    from .main import discover_bot_class

    passed = 0
    failed = 0

    def ok(msg: str):
        nonlocal passed
        print(f"  PASS  {msg}")
        passed += 1

    def fail(msg: str, detail: str = None):
        nonlocal failed
        print(f"  FAIL  {msg}")
        if detail:
            for line in detail.splitlines():
                print(f"        {line}")
        failed += 1

    print(f"Validating bot: {bot_name}")
    print("=" * 50)

    # 1. Discover bot class
    try:
        bot_class = discover_bot_class(bot_name)
        ok("Bot class discovered")
    except Exception as e:
        fail("Bot class discovered", str(e))
        print(f"\nResults: 0 passed, 1 failed — cannot continue")
        return 1

    # 2. Instantiate bot
    try:
        bot = bot_class("validator", BOARD_SIZE, SHIPS)
        ok("Bot instantiated")
    except Exception as e:
        fail("Bot instantiated", str(e))
        print(f"\nResults: {passed} passed, {failed} failed — cannot continue")
        return 1

    # 3. Single place_ships() call
    try:
        ships = bot.place_ships()
        errors = _check_placement(ships, BOARD_SIZE, SHIPS)
        if errors:
            fail("place_ships() returns valid placement", "\n".join(errors))
        else:
            ok("place_ships() returns valid placement")
    except Exception:
        fail("place_ships() returns valid placement", traceback.format_exc())

    # 4. N placement runs for stability
    placement_failures = []
    for i in range(NUM_PLACEMENT_RUNS):
        try:
            b = bot_class("validator", BOARD_SIZE, SHIPS)
            s = b.place_ships()
            errs = _check_placement(s, BOARD_SIZE, SHIPS)
            if errs:
                placement_failures.append(f"run {i}: {'; '.join(errs)}")
        except Exception as e:
            placement_failures.append(f"run {i}: {e}")
    if placement_failures:
        fail(
            f"place_ships() stable across {NUM_PLACEMENT_RUNS} runs",
            placement_failures[0],
        )
    else:
        ok(f"place_ships() stable across {NUM_PLACEMENT_RUNS} runs")

    # 5. take_shot() returns a valid coordinate
    try:
        shot = bot.take_shot()
        if not (
            isinstance(shot, tuple)
            and len(shot) == 2
            and isinstance(shot[0], int)
            and isinstance(shot[1], int)
            and 0 <= shot[0] < BOARD_SIZE[0]
            and 0 <= shot[1] < BOARD_SIZE[1]
        ):
            fail("take_shot() returns valid (x, y) tuple within bounds", f"got {shot!r}")
        else:
            ok("take_shot() returns valid (x, y) tuple within bounds")
    except Exception as e:
        fail("take_shot() returns valid (x, y) tuple within bounds", str(e))

    # 6. receive_shot_result() accepts all documented response shapes
    try:
        b = bot_class("validator", BOARD_SIZE, SHIPS)
        b.receive_shot_result((0, 0), ShotResponse(ShotResult.MISS))
        b.receive_shot_result((1, 0), ShotResponse(ShotResult.HIT))
        b.receive_shot_result((2, 0), ShotResponse(ShotResult.SUNK, sunk_ship_length=3))
        ok("receive_shot_result() accepts MISS / HIT / SUNK")
    except Exception as e:
        fail("receive_shot_result() accepts MISS / HIT / SUNK", str(e))

    # 7. Full game: no repeat shots, no exceptions
    try:
        from .bots.random_bot import RandomBot

        game_bot = bot_class("validator", BOARD_SIZE, SHIPS)
        opponent = RandomBot("opponent", BOARD_SIZE, SHIPS)

        try:
            bot_ships = game_bot.place_ships()
        except Exception as e:
            fail("Full game: no repeat shots and no exceptions", f"place_ships raised: {e}")
            _print_summary(passed, failed)
            return 1 if failed else 0

        try:
            opp_ships = opponent.place_ships()
        except Exception:
            opp_ships = []

        hits: Set[Tuple[int, int]] = set()
        shots_seen: Set[Tuple[int, int]] = set()
        repeat_error = None
        exception_error = None
        max_shots = BOARD_SIZE[0] * BOARD_SIZE[1]

        for _ in range(max_shots):
            try:
                shot = game_bot.take_shot()
            except Exception as e:
                exception_error = f"take_shot raised: {e}"
                break

            if shot in shots_seen:
                repeat_error = f"repeated shot at {shot}"
                break
            shots_seen.add(shot)

            # Calculate result
            result = _calc_result(shot, opp_ships, hits)

            try:
                game_bot.receive_shot_result(shot, result)
            except Exception as e:
                exception_error = f"receive_shot_result raised: {e}"
                break

            # Check win condition
            if opp_ships and all(
                sq in hits
                for ship in opp_ships
                for sq in _get_ship_squares(ship[0], ship[1])
            ):
                break

        if repeat_error:
            fail("Full game: no repeat shots and no exceptions", repeat_error)
        elif exception_error:
            fail("Full game: no repeat shots and no exceptions", exception_error)
        else:
            ok("Full game: no repeat shots and no exceptions")

    except Exception:
        fail("Full game: no repeat shots and no exceptions", traceback.format_exc())

    _print_summary(passed, failed)
    return 1 if failed else 0


def _calc_result(
    shot: Tuple[int, int],
    ships: List[Tuple[Tuple[int, int], Tuple[int, int]]],
    hits: Set[Tuple[int, int]],
) -> ShotResponse:
    x, y = shot
    for ship_start, ship_end in ships:
        squares = _get_ship_squares(ship_start, ship_end)
        if (x, y) in squares:
            hits.add((x, y))
            if all(sq in hits for sq in squares):
                return ShotResponse(ShotResult.SUNK, len(squares))
            return ShotResponse(ShotResult.HIT)
    return ShotResponse(ShotResult.MISS)


def _print_summary(passed: int, failed: int):
    print()
    status = "ALL CHECKS PASSED" if failed == 0 else f"{failed} CHECK(S) FAILED"
    print(f"Results: {passed} passed, {failed} failed — {status}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate a battleship bot before submission"
    )
    parser.add_argument(
        "bot_name",
        help="Bot class name to validate (e.g. MyBot or mymodule.MyBot)",
    )
    args = parser.parse_args()
    sys.exit(run_checks(args.bot_name))


if __name__ == "__main__":
    main()
