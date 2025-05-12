"""
Synthetic Trust Network Generator

This script generates a synthetic trust network with:
- 3 distinct core communities (believers, skeptics, and neutral/scientific)
- Various outlier types (trusted by multiple communities, distrusted by all, etc.)
- Trust on a 0-100 scale (50 = neutral, >50 = trust, <50 = distrust)

The output can be used to test community detection algorithms and trust analysis.
"""

import json
import random
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import os

# Parameters for synthetic data
N_BELIEVER_CORE = 20     # Core believer community
N_SKEPTIC_CORE = 15      # Core skeptic community
N_NEUTRAL_CORE = 10      # Core neutral/scientific community
N_TRUSTED_BY_ALL = 5     # Trusted by all communities (bridges)
N_TRUSTED_BY_NONE = 5    # Distrusted by all communities (trolls)
N_BELIEVER_SKEPTIC = 3   # Trusted by believers and skeptics, not neutrals
N_SKEPTIC_NEUTRAL = 3    # Trusted by skeptics and neutrals, not believers
N_BELIEVER_NEUTRAL = 3   # Trusted by believers and neutrals, not skeptics
N_RANDOM = 5             # Random trust/distrust patterns (noise)

# Trust intensity parameters (on 0-100 scale)
TRUST_MEAN = 85          # Average trust rating for in-group
TRUST_STD = 10           # Standard deviation for trust ratings
DISTRUST_MEAN = 15       # Average distrust rating for out-group
DISTRUST_STD = 10        # Standard deviation for distrust ratings
NEUTRAL_MEAN = 50        # Average neutral rating
NEUTRAL_STD = 5          # Standard deviation for neutral ratings

# Connection density parameters
IN_GROUP_DENSITY = 0.8   # Density of connections within groups
OUT_GROUP_DENSITY = 0.3  # Density of connections between groups
RANDOM_DENSITY = 0.2     # Density of random connections

# File paths
OUTPUT_FILE = "synthetic_trust_assignments.json"
VISUALIZATION_FILE = "visualization/synthetic_network.png"

