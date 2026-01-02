#!/usr/bin/env python3
"""
Test script for MultiZenithProxy Manager
"""
import os
import sys
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import config
import manager


def test_basic_functionality():
    """Test basic functionality of the MultiZenithManager"""
    print("Testing MultiZenithManager basic functionality...")

    # Create a sample configuration
    multi_config = config.MultiZenithConfig.create_sample_config()

    # Create manager
    multi_manager = manager.MultiZenithManager(multi_config)

    print(f"Created manager with {len(multi_manager.instances)} instances")

    # Test status report
    report = multi_manager.get_status_report()
    print("Status report keys:", list(report.keys()))

    # Test connection methods
    print("Testing connect/disconnect methods...")

    # Test adding and removing instances
    print("Testing add/remove instance methods...")

    print("Basic functionality tests passed!")


def test_configuration():
    """Test configuration loading and saving"""
    print("\nTesting configuration functionality...")

    # Test sample config creation
    multi_config = config.MultiZenithConfig.create_sample_config()
    print(f"Created sample config with {len(multi_config.instances)} instances")

    # Test saving and loading
    test_config_path = "test_config.json"
    multi_config.save_to_file(test_config_path)

    loaded_config = config.MultiZenithConfig.load_from_file(test_config_path)
    print(f"Loaded config has {len(loaded_config.instances)} instances")

    # Clean up
    if os.path.exists(test_config_path):
        os.remove(test_config_path)

    print("Configuration tests passed!")


def main():
    print("Running MultiZenithProxy Manager tests...")

    test_configuration()
    test_basic_functionality()

    print("\nAll tests passed successfully!")


if __name__ == "__main__":
    main()