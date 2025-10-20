from typing import Any, Dict, List, Optional, Tuple

NumericKey = Tuple[int, Any]


def _collection_values(obj: Any) -> List[Any]:
    """
    Yahoo's fantasy API encodes many collections as dicts with numeric string keys.
    This helper flattens those structures into ordered lists.
    """
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        numeric_keys: List[NumericKey] = []
        for key in obj.keys():
            if isinstance(key, int):
                numeric_keys.append((key, key))
            elif isinstance(key, str) and key.isdigit():
                numeric_keys.append((int(key), key))
        if numeric_keys:
            numeric_keys.sort(key=lambda kv: kv[0])
            return [obj[k] for _, k in numeric_keys]
    return []

def _flatten_kv(entries: List[Any]) -> Dict[str, Any]:
    """
    Merge a list of single-key dicts (with stray empty lists sprinkled in) into one dict.
    """
    merged: Dict[str, Any] = {}
    for entry in entries:
        if isinstance(entry, dict):
            merged.update(entry)
    return merged


def _to_int(val: Any) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _to_float(val: Any) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _maybe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _extract_slot_value(pos_block: Any) -> Optional[str]:
    """
    Yahoo returns selected_position blocks as either dicts, lists of dicts, or a mix
    of both. This helper walks those structures and returns the first slot label.
    """
    if isinstance(pos_block, str):
        return pos_block
    if isinstance(pos_block, dict):
        for key in ("position", "display_position", "name"):
            val = pos_block.get(key)
            if isinstance(val, str) and val:
                return val
        for child in _collection_values(pos_block):
            slot = _extract_slot_value(child)
            if slot:
                return slot
    if isinstance(pos_block, list):
        for entry in pos_block:
            slot = _extract_slot_value(entry)
            if slot:
                return slot
    return None


def league_key(game_key: str, league_id: str) -> str:
    # Yahoo league keys look like "{game_key}.l.{league_id}", where game_key is numeric
    return f"{game_key}.l.{league_id}"


def extract_game_key(json_games: Dict[str, Any]) -> str:
    # Response: fantasy_content.games.{index}.game[*].game_key
    games = json_games["fantasy_content"]["games"]
    for entry in _collection_values(games):
        game_list = entry.get("game") if isinstance(entry, dict) else entry
        for game in _collection_values(game_list):
            if isinstance(game, dict) and "game_key" in game:
                return game["game_key"]
    raise ValueError("No game_key found")


