"""
Signed Community Detection for the UFO Trust Network

This script implements signed community detection principles based on structural balance theory:
1. Uses positive trust relationships for primary community detection
2. Assigns isolated nodes based on structural balance:
   - Nodes trusted by a community are assigned to that community
   - Nodes distrusted by a community are assigned to the community most commonly 
     distrusted by that community (the "enemy of my enemy" principle)
3. Visualizes the resulting communities with trust/distrust relationships
"""

import json
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import os
import re
from collections import Counter, defaultdict

# File paths
INPUT_FILE = "trust_assignments.json"
COMMUNITY_FILE = "js/data.js"
OUTPUT_FILE = "js/data_signed_communities.js"
VIZ_FILE = "visualization/signed_communities.png"

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
idx_to_user = {i: user for i, user in enumerate(user_list)}
n_users = len(user_list)

print(f"Found {n_users} users in the trust network")

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

# Build weighted graphs:
# - G_pos: Only positive trust relationships (for community detection)
# - G_full: Both positive and negative relationships (for visualization and balance analysis)
G_pos = nx.DiGraph()
G_full = nx.DiGraph()

# Add nodes to both graphs
for i, user in enumerate(user_list):
    G_pos.add_node(i, name=user)
    G_full.add_node(i, name=user)

# Add edges
for i in range(n_users):
    for j in range(n_users):
        # Positive trust edges (> 50)
        if trust_matrix[i, j] > 0:
            G_pos.add_edge(i, j, weight=trust_matrix[i, j])
            G_full.add_edge(i, j, weight=trust_matrix[i, j], type='trust')
        # Negative trust edges (< 50)
        elif trust_matrix[i, j] < 0:
            G_full.add_edge(i, j, weight=abs(trust_matrix[i, j]), type='distrust')

# Convert to undirected for community detection
G_pos_undirected = G_pos.to_undirected()

print(f"Created positive trust network with {G_pos_undirected.number_of_nodes()} nodes and {G_pos_undirected.number_of_edges()} edges")

# Perform initial community detection using Louvain method on positive trust network
try:
    communities = nx.community.louvain_communities(G_pos_undirected, weight='weight')
    print(f"Detected {len(communities)} communities using Louvain method")
    
    # Create node to community mapping
    node_to_comm = {}
    for comm_id, nodes in enumerate(communities):
        for node in nodes:
            node_to_comm[node] = comm_id + 1  # Make community IDs 1-indexed
except Exception as e:
    print(f"Error in community detection: {e}")
    # Fallback to basic assignment
    node_to_comm = {i: 1 for i in range(n_users)}
    print("Using fallback community assignment (all nodes in one community)")

# Find isolated nodes (nodes with no outgoing or incoming positive trust edges)
isolated_nodes = []
for i in range(n_users):
    # Check if node has any positive relationships
    has_pos_relations = False
    for j in range(n_users):
        if trust_matrix[i, j] > 0 or trust_matrix[j, i] > 0:
            has_pos_relations = True
            break
    if not has_pos_relations:
        isolated_nodes.append(i)

print(f"Found {len(isolated_nodes)} isolated nodes (no positive trust connections)")

# Find single-node communities
comm_counts = Counter(node_to_comm.values())
single_node_comms = {comm_id for comm_id, count in comm_counts.items() if count == 1}
for node, comm in node_to_comm.items():
    if comm in single_node_comms and node not in isolated_nodes:
        isolated_nodes.append(node)

print(f"Total nodes requiring reassignment: {len(isolated_nodes)} (isolated + single-node communities)")

# Analyze community distrust patterns
# For each community, find which other communities it most distrusts
community_distrust_patterns = defaultdict(Counter)
for i in range(n_users):
    if i not in node_to_comm:
        continue
    src_comm = node_to_comm[i]
    for j in range(n_users):
        if j not in node_to_comm or trust_matrix[i, j] >= 0:
            continue
        # Count distrust from src_comm to dest_comm
        dest_comm = node_to_comm[j]
        if src_comm != dest_comm:  # Only consider distrust between different communities
            community_distrust_patterns[src_comm][dest_comm] += abs(trust_matrix[i, j])

