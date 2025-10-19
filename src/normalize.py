from typing import Any, Dict, List

def league_key(game_key: str, league_id: str) -> str:
    # Yahoo league keys look like "{game_key}.l.{league_id}", where game_key is numeric
    return f"{game_key}.l.{league_id}"

def extract_game_key(json_games: Dict[str, Any]) -> str:
    # Response: fantasy_content.games[0].game[*].game_key
    games = json_games["fantasy_content"]["games"][0].get("game", [])
    for g in games:
        if "game_key" in g:
            return g["game_key"]
    raise ValueError("No game_key found")

def map_standings(standings_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Flatten league standings into simple rows
    league = standings_json["fantasy_content"]["league"][0]
    teams = standings_json["fantasy_content"]["league"][1]["standings"][0]["teams"]
    out = []
    for t in teams:
        team = t["team"][0]
        name = team[2]["name"]
        team_key = team[0]["team_key"]
        rec = t["team"][1]["team_standings"][0]["outcome_totals"][0]
        out.append({
            "team_key": team_key,
            "name": name,
            "wins": int(rec.get("wins", 0)),
            "losses": int(rec.get("losses", 0)),
            "ties": int(rec.get("ties", 0)),
            "pct": float(rec.get("percentage", 0.0))
        })
    return out

def map_scoreboard(scoreboard_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Current week matchups
    matchups = scoreboard_json["fantasy_content"]["league"][1]["scoreboard"][0]["matchups"]
    out = []
    for m in matchups:
        mj = m["matchup"][0]
        wk = m["matchup"][1]["week"]
        teams = m["matchup"][1]["teams"]
        pair = []
        for tm in teams:
            t0 = tm["team"][0]
            pair.append({
                "team_key": t0["team_key"],
                "name": t0[2]["name"],
                "points": float(tm["team"][1]["team_points"][0]["total"]),
                "proj": float(tm["team"][1].get("team_projected_points", [{"total": 0}])[0]["total"]) if tm["team"][1].get("team_projected_points") else None
            })
        out.append({"week": wk, "teams": pair})
    return out

def map_roster(roster_json: Dict[str, Any]) -> Dict[str, Any]:
    # Flatten a team roster
    team = roster_json["fantasy_content"]["team"][0]
    team_key = team["team_key"]
    name = team[2]["name"]
    players = roster_json["fantasy_content"]["team"][1]["roster"][0]["players"]
    out = []
    for p in players:
        pj = p["player"][0]
        out.append({
            "player_key": pj["player_key"],
            "name": pj[2]["name"]["full"],
            "eligible_positions": [pos["_"] for pos in pj.get("eligible_positions", []) if isinstance(pos, dict)]
        })
    return {"team_key": team_key, "name": name, "players": out}
