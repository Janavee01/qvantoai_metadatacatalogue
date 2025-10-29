from flask import Flask, request, jsonify
import sqlite3
from io import BytesIO
from flask import send_file
from flask import Flask, request, jsonify, render_template, send_file
app = Flask(__name__)
ROLE = "admin"   # Change to "viewer" to simulate role-based access

import joblib, os

MODEL_PATH = 'fraud_model.joblib'
model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None

def get_db_connection():
    conn = sqlite3.connect("metadata.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    
    # Metadata table (now includes linked_to)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            tags TEXT,
            description TEXT,
            linked_to TEXT   -- NEW COLUMN to represent lineage link
        )
    """)
    
    # Claims table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_amount REAL,
            claim_history INTEGER,
            fraud_score REAL,
            label TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def score_claim(amount, history):
    score = 0
    if amount > 10000:
        score += 0.7
    if history > 2:
        score += 0.3
    label = "Suspicious" if score >= 0.7 else "OK"
    return score, label



@app.route("/add_asset", methods=["POST"])
def add_asset():
    if ROLE != "admin":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    name = data.get("name")
    type_ = data.get("type")
    tags = data.get("tags")
    description = data.get("description")
    linked_to = data.get("linked_to")  # NEW FIELD

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO metadata (name, type, tags, description, linked_to)
        VALUES (?, ?, ?, ?, ?)
    """, (name, type_, tags, description, linked_to))
    conn.commit()
    conn.close()
    return jsonify({"message": "Asset added successfully"})


@app.route("/assets", methods=["GET"])
def get_assets():
    conn = get_db_connection()
    assets = conn.execute("SELECT * FROM metadata").fetchall()
    conn.close()
    return jsonify([dict(row) for row in assets])


@app.route("/update_asset/<int:id>", methods=["PUT"])
def update_asset(id):
    if ROLE != "admin":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    conn = get_db_connection()
    conn.execute("""
        UPDATE metadata SET name=?, type=?, tags=?, description=? WHERE id=?
    """, (data.get("name"), data.get("type"), data.get("tags"), data.get("description"), id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Asset updated"})


@app.route("/delete_asset/<int:id>", methods=["DELETE"])
def delete_asset(id):
    if ROLE != "admin":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    conn.execute("DELETE FROM metadata WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Asset deleted"})


@app.route("/search", methods=["GET"])
def search_assets():
    tag = request.args.get("tag")
    conn = get_db_connection()
    results = conn.execute("SELECT * FROM metadata WHERE tags LIKE ?", ('%' + tag + '%',)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route("/fraud_score", methods=["POST"])
def fraud_score():
    if ROLE != "admin":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    amount = data.get("claim_amount", 0)
    history = data.get("claim_history", 0)

    # Calculate score and label
    score, label = score_claim(amount, history)

    # Store in DB
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO claims (claim_amount, claim_history, fraud_score, label) VALUES (?, ?, ?, ?)",
        (amount, history, score, label)
    )
    conn.commit()
    conn.close()

    return jsonify({"fraud_score": score, "label": label})

@app.route("/dashboard", methods=["GET"])
def dashboard():
    conn = get_db_connection()

    # Total claims
    total_claims = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    
    # Suspicious claims
    suspicious_claims = conn.execute("SELECT COUNT(*) FROM claims WHERE label='Suspicious'").fetchone()[0]
    
    # Total assets in metadata
    total_assets = conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]

    conn.close()

    # Fraud rate calculation
    fraud_rate = round((suspicious_claims / total_claims * 100) if total_claims else 0, 1)

    # Simple HTML dashboard
    html = f"""
    <h2>Claims Fraud Dashboard</h2>
    <p>Total Claims: {total_claims}</p>
    <p>Suspicious Claims: {suspicious_claims}</p>
    <p>Fraud Rate: {fraud_rate}%</p>
    <p>Total Metadata Assets: {total_assets}</p>
    """
    return html

@app.route("/lineage")
def lineage():
    import networkx as nx
    import matplotlib.pyplot as plt
    from io import BytesIO

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, type, linked_to FROM metadata")
    assets = cursor.fetchall()
    conn.close()

    G = nx.DiGraph()
    seen = set()

    # Add nodes
    for name, typ, linked_to in assets:
        node_key = f"{name}_{typ}"
        if node_key not in seen:
            G.add_node(node_key, label=f"{name}\n({typ})")
            seen.add(node_key)

    # Add edges dynamically from linked_to column
    for name, typ, linked_to in assets:
        if linked_to:
            src = f"{linked_to}_{'Policy' if 'Policy' in linked_to else 'Claim'}"
            dst = f"{name}_{typ}"
            if src in G.nodes and dst in G.nodes:
                G.add_edge(src, dst)

    # Remove isolated nodes
    isolated = list(nx.isolates(G))
    G.remove_nodes_from(isolated)

    # Color by type
    node_colors = []
    for n in G.nodes:
        if "Policy" in n:
            node_colors.append("lightgreen")
        elif "Claim" in n:
            node_colors.append("skyblue")
        elif "ReserveModel" in n:
            node_colors.append("lightcoral")
        else:
            node_colors.append("grey")

    # Draw the graph
    plt.figure(figsize=(10, 7))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'),
            node_size=2500, node_color=node_colors, font_size=10,
            font_weight="bold", arrowsize=20)
    nx.draw_networkx_edges(G, pos, arrowstyle='-|>', arrowsize=20)
    plt.title("Data Lineage: Policy → Claim → ReserveModel")
    plt.axis('off')
    plt.tight_layout()

    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    return send_file(img, mimetype='image/png')


# add this route (place anywhere above if __name__ == "__main__")
@app.route("/lineage_html")
def lineage_html():
    # returns an HTML page that fetches /assets and renders D3 graph
    return render_template("lineage.html")

@app.route('/fraud_score_ml', methods=['POST'])
def fraud_score_ml():
    data = request.get_json()
    amount = float(data.get('claim_amount', 0))
    history = int(data.get('claim_history', 0))
    score, label = score_claim(amount, history)  # keep rule fallback
    if model:
        X = [[amount, history, score]]
        pred = model.predict_proba(X)[0][1]  # probability of suspicious
        ml_label = 'Suspicious' if pred >= 0.5 else 'OK'
        return jsonify({'rule_score': score, 'rule_label': label, 'ml_prob': pred, 'ml_label': ml_label})
    else:
        return jsonify({'rule_score': score, 'rule_label': label, 'ml_available': False})

@app.route("/train_model", methods=["POST"])
def train_model():
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    import joblib

    conn = get_db_connection()
    df = pd.read_sql_query("SELECT claim_amount, claim_history, fraud_score, label FROM claims", conn)
    conn.close()

    if len(df) < 10:
        return jsonify({"message": "Not enough data to train model (>=10 rows needed)"}), 400

    df['label_bin'] = df['label'].apply(lambda x: 1 if x == 'Suspicious' else 0)
    X = df[['claim_amount', 'claim_history', 'fraud_score']].fillna(0)
    y = df['label_bin']

    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X, y)
    joblib.dump(clf, MODEL_PATH)
    global model
    model = clf
    return jsonify({"message": "ML model trained successfully"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
