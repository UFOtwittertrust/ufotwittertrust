import http.client
import json
import random
import time
import os
import concurrent.futures
from collections import defaultdict
from dotenv import load_dotenv
import google.generativeai as genai
import re
import urllib.parse
import networkx as nx
import numpy as np

# Load environment variables
load_dotenv()

# --- Configuration ---
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY") # Replace with your actual key or ensure it's in .env
RAPIDAPI_HOST = "twitter-api45.p.rapidapi.com"
QUERY = "lue elizondo" # Or a more specific query related to UFOs/UAP
MAX_ACCOUNTS = 100 # Reduced target based on discussion -> INCREASED TO 150 -> SET TO 100
TIMELINE_PAGES_PER_ACCOUNT = 2 # Fetch 2 pages of timeline per account
MAX_WORKERS_API = 10 # For parallel API calls (fetching timelines/interactions)
MAX_WORKERS_LLM = 5  # For parallel LLM calls (trust analysis)
LLM_BATCH_SIZE = 5 # Number of trust assessments per LLM call
TRUST_THRESHOLD = 50 # Threshold for positive trust links in community detection

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")
genai.configure(api_key=GEMINI_API_KEY)
LLM_MODEL_NAME = 'gemini-1.5-flash' # Or another suitable model

# Configure Gemini Model (reuse if already configured)
# genai.configure(api_key=GEMINI_API_KEY)
llm_model = genai.GenerativeModel(LLM_MODEL_NAME)

# --- Helper for API Calls (Common structure) ---
def _call_rapidapi(endpoint):
    """Generic function to call the RapidAPI Twitter endpoint."""
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': RAPIDAPI_HOST
    }
    try:
        print(f"Calling endpoint: {endpoint}")
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        if res.status != 200:
            print(f"Error: API request failed with status {res.status} {res.reason}")
            print(f"Response body: {res.read().decode('utf-8')}")
            return None
        data = res.read()
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        print(f"Error during API call to {endpoint}: {str(e)}")
        return None
    finally:
        conn.close()

# --- Core Functions ---
def fetch_initial_accounts(query, max_accounts):
    """Fetches initial accounts based on a search query."""
    print(f"Fetching initial accounts for query: '{query}' up to {max_accounts} accounts...")
    accounts = {}
    cursor = None
    page_count = 0
    encoded_query = urllib.parse.quote(f'"{query}"')

    while len(accounts) < max_accounts:
        endpoint = f"/search.php?query={encoded_query}&search_type=Top"
        if cursor:
            endpoint += f"&cursor={cursor}"

        page_data = _call_rapidapi(endpoint)
        page_count += 1

        if not page_data or 'timeline' not in page_data or not page_data['timeline']:
            print(f"No more results found or API error after page {page_count}.")
            break

        tweets_fetched = 0
        for tweet in page_data['timeline']:
            # Use user_id as the primary key if available, otherwise screen_name
            user_info = tweet.get('user_info', {})
            user_id = user_info.get('id_str') or tweet.get('user_id') # Prefer id_str if present
            handle = tweet.get('screen_name')

            if not user_id and not handle:
                print("Warning: Tweet found without user_id or screen_name, skipping.")
                continue

            # Use screen_name as a fallback identifier if id is missing, but prioritize ID
            account_key = user_id if user_id else handle

            if account_key not in accounts:
                if len(accounts) >= max_accounts:
                    break # Stop adding if max accounts reached
                accounts[account_key] = {
                    'id': user_id,
                    'screen_name': handle,
                    'name': user_info.get('name'),
                    'followers': user_info.get('followers_count'),
                    'verified': user_info.get('verified', False),
                    'profile_image_url': user_info.get('profile_image_url_https'),
                    'tweets': [] # We might fetch timelines later
                }
            # Optionally store the initial tweet that led us to the account
            # accounts[account_key]['tweets'].append(tweet['text'])
            tweets_fetched += 1

        print(f"Fetched page {page_count}. Added {tweets_fetched} tweets. Total unique accounts: {len(accounts)}")

        cursor = page_data.get('next_cursor')
        if not cursor:
            print("No next cursor found. Stopping search.")
            break

        # Optional: Add a small delay to avoid rate limits, though RapidAPI might handle this
        time.sleep(1)

    print(f"Initial account collection complete. Found {len(accounts)} unique accounts.")
    return accounts

