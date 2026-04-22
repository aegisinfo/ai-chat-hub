import os
import bcrypt
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, decode_token, get_jwt_identity,
    jwt_required
)
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import os
import sys

# Fix for Python 3.13 compatibility
try:
    import distutils.util
except ImportError:
    # For Python 3.13+, distutils is removed
    pass

# Set environment variable for eventlet
os.environ['EVENTLET_NO_DISTUTILS'] = '1'

# ========================
# DATABASE CONFIGURATION
# ========================
app = Flask(__name__, static_folder='static', template_folder='templates')

# Get DATABASE_URL from Railway environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Convert postgres:// to postgresql:// for SQLAlchemy (Railway uses postgres://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to SQLite for local development
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///db.sqlite3"
    print("⚠️ Using SQLite (local development)")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "supersecretkey123")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devsecretkey456")

# CORS for online access
CORS(app, supports_credentials=True, origins=[
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5001",
    "https://*.railway.app",
    "https://*.railway.internal"
])

db = SQLAlchemy(app)
jwt = JWTManager(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    ping_timeout=60,
    ping_interval=25
)

print(f"✅ Database: {'PostgreSQL (Railway)' if 'postgresql' in DATABASE_URL else 'SQLite (Local)'}")

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
# DATABASE INITIALIZATION
# ========================
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin user if no users exist
        if not User.query.first():
            hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            admin = User(username="admin", password=hashed)
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created: admin / admin123")
        
        # Create demo user
        if not User.query.filter_by(username="demo").first():
            hashed = bcrypt.hashpw(b"demo123", bcrypt.gensalt()).decode()
            demo = User(username="demo", password=hashed)
            db.session.add(demo)
            db.session.commit()
            print("✅ Demo user created: demo / demo123")

# ========================
# SOCKET AUTHENTICATION
# ========================
clients = {}

@socketio.on("connect")
def handle_connect():
    auth = request.auth
    if not auth or 'token' not in auth:
        print("❌ No token provided")
        return False
    
    try:
        data = decode_token(auth['token'])
        user_id = data["sub"]
        clients[request.sid] = user_id
        print(f"✅ User {user_id} connected")
        emit("connected", {"status": "ok", "user_id": user_id})
        return True
    except Exception as e:
        print(f"❌ Token error: {e}")
        return False

@socketio.on("disconnect")
def handle_disconnect():
    if request.sid in clients:
        user_id = clients.pop(request.sid)
        print(f"👋 User {user_id} disconnected")

@socketio.on("join")
def handle_join(data):
    conversation_id = data.get("conversation_id")
    if conversation_id:
        join_room(f"conv_{conversation_id}")
        emit("joined", {"conversation_id": conversation_id})

