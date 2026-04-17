import pytest
import base64
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool
import os

from main import app, get_db
from models import Player, Score


@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with dependency override"""
    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="sample_players")
def sample_players_fixture(session: Session):
    """Create sample players for testing"""
    players = [
        Player(name="Mohamed Salah", team="Liverpool"),
        Player(name="Erling Haaland", team="Manchester City"),
        Player(name="Harry Kane", team="Tottenham"),
    ]
    for player in players:
        session.add(player)
    session.commit()
    for player in players:
        session.refresh(player)
    return players


@pytest.fixture(name="sample_scores")
def sample_scores_fixture(session: Session, sample_players):
    """Create sample scores for testing"""
    scores = [
        Score(player_id=sample_players[0].id, gameweek=1, week_points=12, week_cost=2, overall_points=10),
        Score(player_id=sample_players[0].id, gameweek=2, week_points=8, week_cost=1, overall_points=17),
        Score(player_id=sample_players[1].id, gameweek=1, week_points=15, week_cost=3, overall_points=12),
        Score(player_id=sample_players[1].id, gameweek=2, week_points=6, week_cost=0, overall_points=18),
        Score(player_id=sample_players[2].id, gameweek=1, week_points=9, week_cost=1, overall_points=8),
    ]
    for score in scores:
        session.add(score)
    session.commit()
    for score in scores:
        session.refresh(score)
    return scores


@pytest.fixture(name="auth_headers")
def auth_headers_fixture():
    """Create authentication headers for admin user"""
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "password")
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


class TestDashboard:
    """Test dashboard view and chart data generation"""

    def test_dashboard_empty_data(self, client: TestClient):
        """Test dashboard with no data"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Dashboard" in response.text
        
        # Check that chart elements are present
        assert "weeklyChart" in response.text
        assert "overallChart" in response.text
        assert "Weekly Scores" in response.text
        assert "Overall Points" in response.text

    def test_dashboard_with_data(self, client: TestClient, sample_players, sample_scores):
        """Test dashboard with sample data"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Dashboard" in response.text
        
        # Verify team names appear in the response
        assert "Liverpool" in response.text
        assert "Manchester City" in response.text
        assert "Tottenham" in response.text

    def test_dashboard_chart_data_structure(self, client: TestClient, sample_players, sample_scores):
        """Test that chart data has correct structure"""
        response = client.get("/")
        assert response.status_code == 200
        
        # Verify the response contains chart-related JavaScript
        assert "const weeklyData" in response.text
        assert "const overallData" in response.text
        assert "new ChartJS" in response.text

    def test_dashboard_authentication_context(self, client: TestClient, auth_headers):
        """Test dashboard shows admin context when authenticated"""
        response = client.get("/", headers=auth_headers)
        assert response.status_code == 200
        # The template should show admin-specific content when authenticated


class TestAuthentication:
    """Test authentication endpoints"""

    def test_login_without_credentials(self, client: TestClient):
        """Test login endpoint without credentials returns 401"""
        response = client.get("/login")
        assert response.status_code == 401

    def test_login_with_valid_credentials(self, client: TestClient, auth_headers):
        """Test login with valid credentials redirects to dashboard"""
        response = client.get("/login", headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/"

    def test_login_with_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials returns 401"""
        invalid_credentials = base64.b64encode("wrong:credentials".encode()).decode()
        headers = {"Authorization": f"Basic {invalid_credentials}"}
        response = client.get("/login", headers=headers)
        assert response.status_code == 401

    def test_logout_clear(self, client: TestClient):
        """Test logout endpoint clears credentials"""
        response = client.get("/logout-clear")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert "Logout-" in response.headers["WWW-Authenticate"]
        assert response.text == "Credentials cleared"