def fetch_user_timeline(screen_name, max_pages=TIMELINE_PAGES_PER_ACCOUNT):
    """Fetches recent tweets for a specific user using their screen name."""
    print(f"Fetching timeline for account: @{screen_name} (up to {max_pages} pages)...")
    timeline = []
    cursor = None
    pages_fetched = 0
    param_name = "screenname"
    param_value = urllib.parse.quote(screen_name)

    while pages_fetched < max_pages:
        # Construct the endpoint using /timeline.php and screenname parameter
        endpoint = f"/timeline.php?{param_name}={param_value}"
        if cursor:
            endpoint += f"&cursor={cursor}"

        page_data = _call_rapidapi(endpoint)
        pages_fetched += 1

        if not page_data:
            print(f"API call failed or returned no data for @{screen_name} on page {pages_fetched}.")
            break
            
        # Expecting a structure like {'timeline': [...], 'next_cursor': ...}
        if 'timeline' not in page_data:
            print(f"No 'timeline' key found in response for @{screen_name} on page {pages_fetched}. Response keys: {page_data.keys() if isinstance(page_data, dict) else 'Not a dict'}")
            break

        found_tweets = page_data['timeline']
        if not found_tweets:
            print(f"No tweets found in timeline for @{screen_name} on page {pages_fetched}.")
            break

        timeline.extend(found_tweets)
        print(f"   Fetched page {pages_fetched} for @{screen_name}, {len(found_tweets)} tweets.")

        cursor = page_data.get('next_cursor')
        if not cursor:
            # print(f"   No next cursor for @{screen_name}. Reached end of timeline or page limit.")
            break

        time.sleep(0.5) # Small delay between pages for the same user

    print(f"Finished fetching timeline for @{screen_name}. Total tweets: {len(timeline)}")
    return timeline

def fetch_conversation_thread(tweet_id):
    """Fetches a conversation thread given the ID of a tweet within it."""
    print(f"Fetching conversation thread for tweet ID: {tweet_id}...")
    endpoint = f"/tweet_thread.php?id={tweet_id}"
    thread_data = _call_rapidapi(endpoint)

    if not thread_data or not isinstance(thread_data, dict):
        print(f"  Failed to fetch or parse thread for tweet ID {tweet_id}.")
        return None

    # The example shows the actual thread tweets are in a 'thread' key
    if 'thread' not in thread_data or not isinstance(thread_data['thread'], list):
        print(f"  No 'thread' list found in response for tweet ID {tweet_id}. Keys: {thread_data.keys()}")
        # Return the top-level data perhaps? Or indicate failure?
        # Let's return the raw dict for now, maybe thread is optional?
        # Or better, return None if the crucial 'thread' part is missing.
        return None
        
    print(f"  Successfully fetched thread for tweet ID {tweet_id}, found {len(thread_data['thread'])} tweets in thread.")
    # Return the list of tweet objects within the thread
    return thread_data['thread']

