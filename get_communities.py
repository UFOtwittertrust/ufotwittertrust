import json
import re

# Read the data_twitter_static.js file
with open('js/data_twitter_static.js', 'r') as f:
    data = f.read()

# Extract the JSON part
data = data.replace('const staticTrustData = ', '')
if data.endswith(';'):
    data = data[:-1]  # Remove trailing semicolon

# Parse the JSON
try:
    trust_data = json.loads(data)
    # Group by community
    communities = {}
    for node in trust_data['nodes']:
        community_id = node['community']
        if community_id not in communities:
            communities[community_id] = []
        communities[community_id].append(node['id'])
    
    # Print out each community more compactly
    for community_id in sorted(communities.keys()):
        accounts = sorted(communities[community_id])
        print(f"Community {community_id} ({len(accounts)} members): {', '.join(accounts)}")
        
except json.JSONDecodeError as e:
    print(f"Error parsing JSON: {e}")
    # Try to extract using regex as fallback
    nodes_pattern = re.compile(r'"id": "(.*?)",\s*"name": ".*?",\s*"community": (\d+),')
    matches = nodes_pattern.findall(data)
    
    communities = {}
    for account, community_id in matches:
        community_id = int(community_id)
        if community_id not in communities:
            communities[community_id] = []
        communities[community_id].append(account)
    
    # Print out each community more compactly
    for community_id in sorted(communities.keys()):
        accounts = sorted(communities[community_id])
        print(f"Community {community_id} ({len(accounts)} members): {', '.join(accounts)}") 