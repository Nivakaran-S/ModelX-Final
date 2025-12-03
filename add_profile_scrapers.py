# add_profile_scrapers.py - Simple append script
with open('src/utils/utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import at the end, before ALL_TOOLS
insertion = """
# Profile scrapers for competitive intelligence
try:
    from src.utils.profile_scrapers import scrape_twitter_profile, scrape_facebook_profile, scrape_instagram_profile, scrape_linkedin_profile, scrape_product_reviews
    TOOL_MAPPING["scrape_twitter_profile"] = scrape_twitter_profile
    TOOL_MAPPING["scrape_facebook_profile"] = scrape_facebook_profile
    TOOL_MAPPING["scrape_instagram_profile"] = scrape_instagram_profile
    TOOL_MAPPING["scrape_linkedin_profile"] = scrape_linkedin_profile
    TOOL_MAPPING["scrape_product_reviews"] = scrape_product_reviews
except: pass
"""

# Insert before ALL_TOOLS
content = content.replace('\nALL_TOOLS = list', insertion + '\nALL_TOOLS = list')

with open('src/utils/utils.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
