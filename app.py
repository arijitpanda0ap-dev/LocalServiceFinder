from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            service TEXT,
            location TEXT,
            problem TEXT,
            emergency TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            service TEXT,
            location TEXT,
            rating REAL,
            total_reviews INTEGER DEFAULT 0,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- REQUEST ----------
@app.route("/request", methods=["GET", "POST"])
def request_service():
    if request.method == "POST":
        name = request.form["name"]
        service = request.form["service"]
        location = request.form["location"]
        problem = request.form["problem"]
        emergency = request.form.get("emergency")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("INSERT INTO requests (name, service, location, problem, emergency) VALUES (?, ?, ?, ?, ?)",
                       (name, service, location, problem, emergency))

        if emergency:
            cursor.execute("""
                SELECT name, rating FROM providers
                WHERE service=? AND location=?
                LIMIT 1
            """, (service, location))
        else:
            cursor.execute("""
                SELECT name, rating FROM providers
                WHERE service=? AND location=?
                ORDER BY rating DESC
                LIMIT 1
            """, (service, location))

        matched = cursor.fetchone()
        conn.commit()
        conn.close()

        if matched:
            return render_template("match.html",
                                   name=name,
                                   service=service,
                                   provider=matched[0],
                                   rating=matched[1])
        else:
            return "<h2>No provider available in your area.</h2><a href='/'>Back</a>"

    return render_template("request.html")

# ---------- REVIEW SYSTEM ----------
@app.route("/review", methods=["POST"])
def review():
    provider = request.form["provider"]
    new_rating = float(request.form["rating"])

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT rating, total_reviews FROM providers WHERE name=?", (provider,))
    data = cursor.fetchone()

    if data:
        current_rating, total_reviews = data
        updated_reviews = total_reviews + 1
        updated_rating = ((current_rating * total_reviews) + new_rating) / updated_reviews

        cursor.execute("""
            UPDATE providers
            SET rating=?, total_reviews=?
            WHERE name=?
        """, (updated_rating, updated_reviews, provider))

    conn.commit()
    conn.close()

    return redirect("/")

# ---------- PROVIDER REGISTER ----------
@app.route("/provider_register", methods=["GET", "POST"])
def provider_register():
    if request.method == "POST":
        name = request.form["name"]
        service = request.form["service"]
        location = request.form["location"]
        rating = request.form["rating"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO providers (name, service, location, rating, password)
            VALUES (?, ?, ?, ?, ?)
        """, (name, service, location, rating, password))
        conn.commit()
        conn.close()

        return redirect("/provider_login")

    return render_template("provider_register.html")

# ---------- LOGIN ----------
@app.route("/provider_login", methods=["GET", "POST"])
def provider_login():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM providers WHERE name=? AND password=?", (name, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["provider"] = name
            return redirect("/provider_dashboard")
        else:
            return "Invalid Login"

    return render_template("provider_login.html")

# ---------- DASHBOARD ----------
@app.route("/provider_dashboard")
def provider_dashboard():
    if "provider" not in session:
        return redirect("/provider_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT service, location, rating, total_reviews 
        FROM providers 
        WHERE name=?
    """, (session["provider"],))

    provider_data = cursor.fetchone()
    conn.close()

    if provider_data:
        return render_template(
            "dashboard.html",
            data=provider_data,
            name=session["provider"],
            rating=provider_data[2],
            reviews=provider_data[3]
        )
    else:
        return "Provider data not found. Please login again."

# ---------- ADMIN PANEL ----------
@app.route("/admin")
def admin_panel():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name, service, location, rating, total_reviews FROM providers")
    providers = cursor.fetchall()

    cursor.execute("SELECT name, service, location, problem, emergency FROM requests")
    requests_data = cursor.fetchall()

    conn.close()

    return render_template("admin.html", providers=providers, requests=requests_data)

if __name__ == "__main__":
    app.run(debug=True)