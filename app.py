import os
import bcrypt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///db.sqlite3"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "supersecretkey123"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
app.config["SECRET_KEY"] = "devsecretkey456"

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Models
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

# Create tables
with app.app_context():
    db.create_all()
    if not User.query.first():
        hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        admin = User(username="admin", password=hashed)
        db.session.add(admin)
        db.session.commit()
    if not User.query.filter_by(username="demo").first():
        hashed = bcrypt.hashpw(b"demo123", bcrypt.gensalt()).decode()
        demo = User(username="demo", password=hashed)
        db.session.add(demo)
        db.session.commit()

# Routes
@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

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

@app.route("/api/conversation/<int:conv_id>/message", methods=["POST"])
@jwt_required()
def add_message(conv_id):
    user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    data = request.json
    msg = Message(conversation_id=conv_id, role=data['role'], content=data['content'])
    db.session.add(msg)
    conv.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"id": msg.id}), 201

@app.route("/api/export/<int:conv_id>", methods=["GET"])
@jwt_required()
def export_conversation(conv_id):
    user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return jsonify({"error": "Not found"}), 404
    messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at).all()
    format_type = request.args.get('format', 'json')
    if format_type == 'json':
        return jsonify({"title": conv.title, "messages": [{"role": m.role, "content": m.content} for m in messages]})
    elif format_type == 'txt':
        txt = f"Title: {conv.title}\n{'='*50}\n\n"
        for m in messages:
            txt += f"[{m.role.upper()}]\n{m.content}\n{'-'*30}\n"
        return jsonify({"text": txt})
    return jsonify({"error": "Invalid format"}), 400

@app.route("/api/batch-export", methods=["POST"])
@jwt_required()
def batch_export():
    user_id = get_jwt_identity()
    data = request.json
    conv_ids = data.get('conversation_ids', [])
    convs = Conversation.query.filter(Conversation.id.in_(conv_ids), Conversation.user_id == user_id).all()
    exports = []
    for conv in convs:
        messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
        exports.append({"id": conv.id, "title": conv.title, "messages": [{"role": m.role, "content": m.content} for m in messages]})
    return jsonify({"total": len(exports), "conversations": exports})

@app.route("/api/import", methods=["POST"])
@jwt_required()
def import_conversation():
    user_id = get_jwt_identity()
    data = request.json
    content = data.get('content', '')
    title = data.get('title', f"Imported {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    messages = []
    current_role = None
    current_content = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith(('user:', 'human:', 'you:')):
            if current_content:
                messages.append({'role': current_role or 'user', 'content': '\n'.join(current_content)})
            current_role = 'user'
            current_content = [line.split(':', 1)[1].strip() if ':' in line else line]
        elif lower.startswith(('assistant:', 'ai:', 'bot:')):
            if current_content:
                messages.append({'role': current_role or 'user', 'content': '\n'.join(current_content)})
            current_role = 'assistant'
            current_content = [line.split(':', 1)[1].strip() if ':' in line else line]
        else:
            current_content.append(line)
    if current_content:
        messages.append({'role': current_role or 'user', 'content': '\n'.join(current_content)})
    if not messages:
        return jsonify({"error": "Could not parse"}), 400
    conv = Conversation(user_id=user_id, title=title, ai_provider='imported')
    db.session.add(conv)
    db.session.commit()
    for msg in messages:
        db.session.add(Message(conversation_id=conv.id, role=msg['role'], content=msg['content']))
    db.session.commit()
    return jsonify({"conversation_id": conv.id, "message_count": len(messages)}), 201

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
