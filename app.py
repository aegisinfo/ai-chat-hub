import os, json, uuid, subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy

# =========================
# INIT
# =========================
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

# FIX DB PATH (NO MORE ERROR)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(INSTANCE, "local.db")
db = SQLAlchemy(app)

socketio = SocketIO(app, cors_allowed_origins="*")

# =========================
# MODELS
# =========================
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile"
]

# =========================
# DATABASE
# =========================
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100))
    prompt = db.Column(db.Text)
    response = db.Column(db.Text)

# =========================
# FILE STORAGE
# =========================
UPLOAD = "uploads"
os.makedirs(UPLOAD, exist_ok=True)

file_context = {}

# =========================
# AI ROUTER
# =========================
def generate_ai(prompt):
    if not groq_client:
        return "[ERROR] Missing GROQ_API_KEY"

    for model in MODELS:
        try:
            res = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return res.choices[0].message.content
        except:
            continue

    return "[ERROR] All models failed"

# =========================
# STREAMING
# =========================
def stream_ai(prompt):
    if not groq_client:
        yield "[ERROR] Missing GROQ_API_KEY"
        return

    for model in MODELS:
        try:
            stream = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )

            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield token
            return
        except:
            continue

    yield "[ERROR] All models failed"

# =========================
# SANDBOX
# =========================
os.makedirs("sandbox", exist_ok=True)

def run_code(code):
    fname = f"sandbox/{uuid.uuid4().hex}.py"
    with open(fname, "w") as f:
        f.write(code)

    try:
        res = subprocess.run(
            ["python3", fname],
            capture_output=True,
            text=True,
            timeout=5
        )
        return res.stdout + res.stderr
    except:
        return "Execution failed"

# =========================
# FILE PROCESSING
# =========================
from PyPDF2 import PdfReader
import pandas as pd

def process_file(path):
    if path.endswith(".pdf"):
        reader = PdfReader(path)
        text = ""
        for p in reader.pages:
            text += p.extract_text() or ""
        return text[:3000]

    if path.endswith(".csv"):
        df = pd.read_csv(path)
        return df.head().to_string()

    return open(path).read()[:3000]

# =========================
# AGENT
# =========================
def agent_plan(prompt):
    system = """
Respond ONLY JSON:
{ "action": "code/file/final", "input": "..." }
"""
    return generate_ai(system + prompt)

def run_agent(prompt):
    for _ in range(3):
        try:
            plan = json.loads(agent_plan(prompt))
        except:
            return generate_ai(prompt)

        if plan["action"] == "final":
            return plan["input"]

        if plan["action"] == "file":
            prompt += process_file("uploads/" + plan["input"])

        if plan["action"] == "code":
            result = run_code(plan["input"])
            prompt += result

    return generate_ai(prompt)

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return "AEGIS RUNNING"

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    path = os.path.join(UPLOAD, f.filename)
    f.save(path)

    file_context[f.filename] = process_file(path)

    return jsonify({"filename": f.filename})

@app.route("/chats")
def chats():
    data = Conversation.query.all()
    return jsonify([
        {"room": c.room, "title": c.prompt[:30]}
        for c in data
    ])

@app.route("/chat/<room>")
def chat(room):
    data = Conversation.query.filter_by(room=room).all()
    return jsonify([
        {"prompt": c.prompt, "response": c.response}
        for c in data
    ])

# =========================
# SOCKET
# =========================

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="gevent",
    message_queue="redis://localhost:6379/0"
)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

@socketio.on("join")
def join(data):
    join_room(data["room"])

@socketio.on("message")
def handle(data):
    prompt = data["prompt"]
    room = data["room"]

    emit("message", {"text": prompt}, room=room)

    # AGENT
    response = run_agent(prompt)

    full = ""
    for token in response:
        full += token
        emit("ai_stream", {"token": token}, room=room)

    db.session.add(Conversation(room=room, prompt=prompt, response=full))
    db.session.commit()

# =========================
# START
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    socketio.run(app, host="0.0.0.0", port=5000)