def fetch_interactions(account_screen_names):
    """Finds interaction tweets, extracts conversation IDs, and fetches full threads."""
    print(f"\nFinding relevant conversation IDs for {len(account_screen_names)} accounts...")
    # interaction_tweets_by_pair: {(screen_name1, screen_name2): [tweet_objects_from_search]}
    interaction_tweets_by_pair = defaultdict(list)
    # relevant_conv_ids_by_pair: {(screen_name1, screen_name2): set(conversation_ids)}
    relevant_conv_ids_by_pair = defaultdict(set)
    # all_fetched_threads: {conversation_id: [tweet_objects_in_thread]}
    all_fetched_threads = {}
    
    # Generate unique pairs
    account_pairs = []
    for i in range(len(account_screen_names)):
        for j in range(i + 1, len(account_screen_names)):
            account_pairs.append(tuple(sorted((account_screen_names[i], account_screen_names[j]))))
    print(f"Generated {len(account_pairs)} unique screen name pairs to check.")

    # --- Stage 1: Search for tweets mentioning pairs to find conversation IDs --- 
    print("--- Stage 1: Searching for tweets mentioning pairs to identify relevant conversations ---")
    def find_mentioning_tweets(pair):
        acc1_sn, acc2_sn = pair
        query = f"(@{acc1_sn} @{acc2_sn}) OR (from:{acc1_sn} @{acc2_sn}) OR (from:{acc2_sn} @{acc1_sn})"
        encoded_query = urllib.parse.quote(query)
        endpoint = f"/search.php?query={encoded_query}&search_type=Top&count=20" # Limit search results?
        page_data = _call_rapidapi(endpoint)
        found_tweets = []
        if page_data and 'timeline' in page_data:
            found_tweets = page_data['timeline']
        return pair, found_tweets

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_API) as executor:
        future_to_pair = {executor.submit(find_mentioning_tweets, pair): pair for pair in account_pairs}
        for future in concurrent.futures.as_completed(future_to_pair):
            pair, tweets = future.result()
            if tweets:
                interaction_tweets_by_pair[pair].extend(tweets)
                for tweet in tweets:
                    conv_id = tweet.get('conversation_id')
                    if conv_id:
                        relevant_conv_ids_by_pair[pair].add(conv_id)
    
    unique_conv_ids = set().union(*relevant_conv_ids_by_pair.values())
    print(f"--- Stage 1 Complete: Found {len(interaction_tweets_by_pair)} pairs mentioned. Identified {len(unique_conv_ids)} unique relevant conversation IDs.")

    # --- Stage 2: Fetch the full conversation threads for unique IDs --- 
    print("--- Stage 2: Fetching full conversation threads ---")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_API) as executor:
        future_to_conv_id = {executor.submit(fetch_conversation_thread, conv_id): conv_id for conv_id in unique_conv_ids}
        for future in concurrent.futures.as_completed(future_to_conv_id):
            conv_id = future_to_conv_id[future]
            try:
                thread_tweets = future.result()
                if thread_tweets: # Only store successfully fetched threads
                    all_fetched_threads[conv_id] = thread_tweets
            except Exception as exc:
                print(f'Conversation thread fetch for {conv_id} generated an exception: {exc}')

    print(f"--- Stage 2 Complete: Successfully fetched {len(all_fetched_threads)} conversation threads.")

    # --- Stage 3: Map fetched threads back to the relevant pairs --- 
    # final_threads_by_pair: {(userA_sn, userB_sn): [[tweets_thread1], [tweets_thread2], ...]}
    final_threads_by_pair = defaultdict(list)
    for pair, conv_ids_set in relevant_conv_ids_by_pair.items():
        for conv_id in conv_ids_set:
            if conv_id in all_fetched_threads:
                # Check if this thread actually contains posts from *both* users in the pair
                # This is an important filter to ensure relevance
                thread_authors = set(t.get('author', {}).get('screen_name') for t in all_fetched_threads[conv_id] if t.get('author'))
                user_a_sn, user_b_sn = pair
                if user_a_sn in thread_authors and user_b_sn in thread_authors:
                    final_threads_by_pair[pair].append(all_fetched_threads[conv_id])
                # else: 
                    # print(f"DEBUG: Skipping thread {conv_id} for pair {pair} as it doesn't contain both authors.")
            # else: 
                # print(f"DEBUG: Thread {conv_id} relevant to pair {pair} was not successfully fetched.")

    print(f"\nFinished processing interactions. Found relevant threads for {len(final_threads_by_pair)} pairs.")
    return final_threads_by_pair

