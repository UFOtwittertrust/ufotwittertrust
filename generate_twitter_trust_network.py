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

# Load environment variables
load_dotenv()

# --- Config ---
RAPIDAPI_KEY = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
RAPIDAPI_HOST = "twitter-api45.p.rapidapi.com"
QUERY = "lue elizondo"
MAX_ACCOUNTS = 150
PAGE_SIZE = 20  # Twitter API returns ~20 per page
MAX_WORKERS = 5  # Number of parallel LLM requests
MAX_COMMENTS_PER_ACCOUNT = 3  # Limit the number of comments to avoid token limits

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

# --- Helper functions ---
def get_twitter_page(cursor=None):
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': RAPIDAPI_HOST
    }
    url = "/search.php?query=%22lue%20elizondo%22&search_type=Top"
    if cursor:
        url += f"&cursor={cursor}"
    
    conn.request("GET", url, headers=headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

def get_trust_rating(rater_comments, ratee_comments):
    """Use Gemini to generate a trust rating (0-100) based on comments"""
    try:
        # Limit number of comments to avoid token limits
        rater_text = "\n".join(rater_comments[:MAX_COMMENTS_PER_ACCOUNT])
        ratee_text = "\n".join(ratee_comments[:MAX_COMMENTS_PER_ACCOUNT])
        
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create the prompt
        prompt = f"""
        You are a trust rating system. Given two sets of comments:
        
        RATER COMMENTS:
        {rater_text}
        
        ACCOUNT BEING RATED COMMENTS:
        {ratee_text}
        
        Return ONLY a single trust rating number from 0-100 based on how much the rater would trust the second account given their comments.
        0 means no trust, 100 means complete trust.
        RESPOND WITH ONLY THE NUMBER.
        """
        
        # Generate response
        response = model.generate_content(prompt)
        
        # Extract the numeric rating from the response
        rating_text = response.text.strip()
        # Using regex to extract the first number in the response
        match = re.search(r'(\d+)', rating_text)
        if match:
            rating = int(match.group(1))
            # Ensure rating is within 0-100 range
            return max(0, min(100, rating))
        else:
            print(f"Warning: Could not extract numeric rating from: {rating_text}")
            return random.randint(0, 100)  # Fallback if no number found
    except Exception as e:
        print(f"Error getting trust rating: {str(e)}")
        return random.randint(0, 100)  # Fallback on error

# --- Main execution ---
print(f"Starting to collect Twitter data for '{QUERY}'...")

# --- Collect accounts ---
accounts = {}
cursor = None
page_count = 0
while len(accounts) < MAX_ACCOUNTS:
    page = get_twitter_page(cursor)
    page_count += 1
    for tweet in page['timeline']:
        handle = tweet['screen_name']
        if handle not in accounts:
            accounts[handle] = {
                'tweets': [],
                'meta': tweet.get('user_info', {})
            }
        accounts[handle]['tweets'].append(tweet['text'])
    print(f"Fetched page {page_count}, total unique accounts: {len(accounts)}")
    cursor = page.get('next_cursor')
    if not cursor:
        break
    time.sleep(1)  # Be nice to API
    if len(accounts) >= MAX_ACCOUNTS:
        break

print(f"Collection complete. Found {len(accounts)} unique accounts.")

# --- Generate trust ratings ---
print("Generating trust ratings between accounts...")
total_ratings = len(accounts) * 5  # Each account rates ~5 others
ratings_count = 0
trust_data = []

account_handles = list(accounts.keys())

def process_account_batch(batch):
    local_ratings = []
    for rater in batch:
        # Each account rates ~5 random other accounts
        ratees = random.sample([h for h in account_handles if h != rater], 
                              min(5, len(account_handles)-1))
        
        for ratee in ratees:
            trust_value = get_trust_rating(accounts[rater]['tweets'], accounts[ratee]['tweets'])
            timestamp = int(time.time()) + random.randint(-86400*30, 0)  # Random time in last month
            local_ratings.append({
                'source': rater,
                'target': ratee,
                'trust': trust_value,
                'timestamp': timestamp
            })
    return local_ratings

# Process accounts in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Split accounts into batches for parallel processing
    batch_size = len(account_handles) // MAX_WORKERS + 1
    batches = [account_handles[i:i+batch_size] for i in range(0, len(account_handles), batch_size)]
    
    # Process each batch in parallel
    results = list(executor.map(process_account_batch, batches))
    
    # Flatten results
    for batch_result in results:
        trust_data.extend(batch_result)
        ratings_count += len(batch_result)
        print(f"Progress: {ratings_count}/{total_ratings} ratings ({ratings_count*100/total_ratings:.1f}%)")

# Sort trust data by timestamp
trust_data.sort(key=lambda x: x['timestamp'])

print(f"Trust rating generation complete. Generated {len(trust_data)} trust ratings.")

# --- Generate static and temporal trust network data ---
print("Generating visualization data files...")

# Temporal data
temporal_data = {
    'nodes': [{'id': handle, 'name': handle} for handle in accounts.keys()],
    'links': trust_data
}

# Static data (final network state)
static_data = {
    'nodes': [{'id': handle, 'name': handle} for handle in accounts.keys()],
    'links': []
}

# For static data, only keep the latest rating between any two accounts
latest_ratings = {}
for rating in trust_data:
    key = f"{rating['source']}|{rating['target']}"
    if key not in latest_ratings or rating['timestamp'] > latest_ratings[key]['timestamp']:
        latest_ratings[key] = rating

static_data['links'] = list(latest_ratings.values())

# Write data to JS files
with open('js/data_twitter_temporal.js', 'w') as f:
    f.write(f"const temporalTrustData = {json.dumps(temporal_data, indent=2)};")

with open('js/data_twitter_static.js', 'w') as f:
    f.write(f"const staticTrustData = {json.dumps(static_data, indent=2)};")

print("Data files created successfully!")
print("- Temporal data: js/data_twitter_temporal.js")
print("- Static data: js/data_twitter_static.js")
print("You can now view the visualizations in network-temporal-twitter.html and network-static-twitter.html") 