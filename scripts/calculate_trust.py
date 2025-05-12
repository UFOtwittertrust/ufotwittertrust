"""
Calculate trust scores from trust assignments.
This script reads trust_assignments.json and generates data.js with trust scores and network data.
"""

import json
import numpy as np
import networkx as nx
from datetime import datetime
import os
import random
import sys
import logging
from logging.handlers import RotatingFileHandler
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
# Add optional CDlib import for advanced community detection
try:
    from cdlib import algorithms as cd_algorithms
    from cdlib import viz as cd_viz
    CDLIB_AVAILABLE = True
except ImportError:
    CDLIB_AVAILABLE = False

# Input and output files
INPUT_FILE = "trust_assignments.json"
OUTPUT_FILE = "js/data.js"
LOG_FILE = "trust_calculation.log"

# Community colors - keeping colors for visual distinction
COMMUNITY_COLORS = {
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

# Set up logging
logger = logging.getLogger("trust_calculation")
handler = RotatingFileHandler(LOG_FILE, maxBytes=50000, backupCount=3)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def calculate_trust_scores():
    """Calculate trust scores from trust assignments and generate data.js."""
    logger.warning("Starting trust score calculation...")
    
    # Load trust assignments
    if not os.path.exists(INPUT_FILE):
        logger.warning(f"Error: {INPUT_FILE} not found. Run collect_trust.py first.")
        return False
    
    try:
        with open(INPUT_FILE, 'r') as f:
            trust_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"Error parsing {INPUT_FILE}: {e}")
        return False
    
    # Get all unique usernames
    all_users = set()
    for source, targets in trust_data["assignments"].items():
        all_users.add(source)
        for target in targets:
            all_users.add(target)
    
    user_list = sorted(list(all_users))
    user_idx = {user: i for i, user in enumerate(user_list)}
    
    logger.warning(f"Found {len(user_list)} users in the trust network")
    
    # Create trust matrix
    n_users = len(user_list)
    if n_users == 0:
        logger.warning("No users found in trust assignments. Exiting without error.")
        return True
    
    trust_matrix = np.zeros((n_users, n_users))
    
    # Fill in the trust matrix
    for source, targets in trust_data["assignments"].items():
        if source not in user_idx:
            continue  # Skip if user not in index
        source_idx = user_idx[source]
        ratings = []
        valid_targets = []
        for target, value in targets.items():
            if target in user_idx:
                try:
                    # Convert 0-100 scale to -1 to 1 for internal calculations
                    rating = float(value)
                    rating = max(0, min(100, rating))
                    norm_rating = (rating - 50) / 50  # 0=neutral, -1=max distrust, 1=max trust
                    ratings.append(norm_rating)
                    valid_targets.append(target)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid rating value from {source} to {target}: {value}")
        if not ratings:
            continue
        normalization_factor = np.sqrt(sum(r*r for r in ratings))
        if normalization_factor > 0:
            normalized_ratings = [r / normalization_factor * 10 for r in ratings]
        else:
            normalized_ratings = ratings
        for target, rating in zip(valid_targets, normalized_ratings):
            target_idx = user_idx[target]
            trust_matrix[source_idx, target_idx] = rating
    
    # Create separate matrices for positive and negative trust
    positive_matrix = trust_matrix.copy()
    negative_matrix = trust_matrix.copy()
    
    # Keep only positive/negative values in respective matrices
    positive_matrix[positive_matrix < 0] = 0
    negative_matrix[negative_matrix > 0] = 0
    negative_matrix = -negative_matrix  # Make negative values positive for calculation
    
    # Calculate trust scores using PageRank-like approach
    logger.warning("Building trust network graph...")
    G = nx.DiGraph()
    
    # Add nodes and edges to the graph
    for i, user in enumerate(user_list):
        G.add_node(i)
    
    # Add positive trust edges with weights
    for i in range(n_users):
        for j in range(n_users):
            if positive_matrix[i, j] > 0:
                G.add_edge(i, j, weight=positive_matrix[i, j])
    
    logger.warning("Calculating PageRank scores...")
    
    # Calculate PageRank with personalization for positive trust
    alpha = 0.85  # Damping factor
    personalization = None  # Could customize this for different variations
    
    try:
        pageranks = nx.pagerank(G, alpha=alpha, personalization=personalization)
    except Exception as e:
        # Fallback to basic calculation if PageRank fails
        logger.warning(f"Warning: PageRank calculation failed ({e}), using basic scoring")
        pageranks = {i: 1.0/n_users for i in range(n_users)}
        
        # Adjust based on direct trust received
        for i in range(n_users):
            received_trust = 0
            for j in range(n_users):
                if positive_matrix[j, i] > 0:
                    received_trust += positive_matrix[j, i]
            pageranks[i] += received_trust / (100 * n_users)  # Scale factor adjusted for -100 to 100 range
        
        # Normalize
        total = sum(pageranks.values())
        if total > 0:
            for i in pageranks:
                pageranks[i] /= total
    
    # Extract trust scores
    trust_scores = np.zeros(n_users)
    for i, score in pageranks.items():
        trust_scores[i] = score
    
    # Apply distrust penalty
    logger.warning("Applying distrust penalties...")
    
    # Calculate total negative trust received by each user
    for i in range(n_users):
        total_distrust = 0
        for j in range(n_users):
            if negative_matrix[j, i] > 0:  # Remember, we made negatives positive
                # Weight the distrust by the trustor's score
                weighted_distrust = negative_matrix[j, i] * trust_scores[j]
                total_distrust += weighted_distrust
        
        # Apply a penalty proportional to distrust but with diminishing returns
        if total_distrust > 0:
            penalty_factor = np.tanh(total_distrust / 20)  # Tanh limits to range (-1, 1), adjusted for the rating scale
            penalty_factor *= 0.5  # Scale down the effect of distrust
            trust_scores[i] *= (1 - penalty_factor)
    
    # Re-normalize after applying penalties
    total = np.sum(trust_scores)
    if total > 0:
        trust_scores = trust_scores / total
    
    logger.warning("Detecting communities...")
    
    # Detect communities - handle small graphs specially
    if n_users < 3:
        # For very small graphs, just assign everyone to community 1
        community_map = {i: 1 for i in range(n_users)}
    else:
        # Make a graph for community detection - now considering the signed nature
        G_community = nx.DiGraph()
        for i in range(n_users):
            G_community.add_node(i)
        
        # Add all edges (both trust and distrust) to signed graph
        for i in range(n_users):
            for j in range(n_users):
                if trust_matrix[i, j] != 0:
                    G_community.add_edge(i, j, weight=trust_matrix[i, j])
        
        # For community detection, create a positive-only subgraph
        G_positive = nx.DiGraph([(u, v, d) for u, v, d in G_community.edges(data=True) if d["weight"] > 0])
        
        # Convert to undirected for community detection
        G_undirected = G_positive.to_undirected()
        
        # Use CDlib Louvain (or fallback) for community detection on positive trust
        try:
            if CDLIB_AVAILABLE:
                # CDlib returns a Clustering object; extract communities list
                cd_result = cd_algorithms.louvain(G_undirected, weight='weight', resolution=1.0, randomize=True)
                communities = cd_result.communities
            else:
                # Fallback to NetworkX built-in Louvain if CDlib unavailable
                communities = nx.community.louvain_communities(G_undirected, weight='weight', resolution=1.0, seed=42)
            
            community_map = {}
            for i, comm in enumerate(communities):
                for node in comm:
                    community_map[node] = i + 1  # Communities are 1-indexed for display
                    
            # Now handle nodes not assigned to any community (isolated nodes)
            # These could be users who only have distrust relationships
            isolated_nodes = set(range(n_users)) - set(community_map.keys())
            
            if isolated_nodes:
                logger.warning(f"Found {len(isolated_nodes)} isolated nodes to assign to communities")
                
                # For each isolated node, use a heuristic to assign to a community
                for node in isolated_nodes:
                    # Check which community trusts or distrusts this node the most
                    community_trust_scores = defaultdict(float)
                    community_distrust_scores = defaultdict(float)
                    
                    # Look at who trusts this isolated node
                    for i in range(n_users):
                        if i in community_map and trust_matrix[i, node] > 0:
                            community_trust_scores[community_map[i]] += trust_matrix[i, node]
                        elif i in community_map and trust_matrix[i, node] < 0:
                            community_distrust_scores[community_map[i]] -= trust_matrix[i, node]
                    
                    # Look at who this isolated node trusts
                    for i in range(n_users):
                        if i in community_map and trust_matrix[node, i] > 0:
                            community_trust_scores[community_map[i]] += trust_matrix[node, i]
                        elif i in community_map and trust_matrix[node, i] < 0:
                            community_distrust_scores[community_map[i]] -= trust_matrix[node, i]
                    
                    assigned = False
                    
                    # First try to assign based on trust
                    if community_trust_scores:
                        # Assign to the community with the strongest trust relationship
                        best_community = max(community_trust_scores.items(), key=lambda x: x[1])[0]
                        community_map[node] = best_community
                        assigned = True
                        logger.warning(f"Assigned isolated node {user_list[node]} to community {best_community} based on trust")
                    
                    # If no trust relationships, try distrust
                    elif community_distrust_scores:
                        # Find which community distrusts this node the most
                        most_distrusting = max(community_distrust_scores.items(), key=lambda x: x[1])[0]
                        
                        # Find which community is most distrusted by the community that distrusts this node
                        # (the "enemy of my enemy" principle)
                        enemy_of_enemy = defaultdict(float)
                        for i in range(n_users):
                            if community_map.get(i) == most_distrusting:
                                for j in range(n_users):
                                    if j in community_map and trust_matrix[i, j] < 0:
                                        enemy_of_enemy[community_map[j]] -= trust_matrix[i, j]
                        
                        if enemy_of_enemy:
                            best_community = max(enemy_of_enemy.items(), key=lambda x: x[1])[0]
                            community_map[node] = best_community
                            assigned = True
                            logger.warning(f"Assigned isolated node {user_list[node]} to community {best_community} based on structural balance theory")
                    
                    # If still not assigned, just put in largest community
                    if not assigned:
                        community_sizes = Counter(community_map.values())
                        largest_community = max(community_sizes.items(), key=lambda x: x[1])[0]
                        community_map[node] = largest_community
                        logger.warning(f"Assigned isolated node {user_list[node]} to largest community ({largest_community})")
        except Exception as e:
            # Fallback for very small or disconnected graphs
            logger.warning(f"Warning: Community detection failed ({e}), using random assignment")
            community_map = {i: random.randint(1, min(5, n_users)) for i in range(n_users)}
    
    # Analyze community composition
    community_analysis = analyze_communities(communities, user_list, community_map)
    
    # Generate visualization of trust network with communities
    visualize_trust_network(trust_matrix, user_list, community_map)
    
    # Count trustors and trustees for each user
    trustors_count = [0] * n_users
    trustees_count = [0] * n_users
    
    for i in range(n_users):
        for j in range(n_users):
            if trust_matrix[i, j] != 0:
                trustees_count[i] += 1
                trustors_count[j] += 1
    
    logger.warning("Creating JSON data structure...")
    
    # Create relationships data
    relationships = []
    for i in range(n_users):
        for j in range(n_users):
            if trust_matrix[i, j] != 0:
                relationships.append({
                    "source": user_list[i],
                    "target": user_list[j],
                    "value": float(trust_matrix[i, j])
                })
    
    # Create community data with generic names (Community A, B, C, etc.)
    community_data = []
    used_communities = set(community_map.values())
    
    for comm_id in sorted(used_communities):
        # Use letter designation (A, B, C...) for communities
        comm_letter = chr(64 + comm_id) if comm_id <= 26 else str(comm_id)
        
        # Pick a color - use predefined colors or generate random ones
        if comm_id in COMMUNITY_COLORS:
            color = COMMUNITY_COLORS[comm_id]
        else:
            color = f"#{random.randint(0, 0xFFFFFF):06x}"  # Random color
        
        community_data.append({
            "id": comm_id,
            "name": f"Community {comm_letter}",
            "color": color
        })
    
    # Create users data with empty interests
    users = []
    for i, user in enumerate(user_list):
        # Don't assign any interests
        interests = []
        
        users.append({
            "username": user,
            "trustScore": float(trust_scores[i]),
            "trustors": trustors_count[i],
            "trustees": trustees_count[i],
            "interests": interests,
            "communityId": community_map.get(i, 1)
        })
    
    # --- Community-perspective trust scores ---
    community_trust_scores = {}
    for comm_id in sorted(used_communities):
        # Get indices of users in this community
        comm_indices = [i for i, cid in community_map.items() if cid == comm_id]
        if len(comm_indices) == 0:
            continue
        # Build submatrix for this community
        comm_matrix = positive_matrix[np.ix_(comm_indices, comm_indices)]
        n_comm = len(comm_indices)
        # Build subgraph
        G_comm = nx.DiGraph()
        for i in range(n_comm):
            G_comm.add_node(i)
        for i in range(n_comm):
            for j in range(n_comm):
                if comm_matrix[i, j] > 0:
                    G_comm.add_edge(i, j, weight=comm_matrix[i, j])
        # Calculate PageRank for this community
        if n_comm == 1:
            comm_scores = {comm_indices[0]: 1.0}
        else:
            try:
                comm_pagerank = nx.pagerank(G_comm, alpha=alpha)
                comm_scores = {comm_indices[i]: comm_pagerank[i] for i in range(n_comm)}
            except Exception as e:
                logger.warning(f"Community {comm_id} PageRank failed: {e}")
                comm_scores = {comm_indices[i]: 1.0/n_comm for i in range(n_comm)}
        # Normalize
        total = sum(comm_scores.values())
        if total > 0:
            for k in comm_scores:
                comm_scores[k] /= total
        # Map back to usernames
        comm_scores_named = {user_list[k]: comm_scores[k] for k in comm_scores}
        community_trust_scores[comm_id] = comm_scores_named
    
    # Create final data structure
    final_data = {
        "lastUpdated": trust_data.get("last_updated", datetime.now().strftime("%B %d, %Y %I:%M %p")),
        "users": users,
        "relationships": relationships,
        "communities": community_data,
        "communityTrustScores": community_trust_scores
    }
    
    # Create js directory if it doesn't exist
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Generate JavaScript file
    js_content = f"""// Trust system data
// Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
// DO NOT EDIT MANUALLY

const trustData = {json.dumps(final_data, indent=2)};

// Map to quickly look up users by username
const userMap = {{}};
trustData.users.forEach(user => {{
    userMap[user.username] = user;
}});

// Function to get user details
function getUserDetails(username) {{
    return userMap[username];
}}

// Function to get incoming trust relationships for a user
function getIncomingTrust(username) {{
    return trustData.relationships.filter(rel => rel.target === username);
}}

// Function to get outgoing trust relationships for a user
function getOutgoingTrust(username) {{
    return trustData.relationships.filter(rel => rel.source === username);
}}

// Function to get community color for a user
function getUserCommunityColor(username) {{
    const user = getUserDetails(username);
    if (!user) return "#999999";
    
    const community = trustData.communities.find(c => c.id === user.communityId);
    return community ? community.color : "#999999";
}}
"""
    
    # Write to file
    try:
        with open(OUTPUT_FILE, 'w') as f:
            f.write(js_content)
        
        logger.warning(f"Successfully generated {OUTPUT_FILE} with:")
        logger.warning(f"- {len(users)} users")
        logger.warning(f"- {len(relationships)} trust relationships")
        logger.warning(f"- {len(community_data)} communities")
        return True
    except Exception as e:
        logger.warning(f"Error writing to {OUTPUT_FILE}: {e}")
        return False

