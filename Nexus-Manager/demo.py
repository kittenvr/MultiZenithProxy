#!/usr/bin/env python3
"""
Demo script for MultiZenithProxy Manager
This script demonstrates the core functionality of the MultiZenithProxy manager
"""
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import MultiZenithConfig
from manager import MultiZenithManager


def demo_basic_usage():
    """Demonstrate basic usage of the MultiZenithManager"""
    print("=== MultiZenithProxy Manager Demo ===\n")
    
    print("1. Creating sample configuration...")
    config = MultiZenithConfig.create_sample_config()
    print(f"   Created config with {len(config.instances)} instances")
    
    print("\n2. Creating MultiZenithManager...")
    manager = MultiZenithManager(config)
    print(f"   Manager created with {len(manager.instances)} instances")
    
    print("\n3. Getting status report...")
    report = manager.get_status_report()
    print(f"   Status report generated at: {report['timestamp']}")
    for instance_name, status in report['instances'].items():
        print(f"   - {instance_name}: Connected={status['connected']}")
    
    print("\n4. Demonstrating instance management...")
    print("   Current instances:")
    for name in manager.instances.keys():
        print(f"   - {name}")
    
    print("\n5. Showing configuration...")
    print(f"   Rotation enabled: {manager.config.rotation_enabled}")
    print(f"   Check interval: {manager.config.check_interval}s")
    print(f"   Queue check enabled: {manager.config.queue_check_enabled}")
    
    print("\n=== Demo Complete ===")
    print("The actual manager can be started with:")
    print("  python -m src.main start")
    print("\nCommands available:")
    print("  python -m src.main status")
    print("  python -m src.main connect --all")
    print("  python -m src.main disconnect --all")
    print("  python -m src.main list-instances")
    print("  python -m src.main generate-config")


if __name__ == "__main__":
    demo_basic_usage()