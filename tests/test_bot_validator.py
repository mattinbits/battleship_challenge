"""Tests for the bot_validator utility."""

import pytest
from battleship_challenge.bot_validator import run_checks, _check_placement


BOARD_SIZE = (10, 10)
SHIPS = [5, 4, 3, 3, 2]

VALID_SHIPS = [
    ((0, 0), (0, 4)),
    ((2, 0), (2, 3)),
    ((4, 0), (4, 2)),
    ((6, 0), (6, 2)),
    ((8, 0), (8, 1)),
]


# ── _check_placement unit tests ────────────────────────────────────────────────

def test_check_placement_valid():
    assert _check_placement(VALID_SHIPS, BOARD_SIZE, SHIPS) == []


def test_check_placement_reversed_order_valid():
    """Reversed order is still valid — multiset comparison."""
    assert _check_placement(list(reversed(VALID_SHIPS)), BOARD_SIZE, SHIPS) == []


def test_check_placement_wrong_lengths():
    wrong = [
        ((0, 0), (0, 2)),  # length 3 instead of 5
        ((2, 0), (2, 3)),
        ((4, 0), (4, 2)),
        ((6, 0), (6, 2)),
        ((8, 0), (8, 1)),
    ]
    errors = _check_placement(wrong, BOARD_SIZE, SHIPS)
    assert any("don't match" in e for e in errors)


def test_check_placement_out_of_bounds():
    oob = list(VALID_SHIPS)
    oob[0] = ((0, 0), (0, 11))  # end y=11 is out of bounds on a 10-row board
    errors = _check_placement(oob, BOARD_SIZE, SHIPS)
    assert any("out of bounds" in e for e in errors)


def test_check_placement_diagonal_ship():
    diagonal = list(VALID_SHIPS)
    diagonal[0] = ((0, 0), (2, 2))  # diagonal
    errors = _check_placement(diagonal, BOARD_SIZE, SHIPS)
    assert any("horizontal or vertical" in e for e in errors)


def test_check_placement_overlapping_ships():
    overlapping = [
        ((0, 0), (0, 4)),  # length 5
        ((0, 0), (0, 3)),  # length 4 — starts at same square
        ((4, 0), (4, 2)),
        ((6, 0), (6, 2)),
        ((8, 0), (8, 1)),
    ]
    errors = _check_placement(overlapping, BOARD_SIZE, SHIPS)
    assert any("overlap" in e for e in errors)


# ── run_checks integration tests ───────────────────────────────────────────────

def test_run_checks_random_bot_passes(capsys):
    """RandomBot should pass all validation checks."""
    exit_code = run_checks("RandomBot")
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "ALL CHECKS PASSED" in out


def test_run_checks_unknown_bot_fails(capsys):
    """An unknown bot name should fail immediately with a non-zero exit code."""
    exit_code = run_checks("NoSuchBotXYZ")
    assert exit_code == 1


def test_run_checks_failing_bot_fails(capsys):
    """ShipPlacementExceptionBot should fail the placement check."""
    exit_code = run_checks("ShipPlacementExceptionBot")
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL" in out
