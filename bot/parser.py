from __future__ import annotations

import re
from dataclasses import dataclass

_RECORD_RE = re.compile(r"^(\d+)\s*[–—-]\s*(\d+)\s*[–—-]\s*(\d+)$")


@dataclass
class PlayerRound:
    round: int
    pairing: int
    player_name: str
    player_key: str
    game_wins: int | None
    opponent_name: str | None
    opponent_key: str | None
    opponent_game_wins: int | None
    record_wins: int
    record_draws: int
    record_losses: int


def normalize_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def parse_record(token: str) -> tuple[int, int, int] | None:
    m = _RECORD_RE.match(token.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _is_record(token: str) -> bool:
    return _RECORD_RE.match(token.strip()) is not None


def _is_int(token: str) -> bool:
    return token.isdigit()


def _is_name(token: str) -> bool:
    return not _is_int(token) and not _is_record(token)


def parse_tournament(content: str) -> list[PlayerRound] | None:
    tokens = [ln.strip() for ln in content.splitlines() if ln.strip()]
    rows: list[PlayerRound] = []
    round_no = 0
    i = 0
    n = len(tokens)
    while i < n:
        # A pairing starts with: INT (pairing#), NAME (player1), RECORD (player1).
        if not (
            i + 2 < n
            and _is_int(tokens[i])
            and _is_name(tokens[i + 1])
            and _is_record(tokens[i + 2])
        ):
            i += 1  # resync: skip stray token
            continue
        pairing = int(tokens[i])
        p1_name = tokens[i + 1]
        p1_rec = parse_record(tokens[i + 2])
        i += 3
        if pairing == 1:
            round_no += 1
        # Player 2 present iff the next tokens are INT, INT, NAME, RECORD.
        has_p2 = (
            i + 3 < n
            and _is_int(tokens[i])
            and _is_int(tokens[i + 1])
            and _is_name(tokens[i + 2])
            and _is_record(tokens[i + 3])
        )
        if has_p2:
            w1 = int(tokens[i])
            w2 = int(tokens[i + 1])
            p2_name = tokens[i + 2]
            p2_rec = parse_record(tokens[i + 3])
            i += 4
            rows.append(_row(round_no, pairing, p1_name, w1, p2_name, w2, p1_rec))
            rows.append(_row(round_no, pairing, p2_name, w2, p1_name, w1, p2_rec))
        else:
            # Bye: player 1 only, no opponent.
            rows.append(_row(round_no, pairing, p1_name, None, None, None, p1_rec))
    return rows or None


def _row(round_no, pairing, name, game_wins, opp_name, opp_wins, record) -> PlayerRound:
    return PlayerRound(
        round=round_no,
        pairing=pairing,
        player_name=name,
        player_key=normalize_name(name),
        game_wins=game_wins,
        opponent_name=opp_name,
        opponent_key=normalize_name(opp_name) if opp_name else None,
        opponent_game_wins=opp_wins,
        record_wins=record[0],
        record_draws=record[1],
        record_losses=record[2],
    )
