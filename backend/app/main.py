from fastapi import FastAPI, Query
from typing import Optional
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load env and connect to Postgres
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://alexmitchell@localhost:5432/nba_data")
engine = create_engine(DATABASE_URL)

app = FastAPI(title="NBA Betting API")

@app.get("/")
def root():
    return {"message": "NBA Betting API is running"}

# Generic games endpoint (works for ANY team, by id or by stored name; optional season filter)
@app.get("/games")
def get_games(
    team_id: Optional[int] = Query(None, description="NBA team id (e.g., 1610612743 for Nuggets)"),
    team_name: Optional[str] = Query(None, description="Exact stored name (e.g., 'Nuggets')"),
    season: Optional[int] = Query(None, description="Season start year, e.g., 2024 for 2024–25"),
    limit: int = 200
):
    if not team_id and not team_name:
        return {"error": "Provide team_id or team_name"}

    where = []
    params = {"limit": limit}

    if team_id:
        where.append("(home_team_id = :tid OR away_team_id = :tid)")
        params["tid"] = team_id
    if team_name:
        where.append("(home_team_name = :tname OR away_team_name = :tname)")
        params["tname"] = team_name

    if season is not None:
        # NBA season window: Oct 1 (season) → Jul 1 (season+1)
        where.append("game_date >= :start AND game_date < :end")
        params["start"] = f"{season}-10-01"
        params["end"]   = f"{season+1}-07-01"

    sql = f"""
      SELECT game_id, game_date, game_type,
             home_team_name, home_score,
             away_team_name, away_score
      FROM games
      WHERE {' AND '.join(where)}
      ORDER BY game_date DESC
      LIMIT :limit;
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]

# Player last-10 vs season averages (ANY player)
@app.get("/players/agg")
def player_agg(
    person_id: int = Query(..., description="players.person_id"),
    season: Optional[int] = Query(None, description="Season start year, e.g., 2024"),
    last_n: int = 10
):
    season_clause = "AND ps.game_date >= :start AND ps.game_date < :end" if season is not None else ""
    sql = f"""
      WITH ranked AS (
        SELECT
          ps.person_id,
          (p.first_name || ' ' || p.last_name) AS player_name,
          ps.game_date::date AS game_date,
          ps.points, ps.assists, ps.rebounds_total AS rebounds,
          (ps.points + ps.assists + ps.rebounds_total) AS pra,
          ROW_NUMBER() OVER (PARTITION BY ps.person_id ORDER BY ps.game_date DESC) AS rn
        FROM player_statistics ps
        JOIN players p ON p.person_id = ps.person_id
        WHERE ps.person_id = :pid
          {season_clause}
      )
      SELECT
        MAX(player_name) AS player_name,
        AVG(points)  FILTER (WHERE rn <= :n) AS last_n_pts,
        AVG(rebounds)FILTER (WHERE rn <= :n) AS last_n_reb,
        AVG(assists) FILTER (WHERE rn <= :n) AS last_n_ast,
        AVG(pra)     FILTER (WHERE rn <= :n) AS last_n_pra,
        AVG(points)  AS season_pts,
        AVG(rebounds)AS season_reb,
        AVG(assists) AS season_ast,
        AVG(pra)     AS season_pra
      FROM ranked;
    """
    params = {"pid": person_id, "n": last_n}
    if season is not None:
        params["start"] = f"{season}-10-01"
        params["end"]   = f"{season+1}-07-01"

    with engine.connect() as conn:
        row = conn.execute(text(sql), params).mappings().first()
        return dict(row) if row else {}

@app.get("/players/gamelogs")
def player_gamelogs(
    person_id: int,
    season: int | None = None,         # e.g., 2024 for 2024–25
    opponent: str | None = None,       # exact stored name, e.g., 'Lakers'
    home: bool | None = None,          # True/False
    game_type: str | None = None,      # 'Regular Season' or 'Playoffs'
    limit: int = 50,
    offset: int = 0
):
    wh, params = ["ps.person_id = :pid"], {"pid": person_id, "limit": limit, "offset": offset}

    if season is not None:
        wh.append("ps.game_date >= :start AND ps.game_date < :end")
        params["start"] = f"{season}-10-01"
        params["end"]   = f"{season+1}-07-01"
    if opponent:
        wh.append("ps.opponent_team_name = :opp")
        params["opp"] = opponent
    if home is not None:
        wh.append("ps.home = :home")
        params["home"] = home
    if game_type:
        wh.append("ps.game_type = :gt")
        params["gt"] = game_type

    sql = f"""
      SELECT
        ps.game_id,
        ps.game_date::date AS game_date,
        ps.player_team_name AS team,
        ps.opponent_team_name AS opp,
        ps.home AS is_home,
        ps.game_type,
        ps.points, ps.assists, ps.rebounds_total AS rebounds,
        (ps.points + ps.assists + ps.rebounds_total) AS pra,
        ps.three_pointers_made AS tpm,
        ps.field_goals_attempted AS fga, ps.field_goals_made AS fgm,
        ps.free_throws_attempted AS fta, ps.free_throws_made AS ftm,
        ps.plus_minus_points AS plus_minus,
        ps.num_minutes AS minutes
      FROM player_statistics ps
      WHERE {" AND ".join(wh)}
      ORDER BY ps.game_date DESC
      LIMIT :limit OFFSET :offset;
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]

@app.get("/players/search")
def players_search(q: str, limit: int = 20):
    sql = """
      SELECT person_id,
             (first_name || ' ' || last_name) AS player_name
      FROM players
      WHERE (first_name || ' ' || last_name) ILIKE :q
      ORDER BY player_name
      LIMIT :limit;
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"q": f"%{q}%", "limit": limit}).mappings().all()
        return [dict(r) for r in rows]