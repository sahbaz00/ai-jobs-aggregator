import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def list_my_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    print("[*] Querying Google for your authorized models...\n")
    
    try:
        # Just print everything the server says you can use
        for model in client.models.list():
            print(f"ID: {model.name}")
            # print(f"Capabilities: {model.supported_actions}") # Optional for debugging
            print("-" * 30)
    except Exception as e:
        print(f"[-] Still hitting an error: {e}")

if __name__ == "__main__":
    list_my_models()