def generate_synthetic_network():
    """Generate a synthetic trust network with known community structure."""
    
    # Calculate total number of nodes
    n_nodes = (N_BELIEVER_CORE + N_SKEPTIC_CORE + N_NEUTRAL_CORE + 
               N_TRUSTED_BY_ALL + N_TRUSTED_BY_NONE + 
               N_BELIEVER_SKEPTIC + N_SKEPTIC_NEUTRAL + N_BELIEVER_NEUTRAL + 
               N_RANDOM)
    
    # Create node labels and ground truth communities
    nodes = []
    ground_truth = {}
    
    # Helper to add nodes with appropriate naming
    def add_nodes(prefix, count, community):
        for i in range(count):
            node_id = f"{prefix}{i+1}"
            nodes.append(node_id)
            ground_truth[node_id] = community
    
    # Add core community nodes
    add_nodes("B", N_BELIEVER_CORE, "believer")
    add_nodes("S", N_SKEPTIC_CORE, "skeptic")
    add_nodes("N", N_NEUTRAL_CORE, "neutral")
    
    # Add special case nodes
    add_nodes("TAll", N_TRUSTED_BY_ALL, "trusted_by_all")
    add_nodes("TNone", N_TRUSTED_BY_NONE, "trusted_by_none")
    add_nodes("BS", N_BELIEVER_SKEPTIC, "believer_skeptic")
    add_nodes("SN", N_SKEPTIC_NEUTRAL, "skeptic_neutral")
    add_nodes("BN", N_BELIEVER_NEUTRAL, "believer_neutral")
    add_nodes("R", N_RANDOM, "random")
    
    # Create trust assignments dictionary
    trust_assignments = defaultdict(dict)
    
    # Create communities as sets for easier access
    believers = {n for n in ground_truth if ground_truth[n] == "believer"}
    skeptics = {n for n in ground_truth if ground_truth[n] == "skeptic"}
    neutrals = {n for n in ground_truth if ground_truth[n] == "neutral"}
    trusted_by_all = {n for n in ground_truth if ground_truth[n] == "trusted_by_all"}
    trusted_by_none = {n for n in ground_truth if ground_truth[n] == "trusted_by_none"}
    believer_skeptic = {n for n in ground_truth if ground_truth[n] == "believer_skeptic"}
    skeptic_neutral = {n for n in ground_truth if ground_truth[n] == "skeptic_neutral"}
    believer_neutral = {n for n in ground_truth if ground_truth[n] == "believer_neutral"}
    random_nodes = {n for n in ground_truth if ground_truth[n] == "random"}
    
    # Helper function for trust ratings
    def get_trust_rating(source_community, target_community):
        """Get a trust rating based on source and target communities."""
        # Determine if this is in-group or out-group
        if source_community == target_community:
            # In-group trust
            return min(100, max(0, np.random.normal(TRUST_MEAN, TRUST_STD)))
        else:
            # Default to distrust for out-group
            return min(100, max(0, np.random.normal(DISTRUST_MEAN, DISTRUST_STD)))
    
    # Helper function to determine if an edge should be created based on density
    def should_create_edge(source_community, target_community):
        """Determine if an edge should be created based on community relationship."""
        if source_community == target_community:
            return random.random() < IN_GROUP_DENSITY
        else:
            return random.random() < OUT_GROUP_DENSITY
    
    # Generate trust edges between core communities
    for source in nodes:
        source_type = ground_truth[source]
        
        for target in nodes:
            if source == target:
                continue  # Skip self-edges
                
            target_type = ground_truth[target]
            
            # Handle trust assignments based on node types
            should_rate = False
            rating = 50  # Default neutral
            
            # ==== Core community interactions ====
            if source_type == "believer":
                if target_type == "believer":
                    # Believers trust believers
                    should_rate = should_create_edge("believer", "believer")
                    rating = get_trust_rating("believer", "believer")
                elif target_type == "skeptic":
                    # Believers distrust skeptics
                    should_rate = should_create_edge("believer", "skeptic")
                    rating = get_trust_rating("believer", "skeptic")
                elif target_type == "neutral":
                    # Believers mixed on neutrals
                    should_rate = should_create_edge("believer", "neutral")
                    rating = np.random.normal(45, 15)  # Slightly negative bias
            
            elif source_type == "skeptic":
                if target_type == "skeptic":
                    # Skeptics trust skeptics
                    should_rate = should_create_edge("skeptic", "skeptic")
                    rating = get_trust_rating("skeptic", "skeptic")
                elif target_type == "believer":
                    # Skeptics distrust believers
                    should_rate = should_create_edge("skeptic", "believer")
                    rating = get_trust_rating("skeptic", "believer")
                elif target_type == "neutral":
                    # Skeptics tend to trust neutrals/scientific 
                    should_rate = should_create_edge("skeptic", "neutral")
                    rating = np.random.normal(70, 15)  # Positive bias
            
            elif source_type == "neutral":
                if target_type == "neutral":
                    # Neutrals trust neutrals
                    should_rate = should_create_edge("neutral", "neutral")
                    rating = get_trust_rating("neutral", "neutral")
                else:
                    # Neutrals mixed on others based on evidence
                    should_rate = should_create_edge("neutral", "other")
                    rating = np.random.normal(50, 20)  # Wide distribution
            
            # ==== Special cases ====
            
            # Trusted by all are trusted by all core communities
            if target_type == "trusted_by_all":
                should_rate = random.random() < 0.7  # High rating probability
                if source_type in ["believer", "skeptic", "neutral"]:
                    rating = np.random.normal(80, 10)  # High trust
            
            # Trusted by none are distrusted by all core communities
            if target_type == "trusted_by_none":
                should_rate = random.random() < 0.7  # High rating probability
                if source_type in ["believer", "skeptic", "neutral"]:
                    rating = np.random.normal(20, 10)  # Low trust
            
            # Believers and skeptics trust believer_skeptic nodes
            if target_type == "believer_skeptic":
                if source_type in ["believer", "skeptic"]:
                    should_rate = random.random() < 0.7
                    rating = np.random.normal(75, 15)
                else:
                    should_rate = random.random() < 0.3
                    rating = np.random.normal(40, 15)
            
            # Skeptics and neutrals trust skeptic_neutral nodes
            if target_type == "skeptic_neutral":
                if source_type in ["skeptic", "neutral"]:
                    should_rate = random.random() < 0.7
                    rating = np.random.normal(75, 15)
                else:
                    should_rate = random.random() < 0.3
                    rating = np.random.normal(40, 15)
            
            # Believers and neutrals trust believer_neutral nodes
            if target_type == "believer_neutral":
                if source_type in ["believer", "neutral"]:
                    should_rate = random.random() < 0.7
                    rating = np.random.normal(75, 15)
                else:
                    should_rate = random.random() < 0.3
                    rating = np.random.normal(40, 15)
            
            # Random nodes have random trust patterns
            if source_type == "random" or target_type == "random":
                should_rate = random.random() < RANDOM_DENSITY
                rating = np.random.uniform(0, 100)
            
            # Add the trust rating if we decided to create an edge
            if should_rate:
                trust_assignments[source][target] = round(min(100, max(0, rating)), 1)
    
    # Prepare final output
    output_data = {
        "assignments": dict(trust_assignments),
        "last_updated": "2025-05-12 00:00:00",
        "ground_truth": ground_truth
    }
    
    return output_data, nodes, ground_truth