# Print community distrust patterns
print("\nCommunity Distrust Patterns:")
for comm, distrust_counts in community_distrust_patterns.items():
    if distrust_counts:
        most_distrusted = distrust_counts.most_common(1)[0][0]
        print(f"Community {comm} most distrusts Community {most_distrusted}")

# Function to get "opposite" community based on distrust patterns
def get_opposite_community(comm):
    if comm not in community_distrust_patterns or not community_distrust_patterns[comm]:
        # If no distrust pattern, return a random community that's not this one
        all_comms = set(node_to_comm.values())
        other_comms = all_comms - {comm}
        return min(other_comms) if other_comms else comm
    
    # Return the most distrusted community
    return community_distrust_patterns[comm].most_common(1)[0][0]

# Reassign isolated nodes based on structural balance
for node in isolated_nodes:
    incoming_trust = Counter()
    incoming_distrust = Counter()
    
    # Analyze incoming trust and distrust
    for i in range(n_users):
        if i == node or i not in node_to_comm:
            continue
        
        src_comm = node_to_comm[i]
        
        if trust_matrix[i, node] > 0:
            incoming_trust[src_comm] += trust_matrix[i, node]
        elif trust_matrix[i, node] < 0:
            incoming_distrust[src_comm] += abs(trust_matrix[i, node])
    
    # Decision logic:
    # 1. If there is incoming trust, assign to community with highest trust
    # 2. If only distrust, assign to the opposite of the community with highest distrust
    # 3. If neither, leave as is (or assign randomly)
    
    if incoming_trust:
        # Assign to community with highest trust
        new_comm = incoming_trust.most_common(1)[0][0]
        old_comm = node_to_comm.get(node, None)
        node_to_comm[node] = new_comm
        print(f"Node {idx_to_user[node]} reassigned based on trust: {old_comm} -> {new_comm}")
    
    elif incoming_distrust:
        # Find the community that most distrusts this node
        distrusting_comm = incoming_distrust.most_common(1)[0][0]
        # Assign to the opposite community (most distrusted by distrusting_comm)
        opposite_comm = get_opposite_community(distrusting_comm)
        old_comm = node_to_comm.get(node, None)
        node_to_comm[node] = opposite_comm
        print(f"Node {idx_to_user[node]} reassigned based on 'enemy of my enemy': {old_comm} -> {opposite_comm}")
    
    else:
        # No trust or distrust - leave as is or assign randomly
        if node not in node_to_comm:
            # Assign to random existing community
            all_comms = set(node_to_comm.values())
            node_to_comm[node] = min(all_comms) if all_comms else 1
            print(f"Node {idx_to_user[node]} assigned randomly: -> {node_to_comm[node]}")

# Count final community sizes
final_comm_counts = Counter(node_to_comm.values())
print("\nFinal Community Sizes:")
for comm, count in sorted(final_comm_counts.items()):
    print(f"Community {comm}: {count} users")

# Load existing JS data to get community colors and other metadata
if not os.path.exists(COMMUNITY_FILE):
    print(f"Error: {COMMUNITY_FILE} not found. Run calculate_trust.py first.")
    exit(1)

with open(COMMUNITY_FILE, 'r', encoding='utf-8') as f:
    js_content = f.read()
    # Use regex to extract the JSON object
    match = re.search(r"const trustData\s*=\s*(\{.*?\});", js_content, re.DOTALL)
    if not match:
        print("Could not find trustData JSON object in js/data.js")
        exit(1)
    json_str = match.group(1)
    data = json.loads(json_str)

# Build new community data structure
community_colors = {
    1: "#4285F4",  # Blue
    2: "#EA4335",  # Red
    3: "#FBBC05",  # Yellow
    4: "#34A853",  # Green
    5: "#8334A4",  # Purple
    6: "#00ACC1",  # Cyan
    7: "#FF7043",  # Orange
    8: "#9E9E9E",  # Gray
    9: "#5E35B1",  # Deep Purple
    10: "#43A047"  # Deep Green
}

