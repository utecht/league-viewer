import os, json, pathlib, datetime
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from yahoo_client import YahooClient
from normalize import extract_game_key, league_key, map_standings, map_scoreboard, map_roster, map_teams

load_dotenv()

CLIENT_ID = os.environ["YAHOO_CLIENT_ID"]
CLIENT_SECRET = os.environ["YAHOO_CLIENT_SECRET"]
REFRESH = os.environ["YAHOO_REFRESH_TOKEN"]
LEAGUE_ID = os.environ["LEAGUE_ID"]
GAME_CODE = os.environ["GAME_CODE"]       # e.g. nfl
SEASON = os.environ["SEASON"]             # e.g. 2025
TEAM_ID = os.getenv("TEAM_ID")            # optional

DATA_DIR = pathlib.Path("data")
SITE_DIR = pathlib.Path("site")
TPL_DIR = pathlib.Path("src/templates")

DATA_DIR.mkdir(exist_ok=True)
SITE_DIR.mkdir(exist_ok=True)

jinja = Environment(
    loader=FileSystemLoader(TPL_DIR),
    autoescape=select_autoescape(["html"])
)
render = lambda tpl, **ctx: jinja.get_template(tpl).render(**ctx)

yc = YahooClient(CLIENT_ID, CLIENT_SECRET, REFRESH)

# 1) Turn GAME_CODE + SEASON into numeric game_key (Yahoo requires numeric)
games = yc.get_json(f"games;game_codes={GAME_CODE};seasons={SEASON}")
game_key = extract_game_key(games)

# 2) Build league_key and fetch league info
lkey = league_key(game_key, LEAGUE_ID)

standings = yc.get_json(f"league/{lkey}/standings")
scoreboard = yc.get_json(f"league/{lkey}/scoreboard")
teams = yc.get_json(f"league/{lkey}/teams")

# 3) Normalize
stand_rows = map_standings(standings)
score_rows = map_scoreboard(scoreboard)

# 4) Optionally fetch your team roster (if TEAM_ID set)
my_team = None
if TEAM_ID:
    # Yahoo team_key: {game_key}.l.{league_id}.t.{team_id}
    team_key = f"{lkey}.t.{TEAM_ID}"
    roster = yc.get_json(f"team/{team_key}/roster")
    my_team = map_roster(roster)

# 5) Persist raw for debugging
ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
json.dump({"fetched_at": ts, "payload": standings}, open(DATA_DIR/"standings.json", "w"))
json.dump({"fetched_at": ts, "payload": scoreboard}, open(DATA_DIR/"scoreboard.json", "w"))
json.dump({"fetched_at": ts, "payload": teams}, open(DATA_DIR/"teams.json", "w"))
if my_team:
    json.dump({"fetched_at": ts, "payload": my_team}, open(DATA_DIR/"my_team.json", "w"))

# 6) Render pages
index_html = render("index.html",
    updated_at=ts,
    standings=sorted(stand_rows, key=lambda r: (-r["pct"], -r["wins"])),
    scoreboard=score_rows,
    season=SEASON
)
open(SITE_DIR/"index.html", "w").write(index_html)

# Per-team pages (names + links)
team_list = map_teams(teams)

# Basic roster snapshot per team (optional: skip to reduce calls)
for t in team_list:
    roster_json = yc.get_json(f"team/{t['team_key']}/roster")
    roster_norm = map_roster(roster_json)
    html = render("team.html",
        updated_at=ts,
        team=roster_norm,
        season=SEASON
    )
    open(SITE_DIR/f"{t['slug']}.html", "w").write(html)

# Week page (single 'current' week)
if score_rows:
    wk = score_rows[0]["week"]
    week_html = render("week.html",
        updated_at=ts,
        week=wk,
        matchups=score_rows
    )
    open(SITE_DIR/f"week-{wk}.html", "w").write(week_html)

# Simple sitemap
open(SITE_DIR/"robots.txt", "w").write("User-agent: *\nAllow: /\n")
open(SITE_DIR/"sitemap.txt", "w").write("\n".join(
    ["https://<YOUR_USERNAME>.github.io/<YOUR_REPO>/"] +
    [f"https://<YOUR_USERNAME>.github.io/<YOUR_REPO>/{t['slug']}.html" for t in team_list] +
    ([f"https://<YOUR_USERNAME>.github.io/<YOUR_REPO>/week-{score_rows[0]['week']}.html"] if score_rows else [])
))
print("✅ Build complete.")
