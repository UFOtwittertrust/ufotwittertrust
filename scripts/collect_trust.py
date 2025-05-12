"""
Collect trust assignments from Twitter.
This script searches Twitter for #ufotrust tweets and extracts trust assignments.
"""

import http.client
import json
import re
import time
import os
from datetime import datetime, timedelta
import dateutil.parser
import logging
from logging.handlers import RotatingFileHandler

# File paths
CONFIG_FILE = "config.json"
DATA_FILE = "trust_assignments.json"
LOG_FILE = "twitter_collection.log"

# Set up logging
logger = logging.getLogger("twitter_collection")
handler = RotatingFileHandler(LOG_FILE, maxBytes=50000, backupCount=3)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)

def load_config():
    """Load configuration from file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "update_frequency_minutes": 10,
                "api_settings": {
                    "host": "twitter-api45.p.rapidapi.com",
                    "key": "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f",
                    "search_query": "#ufotrust",
                    "max_pages": 3
                },
                "collection_settings": {
                    "tweet_lookback_minutes": 15,
                    "delay_between_requests": 2
                },
                "trust_calculation": {
                    "rating_range": {
                        "min": 0,
                        "max": 100
                    },
                    "normalization": "l2",
                    "alpha": 0.85
                }
            }
    except Exception as e:
        logger.warning(f"Error loading config: {e}. Using defaults.")
        return {
            "update_frequency_minutes": 10,
            "api_settings": {
                "host": "twitter-api45.p.rapidapi.com",
                "key": "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f",
                "search_query": "#ufotrust",
                "max_pages": 3
            },
            "collection_settings": {
                "tweet_lookback_minutes": 15,
                "delay_between_requests": 2
            }
        }

def load_trust_data():
    """Load existing trust data from file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing {DATA_FILE}: {e}. Creating new data file.")
    
    # Create new trust data structure
    return {
        "assignments": {},  # source -> target -> value
        "last_updated": datetime.now().strftime("%B %d, %Y %I:%M %p"),
        "last_tweet_time": None  # Store timestamp of most recent tweet
    }

