import openai

# Add API key directly
OPENAI_API_KEY = "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"
print(f"API key loaded (first 10 chars): {OPENAI_API_KEY[:10]}...")

# Configure OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Create a simple test prompt
def test_api():
    try:
        # Generate a response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'Hello, the API is working!' if you receive this message."}
            ]
        )
        
        # Print response
        print("\nAPI TEST SUCCESSFUL!")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print("\nAPI TEST FAILED!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_api() 