def analyze_communities(communities, user_list, community_map):
    """Analyze the composition of detected communities."""
    logger.info("Analyzing community composition...")
    community_sizes = Counter(community_map.values())
    
    # Sort communities by size (largest first)
    sorted_communities = sorted(community_sizes.items(), key=lambda x: x[1], reverse=True)
    
    analysis = []
    for comm_id, size in sorted_communities:
        # Get usernames in this community
        members = [user_list[i] for i, cid in community_map.items() if cid == comm_id]
        comm_letter = chr(64 + comm_id) if comm_id <= 26 else str(comm_id)
        
        analysis.append({
            "id": comm_id,
            "name": f"Community {comm_letter}",
            "size": size,
            "members": sorted(members)
        })
    
    # Log community analysis
    for comm in analysis:
        logger.info(f"Community {comm['name']} ({comm['size']} members): {', '.join(comm['members'])}")
    
    # Write community analysis to file for easier viewing
    with open("community_analysis.txt", "w") as f:
        f.write(f"Community Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Users: {len(user_list)}\n")
        f.write(f"Number of Communities: {len(sorted_communities)}\n\n")
        for comm in analysis:
            f.write(f"Community {comm['name']} ({comm['size']} members):\n")
            f.write(f"  {', '.join(comm['members'])}\n\n")
    
    logger.info(f"Community analysis written to community_analysis.txt")
    return analysis

