import os
import bcrypt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from flask_cors import CORS

# ========================
# APP SETUP
# ========================
app = Flask(__name__, template_folder='templates')

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///db.sqlite3"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "supersecret")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devsecret")

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
jwt = JWTManager(app)

# ========================
# MODELS
# ========================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    ai_provider = db.Column(db.String(50), default='mock')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========================
# INIT DATABASE
# ========================
with app.app_context():
    db.create_all()
    if not User.query.first():
        hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        admin = User(username="admin", password=hashed)
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin: admin / admin123")

# ========================
# ROUTES
# ========================
@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "database": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get("username")).first()
    if not user or not bcrypt.checkpw(data.get("password", "").encode(), user.password.encode()):
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_access_token(identity=user.id)
    return jsonify({"token": token, "user": {"id": user.id, "username": user.username}})

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data.get("username")).first():
        return jsonify({"error": "Username taken"}), 409
    hashed = bcrypt.hashpw(data.get("password", "").encode(), bcrypt.gensalt()).decode()
    user = User(username=data.get("username"), password=hashed)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=user.id)
    return jsonify({"token": token, "user": {"id": user.id, "username": user.username}}), 201

@app.route("/api/conversations", methods=["GET"])
@jwt_required()
def get_conversations():
    user_id = get_jwt_identity()
    convs = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).all()
    return jsonify([{"id": c.id, "title": c.title, "ai_provider": c.ai_provider, "updated_at": c.updated_at.isoformat()} for c in convs])

@app.route("/api/conversation", methods=["POST"])
@jwt_required()
def create_conversation():
    user_id = get_jwt_identity()
    data = request.json
    conv = Conversation(user_id=user_id, title=data.get("title", f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"), ai_provider=data.get("ai_provider", "mock"))
    db.session.add(conv)
    db.session.commit()
    return jsonify({"id": conv.id, "title": conv.title}), 201

@app.route("/api/conversation/<int:conv_id>", methods=["GET"])
@jwt_required()
def get_conversation(conv_id):
    user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return jsonify({"error": "Not found"}), 404
    messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at).all()
    return jsonify({"id": conv.id, "title": conv.title, "messages": [{"role": m.role, "content": m.content} for m in messages]})

@app.route("/api/conversation/<int:conv_id>", methods=["DELETE"])
@jwt_required()
def delete_conversation(conv_id):
    user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if conv:
        db.session.delete(conv)
        db.session.commit()
    return jsonify({"message": "Deleted"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
