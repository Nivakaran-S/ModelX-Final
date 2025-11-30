import os
import sys
import json

# Ensure we can find the 'src' module from the root
sys.path.append(os.getcwd())

try:
    from src.utils.utils import (
        scrape_facebook,
        scrape_twitter,
        scrape_local_news,
        tool_weather_nowcast
    )
    print("✅ Libraries loaded successfully.\n")
except ImportError as e:
    print(f"❌ Error loading libraries: {e}")
    print("Make sure you are running this from the 'ModelX-Final' folder.")
    sys.exit(1)

def run_test(name, func, **kwargs):
    print(f"--- Testing {name} ---")
    try:
        # Check if it's a LangChain tool (needs .invoke)
        if hasattr(func, "invoke"):
            res = func.invoke(kwargs)
        else:
            res = func(**kwargs)
            
        # Try to print pretty JSON
        try:
            parsed = json.loads(res)
            print(json.dumps(parsed, indent=2))
        except:
            print(res)
            
    except Exception as e:
        print(f"❌ Error: {e}")
    print("\n")

if __name__ == "__main__":
    # --- UNCOMMENT THE TOOL YOU WANT TO TEST ---

    # 1. Test Weather (Fastest check)
    run_test("Weather", tool_weather_nowcast, location="Colombo")

    # 2. Test Facebook (Requires Session)
    # run_test("Facebook", scrape_facebook, keywords=["Sri Lanka"])

    # 3. Test Twitter (Requires Session)
    # run_test("Twitter", scrape_twitter, query="Sri Lanka")