def save_trust_data(trust_data):
    """Save trust data to file."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(trust_data, f, indent=2)
        return True
    except Exception as e:
        logger.warning(f"Error saving {DATA_FILE}: {e}")
        return False

def search_tweets_with_pagination(query, trust_data, config):
    """Search Twitter for trust commands, using pagination and respecting time windows."""
    all_tweets = []
    cursor = None
    page_count = 0
    stop_time = None
    api_settings = config["api_settings"]
    collection_settings = config["collection_settings"]
    
    # Set up stop time based on configuration
    # If we have a last tweet timestamp, use it
    if trust_data.get("last_tweet_time"):
        try:
            stop_time = dateutil.parser.parse(trust_data["last_tweet_time"])
            logger.warning(f"Will collect tweets until reaching previous timestamp: {stop_time}")
        except Exception as e:
            logger.warning(f"Could not parse previous timestamp: {e}")
    else:
        # If no previous timestamp, look back by configured amount
        lookback_minutes = collection_settings.get("tweet_lookback_minutes", 15)
        stop_time = datetime.now() - timedelta(minutes=lookback_minutes)
        logger.warning(f"No previous timestamp found. Looking back {lookback_minutes} minutes to: {stop_time}")
    
    # Keep track of newest tweet time
    newest_tweet_time = None
    
    for page in range(api_settings.get("max_pages", 3)):
        page_count += 1
        logger.warning(f"Retrieving page {page+1}...")
        
        try:
            conn = http.client.HTTPSConnection(api_settings.get("host", "twitter-api45.p.rapidapi.com"))
            
            headers = {
                'x-rapidapi-key': api_settings.get("key", ""),
                'x-rapidapi-host': api_settings.get("host", "twitter-api45.p.rapidapi.com")
            }
            
            # URL encode the query
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            
            # Add cursor if we have one
            cursor_param = f"&cursor={cursor}" if cursor else ""
            endpoint = f"/search.php?query={encoded_query}&search_type=Latest{cursor_param}"
            
            conn.request("GET", endpoint, headers=headers)
            
            response = conn.getresponse()
            if response.status != 200:
                logger.warning(f"Error: API returned status {response.status}")
                break
            
            data = response.read()
            result = json.loads(data.decode("utf-8"))
            
            # Get tweets from this page
            tweets = result.get("timeline", [])
            if not tweets:
                logger.warning("No tweets found on this page")
                break
            
            # Check for the newest tweet time on the first page
            if page == 0 and tweets:
                try:
                    first_tweet = tweets[0]
                    if 'created_at' in first_tweet:
                        newest_time = dateutil.parser.parse(first_tweet['created_at'])
                        newest_tweet_time = first_tweet['created_at']
                        logger.warning(f"Newest tweet is from: {newest_time}")
                except Exception as e:
                    logger.warning(f"Error parsing newest tweet time: {e}")
            
            # Process tweets and check for stop time
            should_stop = False
            tweets_to_add = []
            
            for tweet in tweets:
                if 'created_at' in tweet:
                    try:
                        tweet_time = dateutil.parser.parse(tweet['created_at'])
                        
                        # If we've gone back to or beyond our stop time, stop collecting
                        if stop_time and tweet_time <= stop_time:
                            logger.warning(f"Reached stop point at tweet from {tweet_time}")
                            should_stop = True
                            break
                            
                        tweets_to_add.append(tweet)
                    except Exception as e:
                        logger.warning(f"Error parsing tweet time: {e}")
                        tweets_to_add.append(tweet)
                else:
                    tweets_to_add.append(tweet)
            
            # Add the filtered tweets
            all_tweets.extend(tweets_to_add)
            logger.warning(f"Retrieved {len(tweets_to_add)} new tweets on page {page+1}")
            
            if should_stop:
                logger.warning("Stopping pagination as we've reached the stop point")
                break
            
            # Get cursor for next page
            cursor = result.get("next_cursor")
            if not cursor:
                logger.warning("No more pages available")
                break
            
            # Sleep to avoid rate limiting
            delay = collection_settings.get("delay_between_requests", 2)
            time.sleep(delay)
            
        except Exception as e:
            logger.warning(f"Error retrieving page {page+1}: {e}")
            break
    
    # Update the last tweet time if we found newer tweets
    if newest_tweet_time and (not trust_data.get("last_tweet_time") or 
                              dateutil.parser.parse(newest_tweet_time) > 
                              dateutil.parser.parse(trust_data.get("last_tweet_time", "2000-01-01"))):
        trust_data["last_tweet_time"] = newest_tweet_time
        logger.warning(f"Updated last tweet timestamp to: {newest_tweet_time}")
    
    logger.warning(f"Retrieved a total of {len(all_tweets)} tweets across {page_count} pages")
    return all_tweets

def process_tweets():
    """Process tweets to extract trust assignments."""
    # Load configuration
    config = load_config()
    
    # Load existing trust data
    trust_data = load_trust_data()
    
    # Get search query from config
    query = config["api_settings"].get("search_query", "#ufotrust")
    max_pages = config["api_settings"].get("max_pages", 3)
    
    # Search for tweets
    tweets = search_tweets_with_pagination(query, trust_data, config)
    
    if not tweets:
        logger.warning("No new tweets found with trust commands. Exiting without error.")
        return 0
    
    logger.warning(f"Processing {len(tweets)} tweets for trust commands")
    
    processed_count = 0
    new_assignments = 0
    
    # Get regex pattern with configurable range
    min_rating = config["trust_calculation"]["rating_range"].get("min", 0)
    max_rating = config["trust_calculation"]["rating_range"].get("max", 100)
    
    # Regex pattern to match trust assignments
    trust_pattern_with_user = r'#ufotrust\s+@([A-Za-z0-9_]+)\s+([0-9]{1,3}(?:\.\d+)?)' # For #ufotrust @user score
    trust_pattern_reply = r'#ufotrust\s+([0-9]{1,3}(?:\.\d+)?)' # For #ufotrust score (in a reply)

    # Process each tweet
    for tweet in tweets:
        if tweet.get("type") != "tweet":
            continue
        text = tweet.get("text", "")
        author = tweet.get("screen_name", "")
        tweet_id = tweet.get("tweet_id", "unknown")
        in_reply_to_screen_name = None
        # Check if it's a reply from user_mentions (best guess if direct field not available)
        # A more robust way is to get 'in_reply_to_screen_name' directly from tweet object if API provides it.
        if tweet.get('entities') and tweet['entities'].get('user_mentions'):
            mentions = tweet['entities']['user_mentions']
            if mentions and text.startswith(f"@{mentions[0]['screen_name']}"):
                 # Check if the first mention is at the beginning of the tweet text
                if mentions[0]['indices'][0] == 0:
                    in_reply_to_screen_name = mentions[0]['screen_name']

        if not author or not text:
            continue
        logger.warning(f"Checking tweet {tweet_id} from @{author}")
        
        matches = re.findall(trust_pattern_with_user, text, re.IGNORECASE)
        target_username_from_reply = False

        if not matches and in_reply_to_screen_name:
            reply_matches = re.findall(trust_pattern_reply, text, re.IGNORECASE)
            if reply_matches:
                # Convert reply_matches to the same structure as matches
                matches = [(in_reply_to_screen_name, val) for val in reply_matches]
                target_username_from_reply = True # Flag to know this was a reply-based target
                logger.warning(f"Found reply-based trust command in tweet {tweet_id} to @{in_reply_to_screen_name}")

        if not matches:
            logger.warning(f"No trust commands found in tweet {tweet_id}")
            continue
        # Process each match
        for match in matches:
            target_username = match[0]
            try:
                trust_value = float(match[1] if not target_username_from_reply else match[1]) # match[1] for with_user, match for reply
                trust_value = max(min_rating, min(max_rating, trust_value))
            except (ValueError, IndexError) as e: # Added IndexError for reply case
                logger.warning(f"Invalid trust value or match structure in tweet {tweet_id}: {match} - Error: {e}")
                continue
            
            # Skip if author is trying to trust themselves
            if author.lower() == target_username.lower():
                logger.warning(f"Skipping self-trust from @{author}")
                continue
                
            # Store the trust assignment
            if author not in trust_data["assignments"]:
                trust_data["assignments"][author] = {}
            
            # Check if this is a new or changed assignment
            is_new = author not in trust_data["assignments"] or \
                    target_username not in trust_data["assignments"][author] or \
                    trust_data["assignments"][author][target_username] != trust_value
                    
            if is_new:
                new_assignments += 1
                
            trust_data["assignments"][author][target_username] = trust_value
            processed_count += 1
            logger.warning(f"Processed: @{author} trusts @{target_username} with {trust_value} points (0=distrust, 50=neutral, 100=trust)")
    
    # Update timestamp with time
    trust_data["last_updated"] = datetime.now().strftime("%B %d, %Y %I:%M %p")
    
    # Save updated data
    if save_trust_data(trust_data):
        logger.warning(f"Successfully saved {processed_count} trust assignments ({new_assignments} new/changed)")
    else:
        logger.warning("Failed to save trust assignments")
    
    return processed_count

def main():
    """Main function."""
    logger.warning("=== Starting Twitter Trust System Collection ===")
    
    try:
        processed = process_tweets()
        
        # Load trust data to get stats
        trust_data = load_trust_data()
        total_users = len(trust_data["assignments"])
        
        assignments_count = 0
        for user, targets in trust_data["assignments"].items():
            assignments_count += len(targets)
        
        logger.warning("Collection complete!")
        logger.warning(f"- {processed} trust assignments processed")
        logger.warning(f"- {total_users} users in trust network")
        logger.warning(f"- {assignments_count} total trust relationships")
        
        return processed > 0  # Return True if we found and processed any assignments
    except Exception as e:
        logger.error(f"Unhandled error in trust collection: {e}")
        return False

if __name__ == "__main__":
    main()