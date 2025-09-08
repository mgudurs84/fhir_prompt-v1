"""
Simple script to load environment variables from .env file
"""

import os
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file"""
    # Load the .env file
    load_dotenv()
    
    # Print loaded variables (optional)
    print("Environment variables loaded:")
    print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")
    print(f"STAGING_BUCKET: {os.getenv('STAGING_BUCKET')}")
    print(f"REASONING_ENGINE_RESOURCE_NAME: {os.getenv('REASONING_ENGINE_RESOURCE_NAME')}")

if __name__ == "__main__":
    load_environment()
