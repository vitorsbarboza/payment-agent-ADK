"""
Test Gemini 3 Flash
"""
import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import Part, Content

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]

print("Testing Gemini 3 Models")
print("="*60)

for model_name in models_to_test:
    print(f"\nTesting {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[Content(role="user", parts=[Part(text="Say 'Hello, I am working!'")])]
        )
        
        response_text = ""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    response_text += part.text
        
        print(f"✅ {model_name} - SUCCESS")
        print(f"   Response: {response_text}")
        
    except Exception as e:
        print(f"❌ {model_name} - FAILED")
        print(f"   Error: {str(e)[:300]}")
