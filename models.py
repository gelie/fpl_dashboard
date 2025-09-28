from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, CheckConstraint


class Player(SQLModel, table=True):
    __tablename__ = "players"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    team: str

    # Relationship to Scores
    scores: list["Score"] = Relationship(back_populates="player")

    class Config:
        from_attributes = True


class Score(SQLModel, table=True):
    __tablename__ = "scores"
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="players.id")
    gameweek: int = Field(
        sa_column=Column(Integer, CheckConstraint("gameweek >= 1 AND gameweek <= 38"))
    )
    week_points: int = Field(
        sa_column=Column(Integer, CheckConstraint("week_points >= 0"))
    )
    week_cost: int = Field(sa_column=Column(Integer, CheckConstraint("week_cost >= 0")))
    overall_points: int = Field(
        sa_column=Column(Integer, CheckConstraint("overall_points >= 0")), default=0
    )

    # Relationship to Player
    player: Player = Relationship(back_populates="scores")

    class Config:
        from_attributes = True
        unique_together = ("player_id", "gameweek")


class PlayerForm(SQLModel):
    """Form model for creating/editing players"""

    name: str = ""
    team: str = ""


class ScoreForm(SQLModel):
    """Form model for creating/editing scores"""

    player_id: int = Field(
        foreign_key="players.id", sa_column_kwargs={"nullable": False}
    )
    gameweek: int = 1
    week_points: int = 0
    week_cost: int = 0
    overall_points: int = 0
