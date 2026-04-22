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

<<<<<<< HEAD
# Database configuration
=======
# Database
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///db.sqlite3"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
<<<<<<< HEAD
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "supersecretkey123")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devsecretkey456")
=======
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "supersecret")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devsecret")
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
jwt = JWTManager(app)

<<<<<<< HEAD
print(f"✅ Database: {'PostgreSQL (Railway)' if 'postgresql' in DATABASE_URL else 'SQLite (Local)'}")

=======
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8
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
<<<<<<< HEAD
# DATABASE INITIALIZATION
# ========================
with app.app_context():
    db.create_all()
    
    # Create admin user if no users exist
=======
# INIT DATABASE
# ========================
with app.app_context():
    db.create_all()
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8
    if not User.query.first():
        hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        admin = User(username="admin", password=hashed)
        db.session.add(admin)
        db.session.commit()
<<<<<<< HEAD
        print("✅ Admin user created: admin / admin123")
    
    # Create demo user
    if not User.query.filter_by(username="demo").first():
        hashed = bcrypt.hashpw(b"demo123", bcrypt.gensalt()).decode()
        demo = User(username="demo", password=hashed)
        db.session.add(demo)
        db.session.commit()
        print("✅ Demo user created: demo / demo123")

# ========================
# AUTHENTICATION ROUTES
=======
        print("✅ Admin: admin / admin123")

# ========================
# ROUTES
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8
# ========================
@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/health")
def health():
<<<<<<< HEAD
    return jsonify({
        "status": "healthy",
        "database": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite",
        "timestamp": datetime.utcnow().isoformat()
    })
=======
    return jsonify({"status": "healthy", "database": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"})
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
<<<<<<< HEAD
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password required"}), 400
    
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not bcrypt.checkpw(data["password"].encode(), user.password.encode()):
        return jsonify({"error": "Invalid credentials"}), 401
    
=======
    user = User.query.filter_by(username=data.get("username")).first()
    if not user or not bcrypt.checkpw(data.get("password", "").encode(), user.password.encode()):
        return jsonify({"error": "Invalid credentials"}), 401
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8
    token = create_access_token(identity=user.id)
    return jsonify({"token": token, "user": {"id": user.id, "username": user.username}})

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
<<<<<<< HEAD
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
        return jsonify({"token": token, "user": {"id": new_user.id, "username": new_user.username}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create user"}), 500

# ========================
# CONVERSATION ROUTES
# ========================
=======
    if User.query.filter_by(username=data.get("username")).first():
        return jsonify({"error": "Username taken"}), 409
    hashed = bcrypt.hashpw(data.get("password", "").encode(), bcrypt.gensalt()).decode()
    user = User(username=data.get("username"), password=hashed)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=user.id)
    return jsonify({"token": token, "user": {"id": user.id, "username": user.username}}), 201

>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8
@app.route("/api/conversations", methods=["GET"])
@jwt_required()
def get_conversations():
    user_id = get_jwt_identity()
<<<<<<< HEAD
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).all()
    return jsonify([{
        "id": c.id,
        "title": c.title,
        "ai_provider": c.ai_provider,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat()
    } for c in conversations])
=======
    convs = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).all()
    return jsonify([{"id": c.id, "title": c.title, "ai_provider": c.ai_provider, "updated_at": c.updated_at.isoformat()} for c in convs])
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8

@app.route("/api/conversation", methods=["POST"])
@jwt_required()
def create_conversation():
    user_id = get_jwt_identity()
    data = request.json
<<<<<<< HEAD
    title = data.get("title", f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    ai_provider = data.get("ai_provider", "mock")
    
    conversation = Conversation(user_id=user_id, title=title, ai_provider=ai_provider)
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify({"id": conversation.id, "title": conversation.title, "ai_provider": conversation.ai_provider}), 201
=======
    conv = Conversation(user_id=user_id, title=data.get("title", f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"), ai_provider=data.get("ai_provider", "mock"))
    db.session.add(conv)
    db.session.commit()
    return jsonify({"id": conv.id, "title": conv.title}), 201
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8

@app.route("/api/conversation/<int:conv_id>", methods=["GET"])
@jwt_required()
def get_conversation(conv_id):
    user_id = get_jwt_identity()
<<<<<<< HEAD
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
=======
    conv = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return jsonify({"error": "Not found"}), 404
    messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at).all()
    return jsonify({"id": conv.id, "title": conv.title, "messages": [{"role": m.role, "content": m.content} for m in messages]})
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8

@app.route("/api/conversation/<int:conv_id>", methods=["DELETE"])
@jwt_required()
def delete_conversation(conv_id):
    user_id = get_jwt_identity()
<<<<<<< HEAD
    conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted"})

@app.route("/api/conversation/<int:conv_id>/message", methods=["POST"])
@jwt_required()
def add_message(conv_id):
    """Add a message to a conversation"""
    user_id = get_jwt_identity()
    conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    data = request.json
    if not data or 'role' not in data or 'content' not in data:
        return jsonify({"error": "Role and content required"}), 400
    
    message = Message(
        conversation_id=conv_id,
        role=data['role'],
        content=data['content']
    )
    db.session.add(message)
    conversation.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat()
    }), 201

# ========================
# EXPORT/IMPORT ROUTES
# ========================
@app.route("/api/export/<int:conv_id>", methods=["GET"])
@jwt_required()
def export_conversation(conv_id):
    """Export a single conversation"""
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
            "messages": [{"role": m.role, "content": m.content, "timestamp": m.created_at.isoformat()} for m in messages]
        })
    elif format_type == 'txt':
        txt_content = f"Title: {conversation.title}\n"
        txt_content += f"Exported: {datetime.utcnow().isoformat()}\n"
        txt_content += "="*50 + "\n\n"
        for msg in messages:
            txt_content += f"[{msg.role.upper()}]\n{msg.content}\n{'-'*30}\n"
        return jsonify({"text": txt_content})
    
    return jsonify({"error": "Invalid format"}), 400

