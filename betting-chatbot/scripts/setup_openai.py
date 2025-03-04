#!/usr/bin/env python3
"""
Setup script for OpenAI API key.
This script helps you set up your OpenAI API key in the .env files.
"""

import os
import re

def update_env_file(file_path, api_key):
    """Update the OPENAI_API_KEY in the .env file."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} does not exist.")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the API key
    if 'OPENAI_API_KEY=' in content:
        content = re.sub(r'OPENAI_API_KEY=.*', f'OPENAI_API_KEY={api_key}', content)
    else:
        content += f'\nOPENAI_API_KEY={api_key}\n'
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Updated {file_path} with your API key.")
    return True

def main():
    """Main function."""
    print("OpenAI API Key Setup")
    print("====================")
    print("This script will help you set up your OpenAI API key in the .env files.")
    print("You can get your API key from https://platform.openai.com/api-keys")
    print()
    
    api_key = input("Enter your OpenAI API key: ").strip()
    
    if not api_key:
        print("Error: API key cannot be empty.")
        return
    
    # Update the .env files
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    env_files = [
        os.path.join(root_dir, '.env'),
        os.path.join(root_dir, 'web', 'backend', '.env')
    ]
    
    success = True
    for env_file in env_files:
        if not update_env_file(env_file, api_key):
            success = False
    
    if success:
        print("\nSuccess! Your OpenAI API key has been set up in all .env files.")
        print("You can now run the application with ./run_local.sh")
    else:
        print("\nThere were some errors setting up your API key.")
        print("Please check the error messages above and try again.")

if __name__ == "__main__":
    main() 