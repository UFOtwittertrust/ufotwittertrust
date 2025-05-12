"""
Analyze community structure in the current trust network data.
This script examines the trust_assignments.json file and reports on community detection results.
"""

import json
import numpy as np
import networkx as nx
import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt

# Try to import CDlib
try:
    from cdlib import algorithms as cd_algorithms
    from cdlib import viz as cd_viz
    CDLIB_AVAILABLE = True
    print("CDlib is available - will use enhanced community detection")
except ImportError:
    CDLIB_AVAILABLE = False
    print("CDlib is not available - will use NetworkX only")

# Input file
INPUT_FILE = "trust_assignments.json"

def analyze_communities():
    """Analyze the community structure of the trust network."""
    print(f"Starting community analysis at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Run collect_trust.py first.")
        return False
    
    # Load trust assignments
    try:
        with open(INPUT_FILE, 'r') as f:
            trust_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing {INPUT_FILE}: {e}")
        return False
    
    # Get all unique usernames
    all_users = set()
    for source, targets in trust_data["assignments"].items():
        all_users.add(source)
        for target in targets:
            all_users.add(target)
    
    user_list = sorted(list(all_users))
    user_idx = {user: i for i, user in enumerate(user_list)}
    
    print(f"Found {len(user_list)} users in the trust network")
    
    # Create trust matrix
    n_users = len(user_list)
    if n_users == 0:
        print("No users found in trust assignments.")
        return True
    
    trust_matrix = np.zeros((n_users, n_users))
    
    # Also create a separate matrix for visualization that includes both trust and distrust
    full_trust_matrix = np.zeros((n_users, n_users))
    
    # Fill in the trust matrix with only positive trust values
    for source, targets in trust_data["assignments"].items():
        if source not in user_idx:
            continue  # Skip if user not in index
        source_idx = user_idx[source]
        for target, value in targets.items():
            if target in user_idx:
                try:
                    # Process on 0-100 scale where 50 is neutral
                    rating = float(value)
                    rating = max(0, min(100, rating))
                    
                    # Store the normalized value (-1 to 1) in full matrix for visualization
                    norm_full_rating = (rating - 50) / 50  # -1 to 1 scale
                    target_idx = user_idx[target]
                    full_trust_matrix[source_idx, target_idx] = norm_full_rating
                    
                    # Only positive values for community detection
                    if rating > 50:  # Only use positive trust for community detection
                        norm_rating = (rating - 50) / 50  # 0 to 1 scale
                        trust_matrix[source_idx, target_idx] = norm_rating
                except (ValueError, TypeError):
                    pass
    
    # Build graph for community detection
    G_community = nx.DiGraph()
    
    # Add nodes
    for i, user in enumerate(user_list):
        G_community.add_node(i, name=user)
    
    # Add edges with weights for positive trust relationships
    for i in range(n_users):
        for j in range(n_users):
            if trust_matrix[i, j] > 0:
                G_community.add_edge(i, j, weight=trust_matrix[i, j])
    
    # Convert to undirected for community detection
    G_undirected = G_community.to_undirected()
    
    print(f"Created network with {G_undirected.number_of_nodes()} nodes and {G_undirected.number_of_edges()} edges")
    
    # Analyze communities using different algorithms
    print("\n--- Community Detection Results ---")
    
    # 1. Try CDlib algorithms if available
    if CDLIB_AVAILABLE:
        # Try different algorithms
        print("\nCDlib Algorithms:")
        
        # Louvain
        try:
            cd_louvain = cd_algorithms.louvain(G_undirected, weight='weight', resolution=1.0, randomize=True)
            print(f"Louvain: {len(cd_louvain.communities)} communities")
            
            # Show community sizes
            community_sizes = [len(c) for c in cd_louvain.communities]
            print(f"Community sizes: {community_sizes}")
            
            # Generate visualization file path
            viz_file = "visualization/trust_communities_louvain.png"
            os.makedirs(os.path.dirname(viz_file), exist_ok=True)
            
            # Attempt visualization
            try:
                # Create a graph with both trust and distrust for visualization
                G_full = nx.DiGraph()
                
                # Add nodes
                for i, user in enumerate(user_list):
                    G_full.add_node(i, name=user)
                
                # Add edges with attributes for trust/distrust
                trust_edges = []
                distrust_edges = []
                for i in range(n_users):
                    for j in range(n_users):
                        if full_trust_matrix[i, j] > 0:
                            G_full.add_edge(i, j, weight=full_trust_matrix[i, j], trust_type="trust")
                            trust_edges.append((i, j))
                        elif full_trust_matrix[i, j] < 0:
                            G_full.add_edge(i, j, weight=abs(full_trust_matrix[i, j]), trust_type="distrust")
                            distrust_edges.append((i, j))
                
                # Use spring layout with both positive and negative edges for better visualization
                pos = nx.spring_layout(G_full, seed=42)
                
                # Create a figure for the combined visualization
                plt.figure(figsize=(12, 12))
                
                # Draw nodes with community colors
                node_colors = []
                for node in G_full.nodes():
                    # Find which community this node belongs to
                    for i, comm in enumerate(cd_louvain.communities):
                        if node in comm:
                            node_colors.append(plt.cm.tab10(i % 10))
                            break
                    else:
                        node_colors.append('lightgray')  # Fallback if node not in any community
                
                # Draw nodes
                nx.draw_networkx_nodes(G_full, pos, node_size=80, node_color=node_colors, alpha=0.8)
                
                # Draw edges with different colors for trust/distrust
                nx.draw_networkx_edges(G_full, pos, edgelist=trust_edges, edge_color='green', alpha=0.6, arrows=True)
                nx.draw_networkx_edges(G_full, pos, edgelist=distrust_edges, edge_color='red', alpha=0.6, arrows=True)
                
                # Add labels if the network is small enough
                if n_users <= 30:
                    nx.draw_networkx_labels(G_full, pos, labels={i: user_list[i] for i in range(n_users)}, font_size=8)
                
                # Add a legend (a little hacky but effective)
                trust_patch = plt.Line2D([0], [0], color='green', linewidth=2, label='Trust')
                distrust_patch = plt.Line2D([0], [0], color='red', linewidth=2, label='Distrust')
                community_patch = plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', 
                                            markersize=10, label='Communities', linewidth=0)
                plt.legend(handles=[trust_patch, distrust_patch, community_patch], loc='upper left')
                
                plt.title(f"Trust Network with {len(cd_louvain.communities)} Communities")
                plt.axis('off')
                
                # Save the visualization
                viz_file = "visualization/trust_network_with_communities.png"
                plt.savefig(viz_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                print(f"Complete network visualization saved to {viz_file}")
                
                # Also create the standard CDlib visualization
                cd_viz.plot_network_clusters(G_undirected, cd_louvain, 
                                           figsize=(10, 10), node_size=50, plot_labels=False)
                plt.savefig("visualization/trust_communities_louvain.png")
                plt.close()
                print(f"Community-only visualization saved to visualization/trust_communities_louvain.png")
            except Exception as e:
                print(f"Visualization error: {e}")
        except Exception as e:
            print(f"Louvain algorithm error: {e}")
        
        # Note: Skip Leiden since it requires additional dependencies
        print("Note: Leiden algorithm requires additional dependencies: 'leidenalg'")
        print("To install: pip install leidenalg (may require C++ build tools)")
        
        # Label Propagation (faster but less stable)
        try:
            cd_label_prop = cd_algorithms.label_propagation(G_undirected)
            print(f"Label Propagation: {len(cd_label_prop.communities)} communities")
            
            # Show community sizes
            community_sizes = [len(c) for c in cd_label_prop.communities]
            print(f"Community sizes: {community_sizes}")
        except Exception as e:
            print(f"Label Propagation algorithm error: {e}")
    
    # 2. Try NetworkX built-in algorithms
    print("\nNetworkX Algorithms:")
    
    # Louvain
    try:
        nx_communities = nx.community.louvain_communities(G_undirected, weight='weight')
        print(f"Louvain: {len(nx_communities)} communities")
        
        # Show community sizes
        community_sizes = [len(c) for c in nx_communities]
        print(f"Community sizes: {community_sizes}")
    except Exception as e:
        print(f"NetworkX Louvain error: {e}")
    
    # Girvan-Newman (hierarchical detection)
    try:
        # Only attempt on small networks as it's computationally expensive
        if n_users <= 100:  
            gn_communities = list(nx.community.girvan_newman(G_undirected))
            # Take the first few levels of the hierarchy
            levels_to_show = min(3, len(gn_communities))
            for level in range(levels_to_show):
                communities = list(gn_communities[level])
                print(f"Girvan-Newman (level {level+1}): {len(communities)} communities")
        else:
            print("Girvan-Newman: Skipped (network too large)")
    except Exception as e:
        print(f"Girvan-Newman algorithm error: {e}")
    
    print("\n--- Summary ---")
    if CDLIB_AVAILABLE:
        print("CDlib provided enhanced community detection capabilities")
        print("Visualizations saved to the 'visualization' directory")
    else:
        print("Consider installing CDlib for better community detection and visualization:")
        print("pip install cdlib")
    
    return True

def main():
    """Main function."""
    print("=== Starting Trust Network Community Analysis ===")
    
    try:
        if analyze_communities():
            print("Community analysis completed successfully.")
            return True
        else:
            print("Community analysis failed.")
            return False
    except Exception as e:
        print(f"Unhandled error in community analysis: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 