# Function to extract relevant text from tweets
def _extract_text(tweets):
    # --- DEBUG ---
    # input_desc = "(empty list)"
    # if tweets:
    #     input_desc = f"{len(tweets)} items. First item type: {type(tweets[0]) if tweets else 'N/A'}"
    # print(f"DEBUG _extract_text: Received {input_desc}")
    # --- END DEBUG ---
    if not tweets:
        return []
    # Assuming tweets is a list of dicts with a 'text' key
    extracted = [t.get('text', '') for t in tweets if isinstance(t, dict) and t.get('text')]
    # --- DEBUG ---
    # print(f"DEBUG _extract_text: Extracted {len(extracted)} texts.")
    # --- END DEBUG ---
    return extracted

def _get_llm_trust_rating(user_a_screen_name, user_b_screen_name, thread_list, context_a, context_b):
    """Performs a single LLM call to rate trust from A to B, based on threads and timelines."""
    try:
        # Concatenate text from all tweets in all provided threads for this pair
        interaction_texts = []
        for thread in thread_list:
            interaction_texts.extend(_extract_text(thread))
            
        # Prepare timeline context (using full fetched timeline)
        context_a_texts = _extract_text(context_a)
        context_b_texts = _extract_text(context_b)

        interaction_snippet = "\n".join(interaction_texts) 
        context_a_snippet = "\n".join(context_a_texts)
        context_b_snippet = "\n".join(context_b_texts)

        # Return neutral if no interaction snippet from threads
        if not interaction_snippet:
             # DEBUG: Let's log when this specific condition is met
             print(f"DEBUG: No interaction snippet found for (@{user_a_screen_name} -> @{user_b_screen_name}). Returning neutral (50).")
             return 50

        # --- Start Explicit Debug Prints (Always Run) ---
        print(f"--- DEBUG: Preparing LLM call for (@{user_a_screen_name} -> @{user_b_screen_name}) ---")
        print(f"Interaction Snippet Length: {len(interaction_snippet)}")
        print(f"Interaction Snippet Preview: {interaction_snippet[:200].replace('\\n', ' ')}...") # Show preview, replace newlines for readability
        print(f"Context A Snippet Length: {len(context_a_snippet)}")
        print(f"Context B Snippet Length: {len(context_b_snippet)}")
        # --- End Explicit Debug Prints ---

        # Updated Prompt - Requesting JSON output
        prompt = f"""
        Analyze the trust relationship between two Twitter users based on their participation in conversation threads and their general timelines.

        USER A: @{user_a_screen_name}
        USER B: @{user_b_screen_name}

        CONVERSATION THREAD(S) involving both A and B:
        --- Start of Thread(s) ---
        {interaction_snippet}
        --- End of Thread(s) ---

        USER A's (@{user_a_screen_name}) recent general tweets (timeline context):
        --- Start of Timeline A ---
        {context_a_snippet}
        --- End of Timeline A ---

        USER B's (@{user_b_screen_name}) recent general tweets (timeline context):
        --- Start of Timeline B ---
        {context_b_snippet}
        --- End of Timeline B ---

        Based on the provided conversation thread(s) and timeline context:
        1. Analyze how USER A and USER B interact or align within the thread(s).
        2. Consider their general timeline context.
        3. Estimate how much USER A (@{user_a_screen_name}) likely trusts USER B (@{user_b_screen_name}).

        Return ONLY a JSON object containing the score, like this: {{"score": &lt;integer_score_0_to_100&gt;}}
        Do not include any other text, explanation, or formatting before or after the JSON object.
        """

        # Generate response
        response = llm_model.generate_content(prompt)

        # Parse the JSON rating
        rating_text = response.text.strip()
        try:
            # --- Explicitly remove markdown backticks and language identifier --- #
            cleaned_text = rating_text
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:] # Remove ```json
            if cleaned_text.startswith('```'):
                 cleaned_text = cleaned_text[3:] # Remove ```
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3] # Remove ```
            cleaned_text = cleaned_text.strip() # Strip again after removal
            # --- End Cleaning --- #

            # print(f"  DEBUG: Cleaned text: [{cleaned_text}]") # Optional debug
            data = json.loads(cleaned_text) # Attempt to parse the cleaned string
            rating = int(data['score'])
            return max(0, min(100, rating))

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Handle cases where cleaned string is not valid JSON or lacks 'score' key
            print(f"Warning: Error parsing JSON or extracting score for (@{user_a_screen_name} -> @{user_b_screen_name}). Error: {e}. Response: '{rating_text[:150]}...'. Returning neutral (50).")
            # --- Print full response on JSON failure for debugging ---
            print(f"--- DEBUG: Full LLM Response (JSON Parse Failed) ---")
            print(rating_text)
            print(f"--- End Debug ---")
            return 50

    except Exception as e:
        print(f"Error getting LLM trust rating for (@{user_a_screen_name} -> @{user_b_screen_name}): {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback') and e.response.prompt_feedback.block_reason:
             print(f"   Reason: Blocked by API - {e.response.prompt_feedback.block_reason}")
        return 50

def analyze_trust_with_llm(threads_by_pair, timeline_context, accounts_dict):
    """Uses LLM to analyze trust based on conversation threads and timelines.
       - threads_by_pair uses screen names as keys: {(A_sn, B_sn): [[thread1_tweets], [thread2_tweets]]}
       - timeline_context uses account_keys (ID or screen_name) as keys.
       - accounts_dict maps account_key to account details.
    """
    print(f"\nAnalyzing trust for {len(threads_by_pair)} interacting pairs using fetched threads and timelines...")
    trust_ratings = [] # List of {'source': key, 'target': key, 'trust': score}
    tasks = []

    screen_name_to_key = {data['screen_name']: key
                           for key, data in accounts_dict.items() if data.get('screen_name')}

    # Prepare tasks for parallel execution
    for pair_screen_names, list_of_threads in threads_by_pair.items():
        user_a_sn, user_b_sn = pair_screen_names
        user_a_key = screen_name_to_key.get(user_a_sn)
        user_b_key = screen_name_to_key.get(user_b_sn)

        if not user_a_key or not user_b_key:
            print(f"Warning: Could not find account key mapping for interaction pair: (@{user_a_sn}, @{user_b_sn}). Skipping.")
            continue
            
        if not list_of_threads: # Skip if no threads were actually fetched/relevant for this pair
            print(f"Notice: No relevant threads found/fetched containing both @{user_a_sn} and @{user_b_sn}. Skipping LLM analysis for this pair.")
            continue

        context_a = timeline_context.get(user_a_key, [])
        context_b = timeline_context.get(user_b_key, [])

        # Pass the list of threads to the helper function
        # Task: (user_a_sn, user_b_sn, list_of_threads, context_a, context_b)
        tasks.append((user_a_sn, user_b_sn, list_of_threads, context_a, context_b))
        tasks.append((user_b_sn, user_a_sn, list_of_threads, context_b, context_a))

    print(f"Prepared {len(tasks)} trust rating tasks for LLM analysis based on threads.")

    # Parallel execution for LLM calls
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_LLM) as executor:
        future_to_task_info = {executor.submit(_get_llm_trust_rating, *task): (task[0], task[1]) for task in tasks}

        processed_count = 0
        for future in concurrent.futures.as_completed(future_to_task_info):
            source_sn, target_sn = future_to_task_info[future]
            processed_count += 1
            try:
                trust_score = future.result()
                source_key = screen_name_to_key.get(source_sn)
                target_key = screen_name_to_key.get(target_sn)
                if source_key and target_key:
                    trust_ratings.append({
                        'source': source_key,
                        'target': target_key,
                        'trust': trust_score,
                        'timestamp': int(time.time())
                    })
                else:
                    print(f"Warning: Could not map screen names back to keys for rating (@{source_sn} -> @{target_sn}).")
            except Exception as exc:
                print(f'LLM task for (@{source_sn} -> @{target_sn}) generated an exception: {exc}')
            # else:
            #     if processed_count % 10 == 0 or processed_count * 2 >= len(tasks):
            #         print(f"  LLM Analysis Progress: {processed_count * 2}/{len(tasks)} ratings determined...")

    print(f"\nFinished LLM trust analysis using threads. Generated {len(trust_ratings)} directed trust ratings.")
    return trust_ratings

