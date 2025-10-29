
qvantoai_metadatacatalogue - Metadata Catalog, Lineage, and Claims Fraud Workflow

------------------------------------------
ARCHITECTURE OVERVIEW:

1. Flask REST API backend serving endpoints for:
    - Metadata catalog CRUD operations (/add_asset, /assets, /update_asset, /delete_asset)
    - Search/filter metadata (/search)
    - Fraud scoring (rule-based: /fraud_score, ML-based: /fraud_score_ml)
    - Dashboard summary (/dashboard)
    - Data lineage visualization (/lineage, /lineage_html)
    - Model training (/train_model)

2. SQLite database (metadata.db) storing:
    - metadata table (insurance data assets: policy, claim, reserve model)
    - claims table (claim_amount, claim_history, fraud_score, label)

3. ML Model:
    - RandomForestClassifier for claims fraud detection
    - Saved as 'fraud_model.joblib'
    - Requires >=10 rows in claims table to train; otherwise, rule-based scoring used

4. Lineage Visualization:
    - NetworkX + Matplotlib generates policy → claim → reserve model graphs
    - /lineage_html endpoint serves placeholder for interactive D3.js visualization

------------------------------------------
ASSUMPTIONS:

- Role-based access controlled via `ROLE` variable: "admin" (full access) / "viewer" (read-only)
- Minimum 10 historical claims required for ML training
- Claim labels are either "Suspicious" or "OK"
- SQLite used for simplicity (not for concurrent production)
- Basic HTML dashboard suffices for summary metrics
- Input validation is minimal; production should include stricter checks

------------------------------------------
HOW TO RUN / TEST:

1. Setup environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   pip install flask pandas scikit-learn joblib networkx matplotlib
   python app.py
   ```

App runs on http://127.0.0.1:5000/

Test endpoints:

Add asset:

Invoke-RestMethod -Uri "http://127.0.0.1:5000/add_asset" -Method POST -ContentType "application/json" -Body '{"name": "PolicyData", "type": "Policy", "tags": "PII", "description": "Policy info"}'


Get assets: GET /assets

Update/delete asset: PUT /update_asset/<id>, DELETE /delete_asset/<id>

Search by tag: GET /search?tag=PII

Score claim (rule-based): POST /fraud_score

Score claim (ML): POST /fraud_score_ml

Train ML model: POST /train_model

Dashboard: GET /dashboard

Lineage graph: GET /lineage (image), GET /lineage_html (interactive template)

Notes:

Ensure claims table has >=10 rows to train ML model.

Use ROLE="viewer" to simulate read-only access.

Lineage graph colors: Policy=green, Claim=blue, ReserveModel=red.

Claims Fraud Summary Dashboard (HTML)
Shows total claims, suspicious claims, fraud rate, and total metadata assets.

http://127.0.0.1:5000/dashboard


Lineage Graph 
Displays the policy → claim → reserve model lineage as a static image.

http://127.0.0.1:5000/lineage


Lineage HTML/D3 Interactive Page
Placeholder page to render lineage graph interactively (requires lineage.html in templates/).

http://127.0.0.1:5000/lineage_html
