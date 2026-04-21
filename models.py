# models.py

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    oauth_provider = db.Column(db.String(50))
    created_at = db.Column(db.DateTime)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    plan = db.Column(db.String(50))  # free / pro / enterprise
    stripe_customer_id = db.Column(db.String(120))
    status = db.Column(db.String(50))

class Usage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    tokens_used = db.Column(db.Integer)
    requests = db.Column(db.Integer)