def build_trust_network(accounts_dict, trust_ratings):
    """Builds the NetworkX DiGraph from accounts and trust ratings."""
    print("\nBuilding trust network graph...")
    G = nx.DiGraph()

    # Add nodes with attributes
    for account_key, data in accounts_dict.items():
        G.add_node(
            account_key, # Node ID is the key used throughout (ID or screen_name)
            id=data.get('id'),
            screen_name=data.get('screen_name'),
            name=data.get('name'),
            followers=data.get('followers'),
            verified=data.get('verified'),
            profile_image_url=data.get('profile_image_url'),
            community=None, # Placeholder for community ID
            score=50 # Placeholder for overall score
        )

    print(f"Added {G.number_of_nodes()} nodes to the graph.")

    # Add edges with trust attributes
    edges_added = 0
    for rating in trust_ratings:
        source = rating['source']
        target = rating['target']
        trust = rating['trust']
        timestamp = rating['timestamp']

        # Ensure both source and target nodes exist in the graph
        if G.has_node(source) and G.has_node(target):
            G.add_edge(source, target, trust=trust, timestamp=timestamp)
            # --- Add Print Statement ---
            print(f"  Added edge: {source} -> {target} with trust = {trust}")
            # --- End Print Statement ---
            edges_added += 1
        else:
            print(f"Warning: Skipping edge ({source} -> {target}) because one or both nodes not in graph.")

    print(f"Added {edges_added} directed edges (trust ratings) to the graph.")
    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    return G