@app.route("/api/batch-export", methods=["POST"])
@jwt_required()
def batch_export():
    """Export multiple conversations at once"""
    user_id = get_jwt_identity()
    data = request.json
    conversation_ids = data.get('conversation_ids', [])
    
    if not conversation_ids:
        return jsonify({"error": "No conversation IDs provided"}), 400
    
    conversations = Conversation.query.filter(
        Conversation.id.in_(conversation_ids),
        Conversation.user_id == user_id
    ).all()
    
    exports = []
    for conv in conversations:
        messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
        exports.append({
            "id": conv.id,
            "title": conv.title,
            "ai_provider": conv.ai_provider,
            "created_at": conv.created_at.isoformat(),
            "messages": [{"role": m.role, "content": m.content, "timestamp": m.created_at.isoformat()} for m in messages]
        })
    
    return jsonify({
        "exported_at": datetime.utcnow().isoformat(),
        "total_conversations": len(exports),
        "conversations": exports
    })

@app.route("/api/import", methods=["POST"])
@jwt_required()
def import_conversation():
    """Import a conversation from text"""
    user_id = get_jwt_identity()
    data = request.json
    
    if not data or 'content' not in data:
        return jsonify({"error": "No content provided"}), 400
    
    content = data['content']
    title = data.get('title', f"Imported {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    
    # Parse the conversation
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
    
    # Create conversation
    conversation = Conversation(user_id=user_id, title=title, ai_provider='imported')
    db.session.add(conversation)
    db.session.commit()
    
    # Add messages
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
    port = int(os.getenv("PORT", 5001))
    print(f"\n🚀 AI Chat Hub Running")
    print(f"📍 URL: http://localhost:{port}")
    print(f"📝 Default login: admin / admin123")
    print(f"👥 Demo login: demo / demo123")
    print(f"💾 Database: {'Railway PostgreSQL' if 'postgresql' in DATABASE_URL else 'SQLite (Local)'}")
    print(f"\n✨ Features:")
    print(f"   • User registration and login")
    print(f"   • Create/delete conversations")
    print(f"   • Export single conversation (JSON/TXT)")
    print(f"   • Export all conversations (JSON)")
    print(f"   • Import conversations from text files")
    print(f"\n🌐 Server starting...\n")
    
    app.run(host="0.0.0.0", port=port, debug=False)
=======
    conv = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if conv:
        db.session.delete(conv)
        db.session.commit()
    return jsonify({"message": "Deleted"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
>>>>>>> e406735af56ccc005304ba41e0a22cf84f2489c8