# Update community data
community_data = []
for comm_id in sorted(set(node_to_comm.values())):
    # Use letter designation (A, B, C...) for communities
    comm_letter = chr(64 + comm_id) if comm_id <= 26 else str(comm_id)
    
    # Get color from existing data or default colors
    if comm_id in community_colors:
        color = community_colors[comm_id]
    else:
        # Generate a random color
        color = f"#{hash(comm_id) % 0xFFFFFF:06x}"  
    
    community_data.append({
        "id": comm_id,
        "name": f"Community {comm_letter}",
        "color": color
    })

# Update user data with new community assignments
users = []
for u in data["users"]:
    username = u["username"]
    if username in user_idx:
        node_id = user_idx[username]
        u["communityId"] = node_to_comm.get(node_id, u["communityId"])
    users.append(u)

# Create final data structure
final_data = data.copy()
final_data["users"] = users
final_data["communities"] = community_data

# Write the new JS file
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("// Signed community detection data\n")
    f.write(f"// Auto-generated using structural balance theory\n\n")
    f.write(f"const trustData = {json.dumps(final_data, indent=2)};\n\n")
    
    # Include original utility functions
    f.write("""
// Map to quickly look up users by username
const userMap = {};
trustData.users.forEach(user => {
    userMap[user.username] = user;
});

// Function to get user details
function getUserDetails(username) {
    return userMap[username];
}

// Function to get incoming trust relationships for a user
function getIncomingTrust(username) {
    return trustData.relationships.filter(rel => rel.target === username);
}

// Function to get outgoing trust relationships for a user
function getOutgoingTrust(username) {
    return trustData.relationships.filter(rel => rel.source === username);
}

// Function to get community color for a user
function getUserCommunityColor(username) {
    const user = getUserDetails(username);
    if (!user) return "#999999";
    
    const community = trustData.communities.find(c => c.id === user.communityId);
    return community ? community.color : "#999999";
}
""")

print(f"Signed community detection results written to {OUTPUT_FILE}")

# Visualization
# Create a visualization with community colors and trust/distrust edges
plt.figure(figsize=(12, 12))

# Create a position layout that puts nodes in the same community closer together
pos = nx.spring_layout(G_full, k=0.15, seed=42)

# Draw nodes with community colors
node_colors = []
for node in G_full.nodes():
    comm = node_to_comm.get(node, 0)
    if comm in community_colors:
        node_colors.append(community_colors[comm])
    else:
        node_colors.append("#999999")  # Default gray

# Create separate lists for trust and distrust edges
trust_edges = [(u, v) for u, v, d in G_full.edges(data=True) if d.get('type') == 'trust']
distrust_edges = [(u, v) for u, v, d in G_full.edges(data=True) if d.get('type') == 'distrust']

# Draw nodes
nx.draw_networkx_nodes(G_full, pos, node_size=80, node_color=node_colors, alpha=0.8)

# Draw edges
nx.draw_networkx_edges(G_full, pos, edgelist=trust_edges, edge_color='green', alpha=0.6, arrows=True)
nx.draw_networkx_edges(G_full, pos, edgelist=distrust_edges, edge_color='red', alpha=0.6, arrows=True, style='dashed')

# Add labels if the network is small enough
if n_users <= 30:
    nx.draw_networkx_labels(G_full, pos, labels={i: idx_to_user[i] for i in range(n_users)}, font_size=8)

# Add a legend
trust_patch = plt.Line2D([0], [0], color='green', linewidth=2, label='Trust')
distrust_patch = plt.Line2D([0], [0], color='red', linewidth=2, label='Distrust', linestyle='dashed')
community_patch = plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', 
                            markersize=10, label='Communities', linewidth=0)
plt.legend(handles=[trust_patch, distrust_patch, community_patch], loc='upper left')

plt.title(f"Trust Network with Signed Community Detection")
plt.axis('off')

# Create visualization directory if it doesn't exist
os.makedirs(os.path.dirname(VIZ_FILE), exist_ok=True)

# Save the visualization
plt.savefig(VIZ_FILE, dpi=300, bbox_inches='tight')
print(f"Visualization saved to {VIZ_FILE}")

plt.close()

print("Signed community detection completed successfully!") 