def detect_communities(G):
    """Detects communities in the trust network using the Louvain algorithm
       based on positive trust relationships.
       Updates the graph nodes with community assignments.
    """
    print("\nDetecting communities in the trust network...")

    # Create an undirected graph including only positive trust edges
    G_positive_trust = nx.Graph()
    for node, data in G.nodes(data=True):
        G_positive_trust.add_node(node, **data) # Copy node data

    positive_edges = 0
    for u, v, data in G.edges(data=True):
        trust = data.get('trust', 0)
        if trust > TRUST_THRESHOLD:
            # Scale trust from TRUST_THRESHOLD-100 to a small positive range (e.g., 0.1-1) for weight
            # Avoid zero weight; ensure higher trust means stronger connection
            weight = max(0.01, (trust - TRUST_THRESHOLD) / (100 - TRUST_THRESHOLD))
            G_positive_trust.add_edge(u, v, weight=weight)
            positive_edges += 1

    print(f"Created subgraph for community detection with {G_positive_trust.number_of_nodes()} nodes and {positive_edges} positive trust edges.")

    if G_positive_trust.number_of_edges() == 0:
        print("No positive trust relationships found above threshold. Assigning all nodes to community 0.")
        community_map = {node: 0 for node in G.nodes()}
        nx.set_node_attributes(G, community_map, 'community')
        return community_map

    # Identify isolated nodes in the positive trust graph
    all_nodes = set(G.nodes())
    connected_nodes = set(G_positive_trust.nodes())
    isolated_nodes = list(all_nodes - connected_nodes)
    # Also find nodes *in* the positive graph but potentially disconnected from the main component
    nodes_in_positive_graph_with_no_edges = list(nx.isolates(G_positive_trust))
    all_isolated = set(isolated_nodes + nodes_in_positive_graph_with_no_edges)

    print(f"Found {len(all_isolated)} isolated nodes (no positive trust links above threshold).")

    # Create a graph component for Louvain without isolated nodes
    G_community_detect = G_positive_trust.copy()
    G_community_detect.remove_nodes_from(all_isolated)

    community_map = {}
    if G_community_detect.number_of_nodes() > 0:
        print(f"Running Louvain algorithm on {G_community_detect.number_of_nodes()} connected nodes...")
        # Use weight for community detection
        communities = nx.community.louvain_communities(G_community_detect, weight='weight', resolution=1.0)

        # Assign community IDs (start from 1)
        comm_id_counter = 1
        for community_set in communities:
            for node in community_set:
                community_map[node] = comm_id_counter
            comm_id_counter += 1
        print(f"Detected {comm_id_counter - 1} communities among connected nodes.")
    else:
        print("No connected components found after removing isolated nodes.")

    # Assign isolated nodes to a default community (e.g., 0)
    for node in all_isolated:
        community_map[node] = 0 # Assign to community 0
    if all_isolated:
        print(f"Assigned {len(all_isolated)} isolated nodes to community 0.")

    # Update the original graph G with community assignments
    nx.set_node_attributes(G, community_map, 'community')
    print("Updated node attributes in the main graph with community IDs.")

    return community_map

