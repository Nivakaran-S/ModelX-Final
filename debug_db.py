import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("="*60)
print("[DEBUG] DATABASE DEBUGGER")
print("="*60)
print(f"Python Executable: {sys.executable}")
print(f"Current Directory: {os.getcwd()}")
print("-" * 60)

# 1. Check Neo4j Import
print("\n[1] Checking Neo4j Import...")
try:
    from neo4j import GraphDatabase
    print("[OK] neo4j imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import neo4j: {e}")

# 2. Check ChromaDB Import
print("\n[2] Checking ChromaDB Import...")
try:
    import chromadb
    print("[OK] chromadb imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import chromadb: {e}")

try:
    from langchain_chroma import Chroma
    print("[OK] langchain_chroma imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import langchain_chroma: {e}")

# 3. Check Neo4j Connection
print("\n[3] Testing Neo4j Connection...")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")

# Try multiple URIs
uris_to_test = [
    "bolt://localhost:7687",
    "neo4j://localhost:7687",
    "bolt://127.0.0.1:7687",
    "neo4j://127.0.0.1:7687"
]

success = False
for uri in uris_to_test:
    print(f"\n   Trying: {uri}")
    print(f"   User: {user}")
    print(f"   Password: {'*' * len(password) if password else 'None'}")
    
    try:
        driver = GraphDatabase.driver(
            uri, 
            auth=(user, password),
            connection_timeout=10,
            max_connection_lifetime=3600
        )
        driver.verify_connectivity()
        print(f"   [OK] Connection Successful with {uri}!")
        driver.close()
        success = True
        print(f"\n   >> Use this in .env: NEO4J_URI={uri}")
        break
    except Exception as e:
        print(f"   [FAIL] {type(e).__name__}: {str(e)[:100]}")

if not success:
    print("\n   [ERROR] All connection attempts failed!")

# 4. Check ChromaDB Connection
print("\n[4] Testing ChromaDB Connection...")
chroma_path = os.getenv("CHROMADB_PATH", "./data/chromadb")
print(f"   Path: {chroma_path}")

try:
    client = chromadb.PersistentClient(path=chroma_path)
    print(f"   Collections: {client.list_collections()}")
    print("[OK] ChromaDB Connection Successful!")
except Exception as e:
    print(f"[FAIL] ChromaDB Connection Failed: {e}")

print("\n" + "="*60)
