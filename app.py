```python
import os, time, jwt
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from groq import Groq
import stripe

# ---------------- CONFIG ----------------

app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///instance/local.db"
)

db = SQLAlchemy(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PLANS = {"free": 100, "pro": 5000}

# ---------------- MODELS ----------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    plan = db.Column(db.String(50), default="free")
    usage = db.Column(db.Integer, default=0)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    room = db.Column(db.String(120))
    prompt = db.Column(db.Text)
    response = db.Column(db.Text)

# ---------------- INIT ----------------

with app.app_context():
    os.makedirs("instance", exist_ok=True)
    db.create_all()

# ---------------- AUTH ----------------

def create_token(uid):
    return jwt.encode(
        {"user_id": uid, "exp": datetime.utcnow()+timedelta(days=7)},
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

def get_user():
    auth = request.headers.get("Authorization")
    if not auth: return None
    token = auth.split(" ")[1]
    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return User.query.get(data["user_id"])
    except:
        return None

@app.route("/register", methods=["POST"])
def register():
    d = request.json
    if User.query.filter_by(username=d["username"]).first():
        return jsonify({"error":"exists"})
    u = User(username=d["username"],
             password=generate_password_hash(d["password"]))
    db.session.add(u); db.session.commit()
    return jsonify({"ok":True})

@app.route("/login", methods=["POST"])
def login():
    d = request.json
    u = User.query.filter_by(username=d["username"]).first()
    if not u or not check_password_hash(u.password, d["password"]):
        return jsonify({"error":"invalid"})
    return jsonify({"token":create_token(u.id)})

# ---------------- AI ----------------

def ai(prompt):
    try:
        r = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}]
        )
        return r.choices[0].message.content
    except Exception as e:
        return f"ERROR: {e}"

# ---------------- CHAT ----------------

@app.route("/chats")
def chats():
    u = get_user()
    if not u: return jsonify([])
    rooms = db.session.query(Message.room)\
        .filter_by(user_id=u.id).distinct().all()
    return jsonify([{"room":r[0],"title":r[0]} for r in rooms])

@app.route("/chat/<room>")
def chat(room):
    u = get_user()
    if not u: return jsonify([])
    msgs = Message.query.filter_by(user_id=u.id, room=room).all()
    return jsonify([{"prompt":m.prompt,"response":m.response} for m in msgs])

# ---------------- STRIPE ----------------

@app.route("/billing", methods=["POST"])
def billing():
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price":"price_xxx","quantity":1}],
        success_url="http://localhost:5000/chat-page",
        cancel_url="http://localhost:5000/chat-page"
    )
    return jsonify({"url":session.url})

# ---------------- SOCKET ----------------

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")


@socketio.on("connect")
def connect(auth):
    if not auth or not auth.get("token"):
        return False

@socketio.on("join")
def join(data):
    join_room(data["room"])

@socketio.on("message")
def message(data):
    token = data.get("token")
    try:
        user_id = jwt.decode(token, app.config["SECRET_KEY"],
                             algorithms=["HS256"])["user_id"]
    except:
        return

    user = User.query.get(user_id)

    if user.usage >= PLANS[user.plan]:
        emit("ai_stream", {"token":"⚠️ limit reached"})
        return

    user.usage += 1
    db.session.commit()

    room = data["room"]
    prompt = data["prompt"]

    emit("message", {"text":prompt}, room=room)

    res = ai(prompt)

    for w in res.split():
        emit("ai_stream", {"token":w+" "}, room=room)
        time.sleep(0.02)

    db.session.add(Message(
        user_id=user.id,
        room=room,
        prompt=prompt,
        response=res
    ))
    db.session.commit()

# ---------------- UI ----------------

@app.route("/")
def home():
    return send_from_directory("templates","index.html")

@app.route("/chat-page")
def chat_page():
    return send_from_directory("templates","chat.html")

# ---------------- RUN ----------------

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
```