def save_network_data(G, filename_prefix):
    """Saves the network node and link data to a JS file for visualization."""
    print(f"\nPreparing and saving network data to {filename_prefix}.js...")

    # Prepare node data
    nodes_data = []
    for node_id, data in G.nodes(data=True):
        nodes_data.append({
            'id': node_id, # The key used in the graph (ID or screen_name)
            'screen_name': data.get('screen_name', node_id), # Ensure screen_name is present
            'name': data.get('name', data.get('screen_name', node_id)), # Fallback name
            'community': data.get('community', 0), # Default community if missing
            'score': data.get('score', 50), # Default score if missing
            'followers': data.get('followers'),
            'verified': data.get('verified'),
            'profile_image_url': data.get('profile_image_url')
        })

    # Prepare link data
    links_data = []
    for u, v, data in G.edges(data=True):
        links_data.append({
            'source': u,
            'target': v,
            'trust': data.get('trust', 50), # Default trust if missing
            'timestamp': data.get('timestamp', int(time.time())) # Default timestamp if missing
        })

    # Combine into final structure
    graph_data = {
        'nodes': nodes_data,
        'links': links_data
    }

    # Ensure the js directory exists
    os.makedirs("js", exist_ok=True)

    # Write to JS file
    output_filename = f"{filename_prefix}.js"
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            # Use a variable name suitable for the visualization JS
            f.write(f"const enhancedTrustData = {json.dumps(graph_data, indent=2)};")
        print(f"Successfully wrote network data to {output_filename}")
    except IOError as e:
        print(f"Error writing network data to {output_filename}: {str(e)}")

def calculate_node_scores(G):
    """Calculates a score for each node based on incoming trust.
       Updates the graph nodes with the calculated score.
    """
    print("\nCalculating node scores (average incoming trust)...")
    scores = {}
    for node in G.nodes():
        incoming_edges = G.in_edges(node, data=True)
        incoming_trust_values = [data.get('trust', 50) for _, _, data in incoming_edges]

        if not incoming_trust_values:
            # Assign default score (e.g., 50) if no incoming links
            scores[node] = 50
        else:
            # Calculate average incoming trust
            scores[node] = sum(incoming_trust_values) / len(incoming_trust_values)

    # Update node attributes
    nx.set_node_attributes(G, scores, 'score')
    print("Updated node attributes with calculated scores.")
    return scores # Return the scores dict as well

