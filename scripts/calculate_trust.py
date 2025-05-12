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
logger.setLevel(logging.WARNING)

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
        logger.warning("No users found in trust assignments")
        return False
    
    trust_matrix = np.zeros((n_users, n_users))
    
    # Fill in the trust matrix
    for source, targets in trust_data["assignments"].items():
        if source not in user_idx:
            continue  # Skip if user not in index
        
        source_idx = user_idx[source]
        
        # With the new rating system, we normalize across all ratings for a user
        # to ensure fair influence, but don't enforce a specific budget
        ratings = []
        valid_targets = []
        
        # First pass: collect valid ratings and targets
        for target, value in targets.items():
            if target in user_idx:
                try:
                    # Ensure the rating is between -100 and 100
                    rating = float(value)
                    rating = max(-100, min(100, rating))
                    ratings.append(rating)
                    valid_targets.append(target)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid rating value from {source} to {target}: {value}")
        
        # If user has no valid ratings, skip
        if not ratings:
            continue
            
        # Normalize ratings for this user (optional, but helps prevent one user from dominating)
        # Using L2 normalization (sum of squares = 1)
        normalization_factor = np.sqrt(sum(r*r for r in ratings))
        if normalization_factor > 0:
            normalized_ratings = [r / normalization_factor * 10 for r in ratings]  # Scale by 10 for reasonable values
        else:
            normalized_ratings = ratings  # Shouldn't happen, but just in case
            
        # Assign normalized ratings to the matrix
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
        # Make a simplified graph for community detection (ignore negative edges)
        G_community = nx.DiGraph()
        for i in range(n_users):
            G_community.add_node(i)
        
        for i in range(n_users):
            for j in range(n_users):
                if positive_matrix[i, j] > 0:
                    G_community.add_edge(i, j, weight=positive_matrix[i, j])
        
        # Convert to undirected for community detection
        G_undirected = G_community.to_undirected()
        
        # Use Louvain method for community detection
        try:
            communities = nx.community.louvain_communities(G_undirected)
            community_map = {}
            for i, comm in enumerate(communities):
                for node in comm:
                    community_map[node] = i + 1
        except Exception as e:
            # Fallback for very small or disconnected graphs
            logger.warning(f"Warning: Community detection failed ({e}), using random assignment")
            community_map = {i: random.randint(1, min(5, n_users)) for i in range(n_users)}
    
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
    
    # Create final data structure
    final_data = {
        "lastUpdated": trust_data.get("last_updated", datetime.now().strftime("%B %d, %Y %I:%M %p")),
        "users": users,
        "relationships": relationships,
        "communities": community_data
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