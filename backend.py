
from dotenv import load_dotenv
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
import os
import requests
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Text, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSON

# Load environment variables
load_dotenv()
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")

# Base class
class Base(DeclarativeBase):
    pass

# Flask + SQLAlchemy setup
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Models
class Users(db.Model):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    user_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    user_name = Column(Text)

class Decks(db.Model):
    __tablename__ = "decks"
    __table_args__ = {"schema": "public"}

    deck_id = Column(UUID(as_uuid=True))
    deck_version_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    deck_name = Column(Text)
    version_name = Column(Text)
    user_id = Column(UUID(as_uuid=True))
    format = Column(Text)
    uploaded_on = Column(TIMESTAMP)

class DeckCards(db.Model):
    __tablename__ = "deck_cards"
    __table_args__ = {"schema": "public"}

    card_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    card_name = Column(Text)
    deck_version_id = Column(UUID(as_uuid=True))
    set_code = Column(Text)
    quantity = Column(Integer)
    uploaded_on = Column(TIMESTAMP)
    tag = Column(Text)
    colour = Column(Text)
    format = Column(Text)
    category = Column(Text)

class Game(db.Model):
    __tablename__ = "games"
    __table_args__ = {"schema": "public"}

    primary_key = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    deck_version_id1 = Column(UUID(as_uuid=True))
    deck_version_id2 = Column(UUID(as_uuid=True))
    deck_version_id3 = Column(UUID(as_uuid=True))
    deck_version_id4 = Column(UUID(as_uuid=True))
    job_id = Column(UUID(as_uuid=True))
    game_count = Column(Integer)
    deck1_wins = Column(Integer)
    deck2_wins = Column(Integer)
    deck3_wins = Column(Integer)
    deck4_wins = Column(Integer)
    turn_counts = Column(JSON)
    device_id = Column(UUID(as_uuid=True))
    format = Column(Text)
    created_on = Column(TIMESTAMP)
    finished_on = Column(TIMESTAMP)

def update_card_database():
  '''
  Update local json card database from Scryfall API
  https://api.scryfall.com/bulk-data
  '''
  print('TODO: Update card database')

# Endpoints
@app.route("/deck/create", methods=['POST'])
def deck_create():
    """
    Create or update a deck

    Parameters:
      - deck_name: String
      - user_id: UUID
      - version_name (optional): String
      - format: String
      - cards: [{cardname: quantity}]
    """
    valid_formats = ["constructed", "commander", "jumpstart"]
    if request.form["format"] not in valid_formats:
        raise ValueError(f"'format' must be one of {valid_formats}")



    # TODO: Check all cards against Scryfall bulk download








if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)