class TestPlayers:
    """Test player CRUD operations"""

    def test_get_players_page(self, client: TestClient):
        """Test players page loads correctly"""
        response = client.get("/players")
        assert response.status_code == 200
        assert "Players" in response.text

    def test_get_players_with_data(self, client: TestClient, sample_players):
        """Test players page displays existing players"""
        response = client.get("/players")
        assert response.status_code == 200
        assert "Mohamed Salah" in response.text
        assert "Liverpool" in response.text
        assert "Erling Haaland" in response.text
        assert "Manchester City" in response.text

    def test_create_player_without_auth(self, client: TestClient):
        """Test creating player without authentication fails"""
        response = client.post("/players", data={"name": "Test Player", "team": "Test Team"})
        assert response.status_code == 401

    def test_create_player_with_auth(self, client: TestClient, auth_headers, session: Session):
        """Test creating player with authentication"""
        response = client.post(
            "/players",
            data={"name": "Test Player", "team": "Test Team"},
            headers=auth_headers,
            follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/players"
        
        # Verify player was created
        players = session.exec(select(Player).where(Player.name == "Test Player")).all()
        assert len(players) == 1
        assert players[0].team == "Test Team"

    def test_update_player_without_auth(self, client: TestClient, sample_players):
        """Test updating player without authentication fails"""
        player_id = sample_players[0].id
        response = client.post(
            f"/players/{player_id}",
            data={"name": "Updated Name", "team": "Updated Team"}
        )
        assert response.status_code == 401

    def test_update_player_with_auth(self, client: TestClient, auth_headers, sample_players, session: Session):
        """Test updating player with authentication"""
        player_id = sample_players[0].id
        response = client.post(
            f"/players/{player_id}",
            data={"name": "Updated Salah", "team": "Updated Liverpool"},
            headers=auth_headers,
            follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/players"
        
        # Verify player was updated
        updated_player = session.get(Player, player_id)
        assert updated_player.name == "Updated Salah"
        assert updated_player.team == "Updated Liverpool"

    def test_update_nonexistent_player(self, client: TestClient, auth_headers):
        """Test updating non-existent player returns 404"""
        response = client.post(
            "/players/999",
            data={"name": "Test", "team": "Test"},
            headers=auth_headers,
            follow_redirects=False
        )
        assert response.status_code == 404

    def test_delete_player_without_auth(self, client: TestClient, sample_players):
        """Test deleting player without authentication fails"""
        player_id = sample_players[0].id
        response = client.delete(f"/players/{player_id}")
        assert response.status_code == 401

    def test_delete_player_with_auth(self, client: TestClient, auth_headers, sample_players, session: Session):
        """Test deleting player with authentication"""
        player_id = sample_players[0].id
        response = client.delete(f"/players/{player_id}", headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/players"
        
        # Verify player was deleted
        deleted_player = session.get(Player, player_id)
        assert deleted_player is None

    def test_delete_player_form_with_auth(self, client: TestClient, auth_headers, sample_players, session: Session):
        """Test deleting player via form submission"""
        player_id = sample_players[1].id  # Use second player since first might be deleted
        response = client.post(f"/players/{player_id}/delete", headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/players"
        
        # Verify player was deleted
        deleted_player = session.get(Player, player_id)
        assert deleted_player is None

    def test_delete_nonexistent_player(self, client: TestClient, auth_headers):
        """Test deleting non-existent player returns 404"""
        response = client.delete("/players/999", headers=auth_headers, follow_redirects=False)
        assert response.status_code == 404


class TestScores:
    """Test score CRUD operations and filtering"""

    def test_get_scores_page(self, client: TestClient):
        """Test scores page loads correctly"""
        response = client.get("/scores")
        assert response.status_code == 200
        assert "Scores" in response.text

    def test_get_scores_with_data(self, client: TestClient, sample_players, sample_scores):
        """Test scores page displays existing scores"""
        response = client.get("/scores")
        assert response.status_code == 200
        # Should contain score data
        assert "12" in response.text  # week_points from sample data
        assert "15" in response.text  # week_points from sample data

    def test_filter_scores_by_player(self, client: TestClient, sample_players, sample_scores):
        """Test filtering scores by player"""
        player_id = sample_players[0].id
        response = client.get(f"/scores?player_id={player_id}")
        assert response.status_code == 200
        # Should only show scores for the selected player

    def test_filter_scores_by_gameweek(self, client: TestClient, sample_players, sample_scores):
        """Test filtering scores by gameweek"""
        response = client.get("/scores?gameweek=1")
        assert response.status_code == 200
        # Should only show scores for gameweek 1

    def test_filter_scores_by_both(self, client: TestClient, sample_players, sample_scores):
        """Test filtering scores by both player and gameweek"""
        player_id = sample_players[0].id
        response = client.get(f"/scores?player_id={player_id}&gameweek=1")
        assert response.status_code == 200

    def test_filter_scores_invalid_parameters(self, client: TestClient, sample_players, sample_scores):
        """Test filtering with invalid parameters is handled gracefully"""
        response = client.get("/scores?player_id=invalid&gameweek=invalid")
        assert response.status_code == 200
        # Should show all scores when parameters are invalid

    def test_create_scores_bulk_without_auth(self, client: TestClient):
        """Test bulk score creation without authentication fails"""
        response = client.post("/scores", data={"gameweek": "1"})
        assert response.status_code == 401

    def test_create_scores_bulk_with_auth(self, client: TestClient, auth_headers, sample_players, session: Session):
        """Test bulk score creation with authentication"""
        form_data = {
            "gameweek": "3",
            f"week_points_{sample_players[0].id}": "10",
            f"week_cost_{sample_players[0].id}": "1",
            f"week_points_{sample_players[1].id}": "12",
            f"week_cost_{sample_players[1].id}": "2",
        }
        
        response = client.post("/scores", data=form_data, headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/scores"
        
        # Verify scores were created
        scores = session.exec(select(Score).where(Score.gameweek == 3)).all()
        assert len(scores) == 2

    def test_update_score_without_auth(self, client: TestClient, sample_scores):
        """Test updating score without authentication fails"""
        score_id = sample_scores[0].id
        response = client.post(
            f"/scores/{score_id}",
            data={
                "player_id": sample_scores[0].player_id,
                "gameweek": sample_scores[0].gameweek,
                "week_points": "20",
                "week_cost": "3"
            }
        )
        assert response.status_code == 401

    def test_update_score_with_auth(self, client: TestClient, auth_headers, sample_scores, session: Session):
        """Test updating score with authentication"""
        score_id = sample_scores[0].id
        response = client.post(
            f"/scores/{score_id}",
            data={
                "player_id": sample_scores[0].player_id,
                "gameweek": sample_scores[0].gameweek,
                "week_points": "20",
                "week_cost": "3"
            },
            headers=auth_headers,
            follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/scores"
        
        # Verify score was updated
        updated_score = session.get(Score, score_id)
        assert updated_score.week_points == 20
        assert updated_score.week_cost == 3

    def test_update_nonexistent_score(self, client: TestClient, auth_headers):
        """Test updating non-existent score returns 404"""
        response = client.post(
            "/scores/999",
            data={
                "player_id": "1",
                "gameweek": "1",
                "week_points": "10",
                "week_cost": "1"
            },
            headers=auth_headers,
            follow_redirects=False
        )
        assert response.status_code == 404

    def test_delete_score_without_auth(self, client: TestClient, sample_scores):
        """Test deleting score without authentication fails"""
        score_id = sample_scores[0].id
        response = client.delete(f"/scores/{score_id}")
        assert response.status_code == 401

    def test_delete_score_with_auth(self, client: TestClient, auth_headers, sample_scores, session: Session):
        """Test deleting score with authentication"""
        score_id = sample_scores[0].id
        response = client.delete(f"/scores/{score_id}", headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/scores"
        
        # Verify score was deleted
        deleted_score = session.get(Score, score_id)
        assert deleted_score is None

    def test_delete_score_form_with_auth(self, client: TestClient, auth_headers, sample_scores, session: Session):
        """Test deleting score via form submission"""
        score_id = sample_scores[1].id  # Use second score since first might be deleted
        response = client.post(f"/scores/{score_id}/delete", headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/scores"
        
        # Verify score was deleted
        deleted_score = session.get(Score, score_id)
        assert deleted_score is None

    def test_delete_nonexistent_score(self, client: TestClient, auth_headers):
        """Test deleting non-existent score returns 404"""
        response = client.delete("/scores/999", headers=auth_headers, follow_redirects=False)
        assert response.status_code == 404


class TestScoreCalculations:
    """Test score calculation logic"""

    def test_overall_points_calculation_on_update(self, client: TestClient, auth_headers, sample_players, session: Session):
        """Test that overall points are calculated correctly when updating scores"""
        # Create initial scores
        player_id = sample_players[0].id
        
        # Create score for gameweek 1
        score1 = Score(player_id=player_id, gameweek=1, week_points=10, week_cost=2, overall_points=8)
        session.add(score1)
        session.commit()
        session.refresh(score1)
        
        # Create score for gameweek 2
        score2 = Score(player_id=player_id, gameweek=2, week_points=15, week_cost=3, overall_points=20)
        session.add(score2)
        session.commit()
        session.refresh(score2)
        
        # Update gameweek 1 score
        response = client.post(
            f"/scores/{score1.id}",
            data={
                "player_id": player_id,
                "gameweek": 1,
                "week_points": "12",  # Changed from 10 to 12
                "week_cost": "1"      # Changed from 2 to 1
            },
            headers=auth_headers,
            follow_redirects=False
        )
        assert response.status_code == 302
        
        # Verify calculations
        session.refresh(score1)
        session.refresh(score2)
        
        # Gameweek 1: 12 - 1 = 11
        assert score1.overall_points == 11
        # Gameweek 2: (12 - 1) + (15 - 3) = 11 + 12 = 23
        assert score2.overall_points == 23


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_form_data_bulk_scores(self, client: TestClient, auth_headers, sample_players):
        """Test bulk score creation with empty form data"""
        form_data = {"gameweek": "1"}  # No player data
        response = client.post("/scores", data=form_data, headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302  # Should redirect even with no data

    def test_partial_form_data_bulk_scores(self, client: TestClient, auth_headers, sample_players, session: Session):
        """Test bulk score creation with partial form data"""
        form_data = {
            "gameweek": "1",
            f"week_points_{sample_players[0].id}": "10",
            # Missing week_cost for player 0
            f"week_cost_{sample_players[1].id}": "2",
            # Missing week_points for player 1
        }
        
        response = client.post("/scores", data=form_data, headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        
        # Should not create any scores due to missing data
        scores = session.exec(select(Score).where(Score.gameweek == 1)).all()
        assert len(scores) == 0

    def test_duplicate_score_creation(self, client: TestClient, auth_headers, sample_players, sample_scores, session: Session):
        """Test creating duplicate scores updates existing ones"""
        # Try to create score for existing player/gameweek combination
        existing_score = sample_scores[0]
        form_data = {
            "gameweek": str(existing_score.gameweek),
            f"week_points_{existing_score.player_id}": "99",
            f"week_cost_{existing_score.player_id}": "5",
        }
        
        response = client.post("/scores", data=form_data, headers=auth_headers, follow_redirects=False)
        assert response.status_code == 302
        
        # Verify score was updated, not duplicated
        session.refresh(existing_score)
        assert existing_score.week_points == 99
        assert existing_score.week_cost == 5


if __name__ == "__main__":
    pytest.main([__file__])
