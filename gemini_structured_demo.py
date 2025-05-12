import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import TypedDict, List
import json

# Load environment variables
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Define structured output types
class MovieReview(TypedDict):
    title: str
    rating: float
    pros: List[str]
    cons: List[str]

def get_structured_movie_review(movie_title: str) -> MovieReview:
    # Initialize Gemini model
    model = genai.GenerativeModel('gemini-pro')
    
    # Create prompt that forces structured output
    prompt = f"""
    Analyze the movie "{movie_title}" and provide a review in the following JSON structure:
    {{
        "title": "movie name",
        "rating": "rating out of 10",
        "pros": ["list", "of", "pros"],
        "cons": ["list", "of", "cons"]
    }}
    Only respond with valid JSON, no other text.
    """
    
    # Get response with structured output
    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.7
        }
    )
    
    # Parse JSON response
    review_data = json.loads(response.text)
    return review_data

def main():
    try:
        # Example usage
        movie = "The Matrix"
        review = get_structured_movie_review(movie)
        print(json.dumps(review, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 