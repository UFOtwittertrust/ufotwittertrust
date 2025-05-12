import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Securely get the API key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# Check if the key was loaded
if not openai.api_key:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    # Optionally exit or handle the error appropriately
    exit()

def get_openai_rating(prompt_text):
    """Simple function to get a rating using OpenAI (requires setup)."""
    try:
        response = openai.Completion.create(
            engine="text-davinci-003", # Or another suitable model
            prompt=prompt_text,
            max_tokens=50,
            temperature=0.5
        )
        # Basic extraction - adapt as needed for your specific prompt/response
        rating_text = response.choices[0].text.strip()
        # Add parsing logic here (e.g., find number)
        print(f"OpenAI Raw Response: {rating_text}")
        return rating_text # Return raw text for now
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

# Example Usage (optional - keep commented out or remove if not needed)
# if __name__ == "__main__":
#     test_prompt = "Rate the trustworthiness of this statement on a scale of 0-100: 'The sky is blue.'"
#     rating = get_openai_rating(test_prompt)
#     if rating:
#         print(f"Received rating/response: {rating}")
#     else:
#         print("Failed to get rating.") 