@socketio.on("message")
def handle_message(data):
    conversation_id = data.get("conversation_id")
    content = data.get("content")
    ai_provider = data.get("ai_provider", "mock")
    user_id = clients.get(request.sid)
    
    if not conversation_id or not content or not user_id:
        emit("error", {"message": "Invalid request"})
        return
    
    try:
        conversation = Conversation.query.get(conversation_id)
        if not conversation or conversation.user_id != user_id:
            emit("error", {"message": "Conversation not found"})
            return
        
        # Save user message
        user_msg = Message(conversation_id=conversation_id, role="user", content=content)
        db.session.add(user_msg)
        db.session.commit()
        
        emit("ai_thinking", {"status": "thinking"}, room=f"conv_{conversation_id}")
        
        # Generate AI response (mock for demo)
        full_response = f"🤖 {ai_provider.upper()}: Thanks for your message! This is a demo response from your AI Chat Hub running on Railway."
        
        # Stream response word by word
        for word in full_response.split():
            emit("ai_stream", {"chunk": word + " ", "full": full_response}, room=f"conv_{conversation_id}")
            import time
            time.sleep(0.05)
        
        # Save AI response
        ai_msg = Message(conversation_id=conversation_id, role="assistant", content=full_response)
        db.session.add(ai_msg)
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        emit("ai_complete", {"full_response": full_response}, room=f"conv_{conversation_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        emit("error", {"message": str(e)})

# ========================
# API ROUTES
# ========================
@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "database": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password required"}), 400
    
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not bcrypt.checkpw(data["password"].encode(), user.password.encode()):
        return jsonify({"error": "Invalid credentials"}), 401
    
    token = create_access_token(identity=user.id)
    return jsonify({
        "token": token, 
        "user": {"id": user.id, "username": user.username}
    })

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password required"}), 400
    
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 409
    
    if len(data["username"]) < 3 or len(data["password"]) < 3:
        return jsonify({"error": "Username and password must be at least 3 characters"}), 400
    
    hashed_password = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
    new_user = User(username=data["username"], password=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        token = create_access_token(identity=new_user.id)
        return jsonify({
            "token": token, 
            "user": {"id": new_user.id, "username": new_user.username}
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create user"}), 500

@app.route("/api/conversations", methods=["GET"])
@jwt_required()
def get_conversations():
    user_id = get_jwt_identity()
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).all()
    return jsonify([{
        "id": c.id,
        "title": c.title,
        "ai_provider": c.ai_provider,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat()
    } for c in conversations])

@app.route("/api/conversation", methods=["POST"])
@jwt_required()
def create_conversation():
    user_id = get_jwt_identity()
    data = request.json
    title = data.get("title", f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    ai_provider = data.get("ai_provider", "mock")
    
    conversation = Conversation(
        user_id=user_id,
        title=title,
        ai_provider=ai_provider
    )
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify({
        "id": conversation.id,
        "title": conversation.title,
        "ai_provider": conversation.ai_provider
    }), 201

@app.route("/api/conversation/<int:conv_id>", methods=["GET"])
@jwt_required()
def get_conversation(conv_id):
    user_id = get_jwt_identity()
    conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at).all()
    return jsonify({
        "id": conversation.id,
        "title": conversation.title,
        "ai_provider": conversation.ai_provider,
        "messages": [{
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        } for m in messages]
    })

@app.route("/api/conversation/<int:conv_id>", methods=["DELETE"])
@jwt_required()
def delete_conversation(conv_id):
    user_id = get_jwt_identity()
    conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted"})

@app.route("/api/export/<int:conv_id>", methods=["GET"])
@jwt_required()
def export_conversation(conv_id):
    user_id = get_jwt_identity()
    conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at).all()
    format_type = request.args.get('format', 'json')
    
    if format_type == 'json':
        return jsonify({
            "title": conversation.title,
            "exported_at": datetime.utcnow().isoformat(),
            "messages": [{"role": m.role, "content": m.content} for m in messages]
        })
    elif format_type == 'txt':
        txt = f"Title: {conversation.title}\n{'='*50}\n\n"
        for msg in messages:
            txt += f"[{msg.role.upper()}]\n{msg.content}\n{'-'*30}\n"
        return jsonify({"text": txt})
    
    return jsonify({"error": "Invalid format"}), 400

@app.route("/api/import", methods=["POST"])
@jwt_required()
def import_conversation():
    user_id = get_jwt_identity()
    data = request.json
    
    if not data or 'content' not in data:
        return jsonify({"error": "No content provided"}), 400
    
    content = data['content']
    title = data.get('title', f"Imported {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    
    # Parse text format
    messages = []
    current_role = None
    current_content = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        lower_line = line.lower()
        if lower_line.startswith(('user:', 'human:', 'you:')):
            if current_content:
                messages.append({'role': current_role or 'user', 'content': '\n'.join(current_content)})
            current_role = 'user'
            current_content = [line.split(':', 1)[1].strip() if ':' in line else line]
        elif lower_line.startswith(('assistant:', 'ai:', 'bot:')):
            if current_content:
                messages.append({'role': current_role or 'user', 'content': '\n'.join(current_content)})
            current_role = 'assistant'
            current_content = [line.split(':', 1)[1].strip() if ':' in line else line]
        else:
            current_content.append(line)
    
    if current_content:
        messages.append({'role': current_role or 'user', 'content': '\n'.join(current_content)})
    
    if not messages:
        return jsonify({"error": "Could not parse conversation"}), 400
    
    conversation = Conversation(user_id=user_id, title=title, ai_provider='imported')
    db.session.add(conversation)
    db.session.commit()
    
    for msg in messages:
        message = Message(conversation_id=conversation.id, role=msg['role'], content=msg['content'])
        db.session.add(message)
    
    db.session.commit()
    
    return jsonify({
        "message": "Imported successfully",
        "conversation_id": conversation.id,
        "message_count": len(messages)
    }), 201

# ========================
# ERROR HANDLERS
# ========================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

# ========================
# RUN THE APP
# ========================
if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5001))
    print(f"\n🚀 AI Chat Hub Running")
    print(f"📍 URL: http://localhost:{port}")
    print(f"📝 Default login: admin / admin123")
    print(f"👥 Demo login: demo / demo123")
    print(f"💾 Database: {'Railway PostgreSQL' if 'postgresql' in DATABASE_URL else 'SQLite (Local)'}")
    print(f"📡 WebSocket: Enabled\n")
    socketio.run(app, host="0.0.0.0", port=port, debug=False)

# ========================
# RUN THE APP
# ========================
if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5001))
    
    # Check if running on Railway (production)
    is_production = os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("DATABASE_URL")
    
    if is_production:
        # Production: Use simpler async mode
        print(f"\n🚀 AI Chat Hub Running on Railway (Production)")
        socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
    else:
        # Development: Use eventlet
        print(f"\n🚀 AI Chat Hub Running (Development)")
        socketio.run(app, host="0.0.0.0", port=port, debug=True)
