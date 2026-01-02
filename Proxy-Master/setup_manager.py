

import os
import json
import shutil
import sys
from pathlib import Path

def main():
    print("Multi-ZenithProxy Manager Setup")
    print("=" * 50)
    
    if not os.path.exists("multi_zenith_manager.py"):
        print("Error: Please run this script from the Multi-ZenithProxy directory")
        sys.exit(1)
    
    print("\nStep 1: Creating directories...")
    os.makedirs("instances", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("\nStep 2: Setting up template directory...")
    if not os.path.exists("template"):
        print("No template directory found. You'll need to create one.")
        print("Copy your ZenithProxy files to a 'template' directory:")
        print("  mkdir template")
        print("  cp -r /path/to/zenithproxy/* template/")
    else:
        print("Template directory found.")
    
    print("\nStep 3: Creating example configurations...")
    
    example_configs = [
        {
            "filename": "account1_config.json",
            "config": {
                "account": "account1@example.com",
                "server": "2b2t.org",
                "proxy": "socks5://proxy1.example.com:1080",
                "release_channel": "java.1.21.4",
                "auto_update": True,
                "account_type": "deviceCode"
            }
        },
        {
            "filename": "account2_config.json", 
            "config": {
                "account": "account2@example.com",
                "server": "2b2t.org",
                "proxy": "socks5://proxy2.example.com:1080",
                "release_channel": "java.1.21.4",
                "auto_update": True,
                "account_type": "deviceCode"
            }
        }
    ]
    
    for example in example_configs:
        with open(example["filename"], "w") as f:
            json.dump(example["config"], f, indent=2)
        print(f"Created {example['filename']}")
    
    print("\nStep 4: Setting up main configuration...")
    if not os.path.exists("multi_zenith_config.json"):
        default_config = {
            "rotation_enabled": False,
            "rotation_strategy": "sequential",
            "rotation_interval": 300,
            "instances": {}
        }
        
        with open("multi_zenith_config.json", "w") as f:
            json.dump(default_config, f, indent=2)
        print("Created default multi_zenith_config.json")
    else:
        print("Main configuration already exists.")
    
    print("\nStep 5: Installing Python requirements...")
    if os.path.exists("requirements.txt"):
        print("Installing requirements...")
        os.system("pip install -r requirements.txt")
    else:
        print("No requirements.txt found. Installing requests...")
        os.system("pip install requests")
    
    print("\n" + "=" * 50)
    print("Setup complete!")
    print("\nTo start the manager:")
    print("  python multi_zenith_manager.py")
    print("\nTo add your first instances:")
    print("  1. Edit account1_config.json and account2_config.json with your account details")
    print("  2. In the manager, use:")
    print("     add account1 account1_config.json")
    print("     add account2 account2_config.json")
    print("  3. Enable rotation:")
    print("     rotation on sequential 300")
    print("  4. Start all instances:")
    print("     startall")

if __name__ == "__main__":
    main()