def visualize_trust_network(trust_matrix, user_list, community_map, output_file="visualization/trust_network.png"):
    """Create a visualization of the trust network with communities."""
    logger.warning("Generating trust network visualization...")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create a directed graph
    G = nx.DiGraph()
    
    n_users = len(user_list)
    
    # Add nodes with community info
    for i in range(n_users):
        G.add_node(i, username=user_list[i], community=community_map.get(i, 0))
    
    # Add edges with weights
    for i in range(n_users):
        for j in range(n_users):
            if trust_matrix[i, j] != 0:
                G.add_edge(i, j, weight=trust_matrix[i, j])
    
    # Create position layout
    pos = nx.spring_layout(G, seed=42, k=0.3)
    
    # Define community colors
    communities = set(community_map.values())
    
    plt.figure(figsize=(14, 10))
    
    # Draw trust and distrust edges differently
    trust_edges = [(u, v) for u, v, d in G.edges(data=True) if d["weight"] > 0]
    distrust_edges = [(u, v) for u, v, d in G.edges(data=True) if d["weight"] < 0]
    
    nx.draw_networkx_edges(G, pos, edgelist=trust_edges, edge_color="green", 
                          alpha=0.4, arrows=True, arrowstyle="-|>", width=0.8)
    nx.draw_networkx_edges(G, pos, edgelist=distrust_edges, edge_color="red", 
                          alpha=0.4, arrows=True, style="dashed", arrowstyle="-|>", width=0.8)
    
    # Draw nodes colored by community
    for comm_id in communities:
        color = COMMUNITY_COLORS.get(comm_id, f"#{random.randint(0, 0xFFFFFF):06x}")
        comm_letter = chr(64 + comm_id) if comm_id <= 26 else str(comm_id)
        
        nodelist = [i for i in G.nodes() if G.nodes[i].get("community") == comm_id]
        if nodelist:
            nx.draw_networkx_nodes(G, pos, nodelist=nodelist, node_color=color, 
                                node_size=80, label=f"Community {comm_letter}", alpha=0.8)
    
    # Draw labels if there aren't too many nodes
    if n_users <= 60:
        labels = {i: G.nodes[i]["username"] for i in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
    
    plt.title("UFO Trust Network with Communities")
    plt.legend()
    plt.axis("off")
    
    # Save the visualization
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()
    
    logger.warning(f"Network visualization saved to {output_file}")
    return True

def main():
    """Main function."""
    logger.warning("=== Starting Trust Score Calculation ===")
    
    try:
        if calculate_trust_scores():
            logger.warning("Trust calculation completed successfully.")
            return True
        else:
            logger.warning("Trust calculation failed.")
            return False
    except Exception as e:
        logger.warning(f"Unhandled error in trust calculation: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)