def visualize_network(trust_data, nodes, ground_truth):
    """Create a visualization of the network with community colors."""
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes
    for node in nodes:
        G.add_node(node, community=ground_truth[node])
    
    # Add edges with weights
    for source, targets in trust_data["assignments"].items():
        for target, weight in targets.items():
            # Convert 0-100 scale to -1 to 1 for visualization
            normalized_weight = (weight - 50) / 50
            G.add_edge(source, target, weight=normalized_weight)
    
    # Create a position layout
    pos = nx.spring_layout(G, seed=42, k=0.3)
    
    # Define community colors
    community_colors = {
        "believer": "#EA4335",       # Red
        "skeptic": "#4285F4",        # Blue
        "neutral": "#FBBC05",        # Yellow
        "trusted_by_all": "#34A853", # Green
        "trusted_by_none": "#9E9E9E",# Gray
        "believer_skeptic": "#8334A4",# Purple
        "skeptic_neutral": "#00ACC1",# Cyan
        "believer_neutral": "#FF7043",# Orange
        "random": "#5E35B1"          # Deep Purple
    }
    
    # Create figure
    plt.figure(figsize=(14, 10))
    
    # Draw nodes with colors based on ground truth communities
    for community, color in community_colors.items():
        nodelist = [n for n in G.nodes if G.nodes[n].get("community") == community]
        nx.draw_networkx_nodes(G, pos, nodelist=nodelist, node_color=color, 
                               node_size=80, label=community, alpha=0.8)
    
    # Draw trust and distrust edges differently
    trust_edges = [(u, v) for u, v, d in G.edges(data=True) if d["weight"] > 0]
    distrust_edges = [(u, v) for u, v, d in G.edges(data=True) if d["weight"] < 0]
    
    nx.draw_networkx_edges(G, pos, edgelist=trust_edges, edge_color="green", 
                          alpha=0.5, arrows=True, arrowsize=10, width=0.8)
    nx.draw_networkx_edges(G, pos, edgelist=distrust_edges, edge_color="red", 
                          alpha=0.5, arrows=True, style="dashed", arrowsize=10, width=0.8)
    
    # Draw labels if there aren't too many nodes
    if len(nodes) <= 100:
        nx.draw_networkx_labels(G, pos, font_size=8)
    
    plt.title("Synthetic Trust Network with Community Structure")
    plt.legend()
    plt.axis("off")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(VISUALIZATION_FILE), exist_ok=True)
    
    # Save the visualization
    plt.savefig(VISUALIZATION_FILE, dpi=300, bbox_inches="tight")
    plt.close()
    
    print(f"Network visualization saved to {VISUALIZATION_FILE}")

def main():
    """Generate a synthetic trust network and save it to a file."""
    print("Generating synthetic trust network...")
    
    trust_data, nodes, ground_truth = generate_synthetic_network()
    
    # Save the trust assignments to a JSON file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(trust_data, f, indent=2)
    
    print(f"Synthetic trust network with {len(nodes)} nodes saved to {OUTPUT_FILE}")
    
    # Visualize the network
    visualize_network(trust_data, nodes, ground_truth)
    
    # Print some statistics
    community_counts = {}
    for node, community in ground_truth.items():
        community_counts[community] = community_counts.get(community, 0) + 1
    
    print("\nGround truth community distribution:")
    for community, count in community_counts.items():
        print(f"  {community}: {count} nodes")
    
    total_edges = sum(len(targets) for targets in trust_data["assignments"].values())
    print(f"\nTotal trust edges: {total_edges}")
    
    # Count trust vs. distrust edges
    trust_edges = 0
    distrust_edges = 0
    for source, targets in trust_data["assignments"].items():
        for target, weight in targets.items():
            if weight > 50:
                trust_edges += 1
            elif weight < 50:
                distrust_edges += 1
    
    print(f"Trust edges (>50): {trust_edges}")
    print(f"Distrust edges (<50): {distrust_edges}")
    print(f"Neutral edges (=50): {total_edges - trust_edges - distrust_edges}")

if __name__ == "__main__":
    main() 