# --- Main Execution Logic ---
def main():
    print("Starting Enhanced Twitter Trust Network Generation...")

    # 1. Fetch initial set of accounts
    initial_accounts = fetch_initial_accounts(QUERY, MAX_ACCOUNTS)

    # 2. Fetch timelines for context (Optional but recommended)
    timeline_context = {} # Store timelines: {account_key: [tweets]}
    account_keys = list(initial_accounts.keys())

    print(f"\nFetching timelines for {len(account_keys)} accounts (max {TIMELINE_PAGES_PER_ACCOUNT} pages each)...")
    # Use ThreadPoolExecutor for parallel fetching
    # Note: Adjust MAX_WORKERS_API based on API rate limits and system capacity
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_API) as executor:
        # Create a future for each account timeline fetch
        # Pass the screen_name specifically to fetch_user_timeline
        future_to_account = {}
        for key, account_data in initial_accounts.items():
            screen_name = account_data.get('screen_name')
            if screen_name:
                future = executor.submit(fetch_user_timeline, screen_name)
                future_to_account[future] = key # Map future back to original account key
            else:
                print(f"Warning: Account key {key} missing screen_name, cannot fetch timeline.")

        processed_count = 0
        total_futures = len(future_to_account)
        for future in concurrent.futures.as_completed(future_to_account):
            account_key = future_to_account[future]
            screen_name = initial_accounts[account_key].get('screen_name', '[unknown]') # For logging
            processed_count += 1
            try:
                # Get the result (the list of tweets)
                tweets = future.result()
                timeline_context[account_key] = tweets
                # Optionally update the main accounts dictionary too
                if account_key in initial_accounts:
                    # Store raw tweet objects or just text?
                    # Storing raw objects might be useful for LLM later
                    initial_accounts[account_key]['tweets_raw'] = tweets
                    initial_accounts[account_key]['tweets'] = _extract_text(tweets) # Keep storing text too
            except Exception as exc:
                print(f'Timeline fetch for @{screen_name} (key: {account_key}) generated an exception: {exc}')
            # else:
                 # Be less verbose, print handled in fetch_user_timeline
                 # print(f"Successfully processed timeline for @{screen_name} ({processed_count}/{total_futures})")

    print(f"\nFinished fetching all timelines. Context available for {len(timeline_context)} accounts.")

    # 3. Identify pairs/groups and fetch interactions
    # Ensure fetch_interactions uses appropriate identifiers (screen names?)
    # Need to get screen names from initial_accounts for the interaction query
    account_screen_names = [acc['screen_name'] for acc in initial_accounts.values() if acc.get('screen_name')]
    interaction_data = fetch_interactions(account_screen_names) # Pass screen names

    # 4. Analyze trust using LLM
    # The keys in timeline_context and initial_accounts are account_key (ID or screen name)
    # The keys in interaction_data are tuples of screen names
    # Need to adapt analyze_trust_with_llm to handle this
    trust_ratings = analyze_trust_with_llm(interaction_data, timeline_context, initial_accounts)

    # 5. Build the graph
    # Pass initial_accounts which contains node attributes
    graph = build_trust_network(initial_accounts, trust_ratings)

    # 6. Detect communities
    communities_map = detect_communities(graph) # Updates graph nodes in place

    # 7. Calculate final node scores
    node_scores = calculate_node_scores(graph)

    # 8. Prepare and save data for visualization
    save_network_data(graph, "js/data_twitter_enhanced")

    print("\nEnhanced Twitter Trust Network Generation Complete.")
    print(f"Output saved to js/data_twitter_enhanced.js")
    print("Next steps: Create or adapt an HTML file to visualize this data using D3.js")

if __name__ == "__main__":
    # Placeholder for actual execution
    # print("Script structure created. Implementation pending.") # No longer needed
    main() # Execute the main function 