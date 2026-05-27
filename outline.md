# Battleship Hackathon — Intro Storyboard

*Slide-by-slide outline for a ~10 minute intro. Total event: 2 hours.*

---

## Slide 1 — Title

**Battleship Bot Hackathon**
*Learning AI-assisted coding, one sunk ship at a time*

**Speaker notes:** Welcome everyone. Set the tone — competitive, fun, no prior AI or game experience needed.

---

## Slide 2 — What today is really about

- Today is about **AI-assisted coding**
- The Battleship bot is the playground — small, self-contained, clear win condition
- At the end: a tournament. Bots fight, one wins.

**Speaker notes:** Emphasise the bot is the vehicle, not the destination. The real skill being practised is collaborating with a coding agent.

---

## Slide 3 — The game

- Standard Battleship on a grid
- Default: 10×10, ships [5, 4, 3, 3, 2] *(but this varies — see Slide 7)*
- Your bot must: **place ships**, **take shots**, **react to results** (hit / miss / sunk)
- Hidden information — you only see your own shot outcomes

**Speaker notes:** Quick recap. Most people know the rules; don't dwell.

---

## Slide 4 — The bot interface

Three methods to implement:

```python
def place_ships(self):
    # return [((x1,y1),(x2,y2)), ...]

def take_shot(self):
    # return (x, y)

def receive_shot_result(self, shot, result):
    # update internal state
```

Coordinates: `(0,0)` top-left, x → right, y → down.

**Speaker notes:** Keep this brief — the agent will read the README itself. Just enough so the team knows what they're looking at.

---

## Slide 5 — Setup

1. Python 3.11+
2. Clone the repo
3. `python3 -m venv env && source env/bin/activate`
4. `pip install -e ".[test]"`
5. Sanity check: `battleship_challenge RandomBot RandomBot --visualize`

**Fix environment issues now — not at minute 45.**

**Speaker notes:** Be firm about this. Walk the room while they set up if you can.

---

## Slide 6 — Working with the agent (the actual point)

This is the skill we're here to practice. A few things to experiment with:

- How much context does the agent need before it's useful?
- How do you phrase a request so you get what you actually wanted?
- When something's wrong, what's the fastest way to get the agent unstuck?
- How small should each step be?
- When do you trust its suggestions, and when do you check?

**Notice what works for you. We'll compare notes in the debrief.**

**Speaker notes:** Resist the urge to give them the answers. The discovery is the point. If they ask "what should I do?" turn it back: "try something, see what happens." Mention you'll collect patterns in the debrief — that primes them to pay attention to their own process.

---

## Slide 7 — Rules

- Python **standard library only**
- Board size and ship list **will vary between tournament rounds** — your bot must adapt
- `__init__` receives `board_size` and `ships` — use them, don't hardcode
- Bot must take its turn reasonably quickly
- **Crashes = forfeit** — test before submitting

**Speaker notes:** Hammer this. A bot that assumes 10×10 with [5,4,3,3,2] will work fine in testing and then die in round 2. Test on at least one other configuration before the tournament.

---

## Slide 8 — Timeline & tournament format

- **Now → +1h 10m** — build & test (~70 min)
- **+1h 10m → +1h 30m** — tournament (~20 min)
- **+1h 30m → +2h** — debrief (~30 min)

**Tournament:** multiple rounds, each with a different board configuration. For example:

- Round 1: 10×10, ships [5,4,3,3,2] *(the default)*
- Round 2: 8×8, ships [4,3,2] *(small & fast)*
- Round 3: 12×12, ships [6,5,4,3,2,2] *(big board)*

Bots are scored across all rounds — the most consistent adapter wins.

**Speaker notes:** Encourage them to test against `RandomBot` on at least two different configurations before submitting. Mention they can run `battleship_challenge MyBot RandomBot --board-size 8x8 --ships 4,3,2` to try it.

---

## Slide 9 — Go

- Name your bot something memorable
- Ask for help early
- The team that wins won't be the one with the cleverest algorithm — it'll be the one that collaborated best with their agent

**Good luck. 🎯**

**Speaker notes:** Short, energetic close. Then start the clock.