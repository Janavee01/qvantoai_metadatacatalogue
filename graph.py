import sqlite3
import networkx as nx
import matplotlib.pyplot as plt

# Connect to metadata database
conn = sqlite3.connect("metadata.db")
cursor = conn.cursor()

# Fetch all assets
cursor.execute("SELECT id, name, type, tags FROM metadata")
assets = cursor.fetchall()
conn.close()

print("Assets in DB:", assets)

# Create directed graph
G = nx.DiGraph()

# Track seen nodes to avoid duplicates
seen = set()

# Add nodes dynamically, remove duplicates based on (name, type)
for asset in assets:
    asset_id, name, typ, tags = asset
    node_key = f"{name}_{typ}"  # unique key ignoring ID to remove duplicates
    if node_key not in seen:
        label = f"{name}\n({typ})"
        G.add_node(node_key, label=label)
        seen.add(node_key)

print("Nodes added (duplicates removed):", G.nodes())

# Define edges (Policy -> Claim -> ReserveModel) dynamically
policy_nodes = [n for n in G.nodes if "Policy" in n]
claim_nodes = [n for n in G.nodes if "Claim" in n]
reserve_nodes = [n for n in G.nodes if "ReserveModel" in n]

# Define edges for all nodes
edges = []

# Connect every policy to every claim
for policy in policy_nodes:
    for claim in claim_nodes:
        edges.append((policy, claim))

# Connect every claim to every reserve model
for claim in claim_nodes:
    for reserve in reserve_nodes:
        edges.append((claim, reserve))

G.add_edges_from(edges)

# ✅ Now remove isolated nodes (after edges are added)
isolated = list(nx.isolates(G))
G.remove_nodes_from(isolated)

# ✅ Color nodes based on type
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
plt.figure(figsize=(8, 6))
pos = nx.spring_layout(G, seed=42)
nx.draw(
    G, pos, with_labels=True,
    labels=nx.get_node_attributes(G, 'label'),
    node_size=2500, node_color=node_colors,
    font_size=10, font_weight="bold", arrowsize=20
)
nx.draw_networkx_edges(G, pos, arrowstyle='-|>', arrowsize=20)
plt.title("Data Lineage: Policy → Claim → ReserveModel")
plt.axis('off')
plt.tight_layout()
plt.show()
