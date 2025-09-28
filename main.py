from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Form, HTTPException, Depends, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Session, create_engine, select
from models import Player, Score, PlayerForm
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from collections import defaultdict
import json
import os
from dotenv import load_dotenv
import secrets

# Load environment variables
load_dotenv()

engine = create_engine("sqlite:///fpl.db")
security = HTTPBasic()

# Get admin credentials from environment
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials"""
    is_correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def get_optional_user(request: Request):
    """Get user if authenticated, otherwise return None"""
    try:
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return None
        
        import base64
        encoded_credentials = auth_header.split(" ")[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
        
        is_correct_username = secrets.compare_digest(username, ADMIN_USERNAME)
        is_correct_password = secrets.compare_digest(password, ADMIN_PASSWORD)
        
        if is_correct_username and is_correct_password:
            return username
        return None
    except Exception:
        return None


session = Depends(get_db)


def add_auth_context(request: Request, context: dict):
    """Add authentication context to template context"""
    current_user = get_optional_user(request)
    is_admin = current_user is not None
    context["is_admin"] = is_admin
    context["current_user"] = current_user
    return context


@app.get("/", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request, session: Session = session):
    # Get all scores with player and team information
    scores = session.exec(
        select(Score, Player)
        .join(Player)
        .order_by(Score.gameweek, Player.team, Player.name)
    ).all()

    # Prepare data for weekly scores per team chart
    team_weekly_data = defaultdict(lambda: defaultdict(int))
    team_overall_data = defaultdict(lambda: defaultdict(int))

    # Get all unique teams and gameweeks
    teams = set()
    gameweeks = set()

    for score, player in scores:
        teams.add(player.team)
        gameweeks.add(score.gameweek)

        # Sum weekly points per team per gameweek (gross points)
        team_weekly_data[player.team][score.gameweek] += score.week_points

        # For overall points, we'll calculate cumulative sum per team
        team_overall_data[player.team][score.gameweek] += score.overall_points

    # Sort teams and gameweeks for consistent ordering
    sorted_teams = sorted(teams)
    sorted_gameweeks = sorted(gameweeks) if gameweeks else [1]

    # Prepare chart data for weekly scores
    weekly_chart_data = {"labels": sorted_gameweeks, "datasets": []}

    # Color palette for teams
    colors = [
        "#FF6384",
        "#36A2EB",
        "#FFCE56",
        "#4BC0C0",
        "#9966FF",
        "#FF9F40",
        "#FF6384",
        "#C9CBCF",
        "#4BC0C0",
        "#FF6384",
    ]

    for i, team in enumerate(sorted_teams):
        weekly_data = []
        for gw in sorted_gameweeks:
            weekly_data.append(team_weekly_data[team].get(gw, 0))

        weekly_chart_data["datasets"].append(
            {
                "label": team,
                "data": weekly_data,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)] + "20",  # Add transparency
                "tension": 0.4,
                "fill": False,
            }
        )

    # Prepare chart data for overall points (cumulative)
    overall_chart_data = {"labels": sorted_gameweeks, "datasets": []}

    for i, team in enumerate(sorted_teams):
        # Calculate cumulative overall points per team
        cumulative_data = []
        cumulative_sum = 0

        for gw in sorted_gameweeks:
            # Get the maximum overall_points for this team at this gameweek
            # (since overall_points is already cumulative per player)
            team_players_at_gw = [
                score.overall_points
                for score, player in scores
                if player.team == team and score.gameweek == gw
            ]
            if team_players_at_gw:
                # Sum all players' overall points for this team at this gameweek
                cumulative_sum = sum(team_players_at_gw)
            cumulative_data.append(cumulative_sum)

        overall_chart_data["datasets"].append(
            {
                "label": team,
                "data": cumulative_data,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)] + "20",
                "tension": 0.4,
                "fill": False,
            }
        )

    context = {
        "request": request,
        "title": "Dashboard",
        "weekly_chart_data": json.dumps(weekly_chart_data),
        "overall_chart_data": json.dumps(overall_chart_data),
    }
    context = add_auth_context(request, context)
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/login")
def login_page(current_user: str = Depends(get_current_user)):
    """Protected login endpoint that triggers HTTP Basic Auth"""
    return RedirectResponse("/", status_code=302)


@app.get("/logout-clear")
def logout_clear():
    """Endpoint to clear credentials by returning 401"""
    import time
    
    # Create a unique realm to force credential clearing
    logout_realm = f"Logout-{int(time.time())}"
    
    response = Response(
        content="Credentials cleared", 
        status_code=401,
        headers={
            "WWW-Authenticate": f"Basic realm=\"{logout_realm}\"",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
    return response


@app.get("/players")
def players(request: Request, session: Session = session):
    players = session.exec(select(Player)).all()
    form = PlayerForm()
    
    context = {
        "request": request, 
        "players": players, 
        "form": form, 
        "title": "Players",
    }
    context = add_auth_context(request, context)
    return templates.TemplateResponse("players.html", context)


@app.post("/players")
def create_player(
    name: str = Form(...),
    team: str = Form(...),
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    player = Player(name=name, team=team)
    session.add(player)
    session.commit()
    return RedirectResponse("/players", status_code=302)


@app.post("/players/{player_id}")
def update_player(
    player_id: int,
    name: str = Form(...),
    team: str = Form(...),
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    player.name = name
    player.team = team
    session.add(player)
    session.commit()
    session.refresh(player)
    return RedirectResponse("/players", status_code=302)


@app.delete("/players/{player_id}")
def delete_player(
    player_id: int, 
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    session.delete(player)
    session.commit()
    return RedirectResponse("/players", status_code=302)


@app.post("/players/{player_id}/delete")
def delete_player_form(
    player_id: int, 
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    """Handle player deletion via form submission"""
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    session.delete(player)
    session.commit()
    return RedirectResponse("/players", status_code=302)


@app.get("/scores")
def scores(
    request: Request,
    session: Session = session,
    player_id: Optional[str] = Query(None),
    gameweek: Optional[str] = Query(None),
):
    # Build the query with optional filters
    query = select(Score)

    # Convert string parameters to integers if they're not empty
    player_id_int = None
    gameweek_int = None

    if player_id and player_id.strip():
        try:
            player_id_int = int(player_id)
            query = query.where(Score.player_id == player_id_int)
        except ValueError:
            pass  # Ignore invalid integers

    if gameweek and gameweek.strip():
        try:
            gameweek_int = int(gameweek)
            query = query.where(Score.gameweek == gameweek_int)
        except ValueError:
            pass  # Ignore invalid integers

    scores = session.exec(query).all()
    players = session.exec(select(Player)).all()

    # Get max gameweek from all scores (not filtered)
    all_scores = session.exec(select(Score)).all()
    gameweeks = [s.gameweek for s in all_scores] if all_scores else [0]
    max_gameweek = max(gameweeks) if gameweeks else 0
    next_gameweek = max_gameweek + 1
    
    context = {
        "request": request,
        "scores": scores,
        "players": players,
        "max_gameweek": max_gameweek,
        "next_gameweek": next_gameweek,
        "title": "Scores",
        "player_id": player_id_int,
        "gameweek": gameweek_int,
    }
    context = add_auth_context(request, context)
    return templates.TemplateResponse("scores.html", context)


@app.post("/scores")
async def create_scores_bulk(
    request: Request,
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    """Handle bulk score creation for all players in a gameweek"""
    form_data = await request.form()
    
    # Get the gameweek from form
    gameweek = int(form_data.get("gameweek", 1))
    
    # Get all players
    players = session.exec(select(Player)).all()
    
    for player in players:
        # Get points and cost for this player from form
        week_points_key = f"week_points_{player.id}"
        week_cost_key = f"week_cost_{player.id}"
        
        week_points = form_data.get(week_points_key)
        week_cost = form_data.get(week_cost_key)
        
        # Skip if no data provided for this player
        if not week_points or not week_cost:
            continue
            
        week_points = int(week_points)
        week_cost = int(week_cost)
        
        # Check if score already exists for this player/gameweek
        existing_score = session.exec(
            select(Score).where(
                Score.player_id == player.id,
                Score.gameweek == gameweek
            )
        ).first()
        
        if existing_score:
            # Update existing score
            existing_score.week_points = week_points
            existing_score.week_cost = week_cost
            session.add(existing_score)
        else:
            # Calculate overall_points as sum of all week_points for this player
            existing_scores = session.exec(
                select(Score).where(Score.player_id == player.id)
            ).all()
            total_points = (
                sum((score.week_points - score.week_cost) for score in existing_scores)
                + week_points - week_cost
            )

            # Create new score
            score = Score(
                player_id=player.id,
                gameweek=gameweek,
                week_points=week_points,
                week_cost=week_cost,
                overall_points=total_points,
            )
            session.add(score)
    
    session.commit()
    return RedirectResponse("/scores", status_code=302)


# @app.get("/scores/{score_id}")
# def edit_score(score_id: int, session: Session = session):
#     score = session.get(Score, score_id)
#     if not score:
#         raise HTTPException(status_code=404, detail="Score not found")
#     return templates.TemplateResponse("edit_score.html", {"score": score})


@app.post("/scores/{score_id}")
def update_score(
    score_id: int,
    player_id: int = Form(...),
    gameweek: int = Form(...),
    week_points: int = Form(...),
    week_cost: int = Form(...),
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    score = session.get(Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    # Calculate overall_points per gameweek before updating
    # Get all OTHER scores for this player up to this gameweek (excluding current one)
    other_scores = session.exec(
        select(Score)
        .where(Score.player_id == player_id)
        .where(Score.gameweek <= gameweek)
        .where(Score.id != score_id)
    ).all()

    # Calculate total: sum of other scores + new values for current score
    total_points = sum((s.week_points - s.week_cost) for s in other_scores) + (
        week_points - week_cost
    )

    # Update score with all new values including calculated total
    score.player_id = player_id
    score.gameweek = gameweek
    score.week_points = week_points
    score.week_cost = week_cost
    score.overall_points = total_points
    session.add(score)

    # Recalculate and update overall_points for all subsequent gameweeks
    subsequent_scores = session.exec(
        select(Score)
        .where(Score.player_id == player_id)
        .where(Score.gameweek > gameweek)
        .order_by(Score.gameweek)
    ).all()

    for subsequent_score in subsequent_scores:
        # Get all scores up to this subsequent gameweek
        scores_up_to_week = session.exec(
            select(Score)
            .where(Score.player_id == player_id)
            .where(Score.gameweek <= subsequent_score.gameweek)
        ).all()

        # Calculate cumulative total
        subsequent_total = sum((s.week_points - s.week_cost) for s in scores_up_to_week)

        subsequent_score.overall_points = subsequent_total
        session.add(subsequent_score)

    # Single commit for all changes
    session.commit()
    session.refresh(score)

    print(f"Updated score: {score}")
    return RedirectResponse("/scores", status_code=302)


@app.delete("/scores/{score_id}")
def delete_score(
    score_id: int, 
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    score = session.get(Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    session.delete(score)
    session.commit()
    return RedirectResponse("/scores", status_code=302)


@app.post("/scores/{score_id}/delete")
def delete_score_form(
    score_id: int, 
    session: Session = session,
    current_user: str = Depends(get_current_user),
):
    """Handle score deletion via form submission"""
    score = session.get(Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    session.delete(score)
    session.commit()
    return RedirectResponse("/scores", status_code=302)


# Vercel handler
handler = app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app="main:app", host="0.0.0.0", port=8000, reload=True)
