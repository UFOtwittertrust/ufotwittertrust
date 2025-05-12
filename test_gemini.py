import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
print(f"API key loaded (first 10 chars): {GEMINI_API_KEY[:10]}...")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Create a simple test prompt
def test_api():
    try:
        # Initialize model with gemini-2.0-flash instead of gemini-pro
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Generate a response
        response = model.generate_content("Say 'Hello, the API is working!' if you receive this message.")
        
        # Print response
        print("\nAPI TEST SUCCESSFUL!")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print("\nAPI TEST FAILED!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_api() 