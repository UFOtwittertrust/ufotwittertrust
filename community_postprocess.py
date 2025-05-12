"""
Post-process community assignments to reduce isolated (single-node) communities.
Assign isolated nodes to the community from which they receive the most trust (or, if none, the least distrust).
"""

import json
import numpy as np
import networkx as nx
import os
from collections import Counter
import re

INPUT_FILE = "trust_assignments.json"
COMMUNITY_FILE = "js/data.js"  # Where community assignments are stored (from calculate_trust.py)
OUTPUT_FILE = "js/data_postprocessed.js"

# Load trust assignments
if not os.path.exists(INPUT_FILE):
    print(f"Error: {INPUT_FILE} not found.")
    exit(1)

with open(INPUT_FILE, 'r') as f:
    trust_data = json.load(f)

# Get all unique usernames
all_users = set()
for source, targets in trust_data["assignments"].items():
    all_users.add(source)
    for target in targets:
        all_users.add(target)
user_list = sorted(list(all_users))
user_idx = {user: i for i, user in enumerate(user_list)}
n_users = len(user_list)

# Build full trust matrix (-1 to 1 scale)
trust_matrix = np.zeros((n_users, n_users))
for source, targets in trust_data["assignments"].items():
    if source not in user_idx:
        continue
    source_idx = user_idx[source]
    for target, value in targets.items():
        if target in user_idx:
            try:
                rating = float(value)
                rating = max(0, min(100, rating))
                trust_matrix[source_idx, user_idx[target]] = (rating - 50) / 50
            except (ValueError, TypeError):
                pass

# Load community assignments from js/data.js
if not os.path.exists(COMMUNITY_FILE):
    print(f"Error: {COMMUNITY_FILE} not found. Run calculate_trust.py first.")
    exit(1)

with open(COMMUNITY_FILE, 'r', encoding='utf-8') as f:
    js_content = f.read()
    # Use regex to extract the JSON object assigned to const trustData = ...;
    match = re.search(r"const trustData\s*=\s*(\{.*?\});", js_content, re.DOTALL)
    if not match:
        print("Could not find trustData JSON object in js/data.js")
        exit(1)
    json_str = match.group(1)
    data = json.loads(json_str)

users = data["users"]
communities = data["communities"]
relationships = data["relationships"]

# Build a mapping from username to communityId
user_to_comm = {u["username"]: u["communityId"] for u in users}

# Find isolated (single-node) communities
comm_counts = Counter(user_to_comm.values())
isolated_communities = {comm_id for comm_id, count in comm_counts.items() if count == 1}
isolated_users = [u for u in users if u["communityId"] in isolated_communities]

print(f"Found {len(isolated_users)} isolated users. Reassigning...")

# For each isolated user, assign to the community from which they receive the most trust
for user in isolated_users:
    idx = user_idx[user["username"]]
    # Find incoming trust from each community
    incoming = trust_matrix[:, idx]
    comm_trust = Counter()
    for j, val in enumerate(incoming):
        if val > 0:
            src_user = user_list[j]
            src_comm = user_to_comm.get(src_user)
            if src_comm is not None:
                comm_trust[src_comm] += val
    if comm_trust:
        # Assign to the community with the most incoming trust
        new_comm = comm_trust.most_common(1)[0][0]
        user["communityId"] = new_comm
    else:
        # If no incoming trust, try least incoming distrust
        comm_distrust = Counter()
        for j, val in enumerate(incoming):
            if val < 0:
                src_user = user_list[j]
                src_comm = user_to_comm.get(src_user)
                if src_comm is not None:
                    comm_distrust[src_comm] += abs(val)
        if comm_distrust:
            new_comm = comm_distrust.most_common(1)[0][0]
            user["communityId"] = new_comm
        # Otherwise, leave as is

# Update the user_to_comm mapping
user_to_comm = {u["username"]: u["communityId"] for u in users}

# Rebuild the output data structure
final_data = data
final_data["users"] = users

# Write the new JS file
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("// Post-processed trust system data\n")
    f.write(f"// Auto-generated\n\nconst trustData = {json.dumps(final_data, indent=2)};\n")

print(f"Post-processed community assignments written to {OUTPUT_FILE}") 