def map_standings(standings_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Flatten league standings into simple rows
    teams = standings_json["fantasy_content"]["league"][1]["standings"][0]["teams"]
    out = []
    for wrapped in _collection_values(teams):
        team_payload = wrapped.get("team") if isinstance(wrapped, dict) else None
        if not team_payload or not isinstance(team_payload, list):
            continue
        meta = _flatten_kv(team_payload[0] if len(team_payload) else [])
        standings_info = {}
        for section in team_payload[1:]:
            if isinstance(section, dict) and "team_standings" in section:
                standings_info = section["team_standings"]
                break
        outcome = standings_info.get("outcome_totals", {}) if standings_info else {}
        out.append({
            "team_key": meta.get("team_key"),
            "name": meta.get("name"),
            "wins": _to_int(outcome.get("wins")),
            "losses": _to_int(outcome.get("losses")),
            "ties": _to_int(outcome.get("ties")),
            "pct": _to_float(outcome.get("percentage")),
        })
    return out


def map_scoreboard(scoreboard_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Current week matchups
    scoreboard = scoreboard_json["fantasy_content"]["league"][1]["scoreboard"]
    matchups = scoreboard.get("0", {}).get("matchups")
    if not matchups:
        return []
    out = []
    for wrapped in _collection_values(matchups):
        matchup = wrapped.get("matchup") if isinstance(wrapped, dict) else None
        if not matchup:
            continue
        week_val = matchup.get("week", scoreboard.get("week"))
        teams_container = matchup.get("0", {}).get("teams", {})
        pair = []
        for team_wrapper in _collection_values(teams_container):
            team_payload = team_wrapper.get("team") if isinstance(team_wrapper, dict) else None
            if not team_payload or not isinstance(team_payload, list):
                continue
            meta = _flatten_kv(team_payload[0] if len(team_payload) else [])
            stats_block = team_payload[1] if len(team_payload) > 1 and isinstance(team_payload[1], dict) else {}
            points = stats_block.get("team_points", {}).get("total")
            proj = stats_block.get("team_projected_points", {}).get("total") if "team_projected_points" in stats_block else None
            pair.append({
                "team_key": meta.get("team_key"),
                "name": meta.get("name"),
                "points": _maybe_float(points) or 0.0,
                "proj": _maybe_float(proj),
            })
        out.append({"week": _to_int(week_val), "teams": pair})
    return out


def map_roster(roster_json: Dict[str, Any]) -> Dict[str, Any]:
    # Flatten a team roster
    team = roster_json["fantasy_content"]["team"]
    meta = _flatten_kv(team[0] if team and isinstance(team[0], list) else [])
    roster_block = team[1]["roster"] if len(team) > 1 and isinstance(team[1], dict) else {}
    players = roster_block.get("0", {}).get("players") if isinstance(roster_block, dict) else roster_block.get("players")
    players = players if players is not None else roster_block
    out = []
    for idx, player_wrapper in enumerate(_collection_values(players)):
        player_sections = player_wrapper.get("player") if isinstance(player_wrapper, dict) else None
        if not player_sections or not isinstance(player_sections, list):
            continue
        pmeta = _flatten_kv(player_sections[0] if len(player_sections) else [])
        eligible = []
        for pos in pmeta.get("eligible_positions", []):
            if isinstance(pos, dict):
                slot = pos.get("position") or pos.get("name") or pos.get("_")
                if slot:
                    eligible.append(slot)
        selected_position = None
        points_total: Optional[float] = None
        projected_total: Optional[float] = None
        for section in player_sections[1:]:
            if not isinstance(section, dict):
                continue
            pos_block = None
            if "selected_position" in section:
                pos_block = section["selected_position"]
            elif "starting_position" in section:
                pos_block = section["starting_position"]
            if pos_block is not None and selected_position is None:
                selected_position = _extract_slot_value(pos_block)
            if "player_points" in section and points_total is None:
                pts_block = section["player_points"]
                if isinstance(pts_block, dict):
                    points_total = _maybe_float(pts_block.get("total"))
            if "player_projected_points" in section and projected_total is None:
                proj_block = section["player_projected_points"]
                if isinstance(proj_block, dict):
                    projected_total = _maybe_float(proj_block.get("total"))
        bench_slots = {"BN", "BENCH"}
        slot_upper = (selected_position or "").upper()
        on_bench = slot_upper in bench_slots
        on_injured_reserve = slot_upper.startswith("IR") or slot_upper in {"IL", "DL"}
        out.append({
            "player_key": pmeta.get("player_key"),
            "name": pmeta.get("name", {}).get("full") if isinstance(pmeta.get("name"), dict) else pmeta.get("name"),
            "eligible_positions": eligible,
            "selected_position": selected_position,
            "on_bench": on_bench,
            "on_injured_reserve": on_injured_reserve,
            "points": points_total,
            "projected_points": projected_total,
            "_order": idx,
        })
    def _category(player: Dict[str, Any]) -> int:
        if player["on_injured_reserve"]:
            return 2
        if player["on_bench"]:
            return 1
        return 0
    out.sort(key=lambda p: (_category(p), p["_order"]))
    for player in out:
        player.pop("_order", None)
    return {"team_key": meta.get("team_key"), "name": meta.get("name"), "players": out}


def map_teams(teams_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Produce a simple list of teams in the league payload with slugs for file naming.
    """
    teams_block = teams_json["fantasy_content"]["league"][1]["teams"]
    out = []
    for wrapped in _collection_values(teams_block):
        payload = wrapped.get("team") if isinstance(wrapped, dict) else None
        if not payload or not isinstance(payload, list):
            continue
        meta = _flatten_kv(payload[0] if len(payload) else [])
        team_key = meta.get("team_key")
        name = meta.get("name")
        if not team_key or not name:
            continue
        slug = team_key.replace(".", "-")
        out.append({"team_key": team_key, "name": name, "slug": slug})
    return out
