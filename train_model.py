import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# load labeled historical claims from your claims table (you need historical 'label' ground truth)
conn = sqlite3.connect('metadata.db')
df = pd.read_sql_query("SELECT claim_amount, claim_history, fraud_score, label FROM claims", conn)
conn.close()

# simple feature engineering
df['label_bin'] = df['label'].apply(lambda x: 1 if x == 'Suspicious' else 0)
X = df[['claim_amount', 'claim_history', 'fraud_score']].fillna(0)
y = df['label_bin']

if len(df) >= 10:
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X, y)
    joblib.dump(model, 'fraud_model.joblib')
    print('Model trained and saved to fraud_model.joblib')
else:
    print('Not enough data to train a model yet (need >=10 rows).')
