import json
import numpy as np
import networkx as nx
import os

INPUT_FILE = "trust_assignments.json"

def find_resolution_for_few_communities():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    try:
        with open(INPUT_FILE, 'r') as f:
            trust_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing {INPUT_FILE}: {e}")
        return

    all_users = set()
    if "assignments" not in trust_data or not trust_data["assignments"]:
        print("No assignments found in the data.")
        return

    for source, targets in trust_data["assignments"].items():
        all_users.add(source)
        for target in targets:
            all_users.add(target)
    
    user_list = sorted(list(all_users))
    user_idx = {user: i for i, user in enumerate(user_list)}
    n_users = len(user_list)

    if n_users == 0:
        print("No users to process.")
        return
    if n_users < 3 and n_users > 0 : # If you want exactly 3, but have less.
        print(f"Network has only {n_users} users, cannot form 3 communities unless n_users is 3.")
        # For n_users=1 or 2, Louvain gives 1 or 2 communities respectively with res=1.0
        # If n_users=3, res=1.0 often gives 3 communities if no edges, or fewer if edges exist.
        # The goal of "3 communities" is only really meaningful if n_users >= 3.
        if n_users > 0: # Check default for small N
            G_community_small_check = nx.DiGraph()
            for i in range(n_users): G_community_small_check.add_node(i)
            # ... (build graph as before) ...
            # For simplicity, if n_users <3, we just state the fact.
            # The complex graph building part is mostly for n_users >=3
        return


    trust_matrix = np.zeros((n_users, n_users))
    # ... (rest of matrix population code from previous script is the same) ...
    for source, targets in trust_data["assignments"].items():
        if source not in user_idx:
            continue
        source_idx = user_idx[source]
        ratings = []
        valid_targets = []
        for target, value in targets.items():
            if target in user_idx:
                try:
                    rating = float(value)
                    rating = max(0, min(100, rating)) 
                    norm_rating = (rating - 50) / 50  
                    ratings.append(norm_rating)
                    valid_targets.append(target)
                except (ValueError, TypeError):
                    pass # Already warned if needed
        
        if not ratings:
            continue
        l2_norm_val = np.sqrt(sum(r*r for r in ratings))
        if l2_norm_val > 0:
            final_ratings = [(r / l2_norm_val) * 10 for r in ratings]
        else:
            final_ratings = ratings
        for target_user, final_rating_val in zip(valid_targets, final_ratings):
            target_idx = user_idx[target_user]
            trust_matrix[source_idx, target_idx] = final_rating_val

    positive_matrix = trust_matrix.copy()
    positive_matrix[positive_matrix < 0] = 0 

    G_community = nx.DiGraph()
    for i in range(n_users):
        G_community.add_node(i)
    for i in range(n_users):
        for j in range(n_users):
            if positive_matrix[i, j] > 0:
                G_community.add_edge(i, j, weight=positive_matrix[i, j])
    
    if G_community.number_of_nodes() > 0 and G_community.number_of_edges() == 0:
        num_default_comms = G_community.number_of_nodes()
        print(f"Graph has {num_default_comms} nodes but 0 positive edges. Louvain (res=1.0) will result in {num_default_comms} communities.")
        if num_default_comms == 3:
            print("Resolution 1.0 will result in 3 communities by default for this graph structure.")
        return

    G_undirected = G_community.to_undirected()
    if G_undirected.number_of_nodes() == 0:
        print("No nodes in graph for community detection.")
        return

    num_connected_components = nx.number_connected_components(G_undirected)
    print(f"Graph for community detection: {G_undirected.number_of_nodes()} nodes, {G_undirected.number_of_edges()} edges. It has {num_connected_components} connected components.")
    if num_connected_components > 3:
         print(f"Warning: The graph has {num_connected_components} connected components. It's impossible to get fewer communities than this number ({num_connected_components}) using Louvain resolution.")
         return
    if num_connected_components == 3:
        print(f"The graph already has 3 connected components. Resolution parameter will likely not merge these further. Resolution 1.0 might already yield 3 communities or a value slightly less than 1 for robustness.")
        # Check resolution 1.0
        try:
            communities_at_1_strict = list(nx.community.louvain_communities(G_undirected, resolution=1.0, seed=42))
            if len(communities_at_1_strict) == 3:
                print("Resolution 1.00 already results in 3 communities.")
                return
        except Exception:
            pass # Continue to search lower

    # Iterate downwards from 1.0
    current_resolution = 1.0
    step = 0.05
    min_resolution = 0.05 # Lower bound for the search (resolution cannot be 0 or negative)
    seed_for_louvain = 42 
    
    last_num_communities = -1
    
    # Check resolution 1.0 first
    try:
        communities_at_1 = list(nx.community.louvain_communities(G_undirected, resolution=1.0, seed=seed_for_louvain))
        num_communities_at_1 = len(communities_at_1)
        print(f"Trying resolution 1.00: Found {num_communities_at_1} communities")
        if num_communities_at_1 == 3:
            print("Found 3 communities at resolution 1.00")
            return
        last_num_communities = num_communities_at_1
    except Exception as e:
        print(f"Error during Louvain with resolution 1.0: {e}")
        return

    current_resolution = 1.0 - step
    while current_resolution >= min_resolution:
        try:
            communities_iterable = nx.community.louvain_communities(G_undirected, resolution=current_resolution, seed=seed_for_louvain)
            num_communities = len(list(communities_iterable)) # consume iterator
            print(f"Trying resolution {current_resolution:.2f}: Found {num_communities} communities")

            if num_communities == 3:
                print(f"Success! Resolution found for 3 communities is approximately: {current_resolution:.2f}")
                return
            # If num_communities increases as we decrease resolution, it means we might have passed an optimal point or the behavior is non-monotonic here
            # For this search (decreasing resolution to get fewer communities), if we get MORE communities than before, it's unusual.
            # If we get fewer than 3, we've gone too far.
            elif num_communities < 3:
                 print(f"Overshot: Found {num_communities} communities at resolution {current_resolution:.2f}. The optimal resolution for 3 communities might be between {current_resolution:.2f} and {current_resolution + step:.2f}.")
                 print("You may need to try finer steps in this range or the closest was " + f"{current_resolution + step:.2f}")

                 return
            
            last_num_communities = num_communities
        except Exception as e:
            print(f"Error during Louvain with resolution {current_resolution:.2f}: {e}")
            return

        current_resolution -= step
        current_resolution = round(current_resolution, 2) # Avoid floating point precision issues for step

    print(f"Could not find a resolution value down to {min_resolution:.2f} that results in exactly 3 communities. The number of communities at {min_resolution:.2f} was {last_num_communities}.")

if __name__ == '__main__':
    find_resolution_for_few_communities()
