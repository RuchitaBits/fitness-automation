import os
import sqlite3
from datetime import date
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "instance" / "aceest.db"))

PROGRAMS = {
    "Fat Loss": {"factor": 22, "workout": "Strength and conditioning", "nutrition": "Protein-rich meals with a measured calorie deficit."},
    "Muscle Gain": {"factor": 35, "workout": "Progressive resistance training", "nutrition": "Protein-rich meals with a measured calorie surplus."},
    "Beginner": {"factor": 26, "workout": "Full-body fundamentals", "nutrition": "Balanced meals focused on consistency and recovery."},
}
EXERCISES = {
    "beginner": ["Push-Up", "Goblet Squat", "Dumbbell Row", "Plank"],
    "intermediate": ["Bench Press", "Barbell Row", "Leg Press", "Lateral Raise"],
    "advanced": ["Deadlift", "Overhead Press", "Pull-Up", "Kettlebell Swings"],
}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=str(DATABASE),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db()

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def index():
        return render_template("index.html", programs=PROGRAMS)

    @app.route("/health")
    def health():
        return jsonify(status="healthy")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        clients = query_db("SELECT * FROM clients ORDER BY name")
        workouts = query_db("SELECT workouts.*, clients.name AS client_name FROM workouts JOIN clients ON clients.id = workouts.client_id ORDER BY workout_date DESC LIMIT 5")
        active = sum(client["membership_status"] == "Active" for client in clients)
        return render_template("dashboard.html", clients=clients, workouts=workouts, active=active, programs=PROGRAMS)

    @app.route("/clients")
    @login_required
    def clients():
        return render_template("clients.html", clients=query_db("SELECT * FROM clients ORDER BY name"), programs=PROGRAMS)

    @app.route("/clients/add", methods=("POST",))
    @login_required
    def add_client():
        form = request.form
        try:
            name = form.get("name", "").strip()
            age, height, weight, target_weight = (float(form.get(key, 0)) for key in ("age", "height", "weight", "target_weight"))
            program = form.get("program", "")
            if not name or program not in PROGRAMS or min(age, height, weight) <= 0:
                raise ValueError
            execute_db("INSERT INTO clients (name, age, height, weight, program, estimated_calories, target_weight, target_adherence, membership_status, membership_end) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, age, height, weight, program, calculate_calories(weight, program), target_weight, float(form.get("target_adherence", 80)), form.get("membership_status", "Active"), form.get("membership_end", "")))
            flash("Client added.", "success")
        except (TypeError, ValueError):
            flash("Please provide valid client details.", "error")
        return redirect(url_for("clients"))

    @app.route("/clients/<int:client_id>")
    @login_required
    def client_detail(client_id):
        client = query_db("SELECT * FROM clients WHERE id = ?", (client_id,), one=True)
        if client is None:
            return render_template("error.html", message="Client not found."), 404
        progress = query_db("SELECT * FROM progress WHERE client_id = ? ORDER BY week_date DESC", (client_id,))
        metrics = query_db("SELECT * FROM metrics WHERE client_id = ? ORDER BY metric_date DESC", (client_id,))
        return render_template("client_detail.html", client=client, progress=progress, metrics=metrics)

    @app.route("/clients/<int:client_id>/update", methods=("POST",))
    @login_required
    def update_client(client_id):
        form = request.form
        try:
            weight = float(form["weight"])
            program = form["program"]
            if weight <= 0 or program not in PROGRAMS:
                raise ValueError
            execute_db("UPDATE clients SET weight = ?, program = ?, estimated_calories = ?, membership_status = ?, membership_end = ? WHERE id = ?", (weight, program, calculate_calories(weight, program), form.get("membership_status", "Active"), form.get("membership_end", ""), client_id))
            flash("Client updated.", "success")
        except (KeyError, TypeError, ValueError):
            flash("Invalid update details.", "error")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.route("/clients/<int:client_id>/delete", methods=("POST",))
    @login_required
    def delete_client(client_id):
        execute_db("DELETE FROM clients WHERE id = ?", (client_id,))
        flash("Client deleted.", "success")
        return redirect(url_for("clients"))

    @app.route("/programs")
    @login_required
    def programs():
        return render_template("programs.html", programs=PROGRAMS)

    @app.route("/programs/generate", methods=("POST",))
    @login_required
    def generate_program():
        program = request.form.get("program", "Beginner")
        level = request.form.get("experience", "beginner").lower()
        if program not in PROGRAMS or level not in EXERCISES:
            flash("Select a valid program and experience level.", "error")
            return redirect(url_for("programs"))
        generated = list(EXERCISES[level])
        session["generated_program"] = {"program": program, "experience": level.title(), "exercises": generated}
        return render_template("programs.html", programs=PROGRAMS, generated=session["generated_program"])

    @app.route("/workouts")
    @login_required
    def workouts():
        clients = query_db("SELECT id, name FROM clients ORDER BY name")
        records = query_db("SELECT workouts.*, clients.name AS client_name FROM workouts JOIN clients ON clients.id = workouts.client_id ORDER BY workout_date DESC")
        return render_template("workouts.html", clients=clients, workouts=records)

    @app.route("/workouts/add", methods=("POST",))
    @login_required
    def add_workout():
        form = request.form
        try:
            client_id = int(form["client_id"])
            duration = int(form["duration"])
            if duration <= 0 or not query_db("SELECT id FROM clients WHERE id = ?", (client_id,), one=True):
                raise ValueError
            execute_db("INSERT INTO workouts (client_id, workout_date, workout_type, duration, notes) VALUES (?, ?, ?, ?, ?)", (client_id, form.get("workout_date") or date.today().isoformat(), form.get("workout_type", "Strength"), duration, form.get("notes", "").strip()))
            flash("Workout recorded.", "success")
        except (KeyError, TypeError, ValueError):
            flash("Please provide valid workout details.", "error")
        return redirect(url_for("workouts"))

    @app.route("/clients/<int:client_id>/progress", methods=("POST",))
    @login_required
    def add_progress(client_id):
        try:
            adherence = float(request.form["adherence"])
            if not 0 <= adherence <= 100:
                raise ValueError
            execute_db("INSERT INTO progress (client_id, week_date, adherence) VALUES (?, ?, ?)", (client_id, request.form.get("week_date") or date.today().isoformat(), adherence))
            flash("Progress saved.", "success")
        except (KeyError, TypeError, ValueError):
            flash("Adherence must be between 0 and 100.", "error")
        return redirect(url_for("client_detail", client_id=client_id))

    return app


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app().config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def current_app():
    from flask import current_app as flask_current_app
    return flask_current_app


def query_db(query, args=(), one=False):
    cursor = get_db().execute(query, args)
    rows = cursor.fetchall()
    cursor.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, args=()):
    db = get_db()
    cursor = db.execute(query, args)
    db.commit()
    return cursor.lastrowid


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age REAL NOT NULL, height REAL NOT NULL, weight REAL NOT NULL, program TEXT NOT NULL, estimated_calories REAL NOT NULL, target_weight REAL NOT NULL, target_adherence REAL NOT NULL, membership_status TEXT NOT NULL, membership_end TEXT);
        CREATE TABLE IF NOT EXISTS progress (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, week_date TEXT NOT NULL, adherence REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, workout_date TEXT NOT NULL, workout_type TEXT NOT NULL, duration INTEGER NOT NULL, notes TEXT);
        CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE, name TEXT NOT NULL, sets INTEGER, reps INTEGER, weight REAL);
        CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, metric_date TEXT NOT NULL, weight REAL, waist REAL, body_fat REAL);
    """)
    username = os.environ.get("DEMO_USERNAME", "admin")
    password_hash = generate_password_hash(os.environ.get("DEMO_PASSWORD", "admin"))
    db.execute(
        "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    db.commit()


def calculate_calories(weight, program):
    if program not in PROGRAMS or float(weight) <= 0:
        raise ValueError("Weight and program must be valid")
    return round(float(weight) * PROGRAMS[program]["factor"], 2)


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))