import argparse
import sys
import json
from pathlib import Path
from typing import List
from datetime import datetime

# Handle both relative and absolute imports for different execution contexts
try:
    # Try relative imports first (for when used as package)
    from .config import MultiZenithConfig, initialize_config
    from .manager import MultiZenithManager
except ImportError:
    # Fall back to absolute imports (for when run as script)
    from config import MultiZenithConfig, initialize_config
    from manager import MultiZenithManager


def create_parser():
    """Create the argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        description="MultiZenithProxy Manager - Manage multiple ZenithProxy instances for 24/7 server presence"
    )
    
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the MultiZenith manager")
    start_parser.add_argument("--no-rotation", action="store_true", help="Disable automatic rotation")
    
    # Status command
    subparsers.add_parser("status", help="Show status of all instances")
    
    # Add instance command
    add_instance_parser = subparsers.add_parser("add-instance", help="Add a new Zenith instance")
    add_instance_parser.add_argument("--name", required=True, help="Name of the instance")
    add_instance_parser.add_argument("--api-url", required=True, help="API URL of the Zenith instance")
    add_instance_parser.add_argument("--server", default="", help="Target server address")
    add_instance_parser.add_argument("--server-port", type=int, default=25565, help="Target server port")

    # List instances command
    subparsers.add_parser("list-instances", help="List all configured instances")

    # Add account command - starts a new instance with device code auth
    add_account_parser = subparsers.add_parser("add-account", help="Add a new account by starting a new ZenithProxy instance with device code auth")
    add_account_parser.add_argument("--server", required=True, help="Server address to connect to (e.g., 2b2t.org)")
    add_account_parser.add_argument("--port", type=int, default=25565, help="Server port to connect to")

    # Remove account command
    remove_account_parser = subparsers.add_parser("remove-account", help="Remove an account from a Zenith instance")
    remove_account_parser.add_argument("--instance", required=True, help="Name of the instance to remove account from")
    remove_account_parser.add_argument("--account-name", required=True, help="Name of the account to remove")

    # Connect all command
    connect_parser = subparsers.add_parser("connect", help="Connect all instances")
    connect_parser.add_argument("--all", action="store_true", help="Connect all configured instances")

    # Disconnect all command
    disconnect_parser = subparsers.add_parser("disconnect", help="Disconnect instances")
    disconnect_parser.add_argument("--all", action="store_true", help="Disconnect all instances")

    # Connect specific account command
    connect_account_parser = subparsers.add_parser("connect-account", help="Connect a specific account")
    connect_account_parser.add_argument("--instance", required=True, help="Name of the instance")
    connect_account_parser.add_argument("--account-name", required=True, help="Name of the account to connect")

    # Disconnect specific account command
    disconnect_account_parser = subparsers.add_parser("disconnect-account", help="Disconnect a specific account")
    disconnect_account_parser.add_argument("--instance", required=True, help="Name of the instance")
    disconnect_account_parser.add_argument("--account-name", help="Name of the account to disconnect")

    # Enable/disable rotation command
    rotation_parser = subparsers.add_parser("rotation", help="Manage rotation settings")
    rotation_parser.add_argument("--enable", action="store_true", help="Enable rotation")
    rotation_parser.add_argument("--disable", action="store_true", help="Disable rotation")
    
    # Generate sample config command
    subparsers.add_parser("generate-config", help="Generate a sample configuration file")
    
    return parser


def handle_generate_config(args):
    """Handle the generate-config command"""
    config = MultiZenithConfig.create_sample_config()
    config_path = Path(args.config)
    config.save_to_file(config_path)
    print(f"Sample configuration generated at {config_path}")
    

def handle_list_instances(args, manager: MultiZenithManager):
    """Handle the list-instances command"""
    print("Configured Zenith Instances:")
    for name, instance in manager.instances.items():
        status = instance.update_status()
        print(f"  - {name}: API={instance.config.api_url}, Connected={status.connected}, Server={instance.config.server_address}")


def handle_status(args, manager: MultiZenithManager):
    """Handle the status command"""
    # Use the new detailed account status method
    status_report = manager.get_account_status()
    print(f"Account Status Report - {datetime.now().isoformat()}")
    print("-" * 60)

    for instance_name, instance_status in status_report.items():
        print(f"Instance: {instance_name}")
        print(f"  Connected: {instance_status['connected']}")
        print(f"  Server Status: {instance_status.get('server_status', 'N/A')}")
        print(f"  Running: {instance_status.get('running', 'N/A')}")
        print(f"  Auth Code: {instance_status.get('auth_code', 'N/A')}")

        print("  Accounts:")
        if instance_status['accounts']:
            for account in instance_status['accounts']:
                print(f"    - {account['name']}")
                print(f"      Connection Duration: {account['connection_duration']:.0f}s")
                print(f"      Session Duration: {account['session_duration']:.0f}s")
        else:
            print("    No accounts connected")
        print()


def handle_start(args, manager: MultiZenithManager):
    """Handle the start command"""
    if args.no_rotation:
        manager.config.rotation_enabled = False
        print("Automatic rotation disabled")
    
    print("Starting MultiZenith Manager...")
    manager.start()
    
    try:
        # Keep the main thread alive
        while manager.running:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down MultiZenith Manager...")
        manager.stop()


def handle_connect(args, manager: MultiZenithManager):
    """Handle the connect command"""
    if args.all:
        print("Connecting all instances...")
        manager.connect_all_instances()
    else:
        # Connect specific instances if specified, or just show help
        print("Use --all to connect all instances, or specify individual instances")


def handle_disconnect(args, manager: MultiZenithManager):
    """Handle the disconnect command"""
    if args.all:
        print("Disconnecting all instances...")
        manager.disconnect_all_instances()
    else:
        # Disconnect specific instances if specified, or just show help
        print("Use --all to disconnect all instances, or specify individual instances")


def handle_add_account(args, manager: MultiZenithManager):
    """Handle the add-account command - starts a new instance with device code auth"""
    instance_name = manager.start_new_account(args.server, args.port)
    if instance_name:
        print(f"Started new account instance '{instance_name}'")
        print("Look for the device authentication code in the console output above.")
        print("Visit https://login.microsoft.com/ and enter the code when prompted.")
    else:
        print("Failed to start a new account instance")


def handle_remove_account(args, manager: MultiZenithManager):
    """Handle the remove-account command"""
    success = manager.remove_account_from_instance(args.instance, args.account_name)
    if success:
        print(f"Successfully removed account '{args.account_name}' from instance '{args.instance}'")
    else:
        print(f"Failed to remove account '{args.account_name}' from instance '{args.instance}'")


def handle_connect_account(args, manager: MultiZenithManager):
    """Handle the connect-account command"""
    success = manager.connect_specific_account(args.instance, args.account_name)
    if success:
        print(f"Successfully connected account '{args.account_name}' on instance '{args.instance}'")
    else:
        print(f"Failed to connect account '{args.account_name}' on instance '{args.instance}'")


def handle_disconnect_account(args, manager: MultiZenithManager):
    """Handle the disconnect-account command"""
    success = manager.disconnect_specific_account(args.instance, args.account_name)
    if success:
        print(f"Successfully disconnected account '{args.account_name}' from instance '{args.instance}'")
    else:
        print(f"Failed to disconnect account '{args.account_name}' from instance '{args.instance}'")


def handle_rotation(args, manager: MultiZenithManager):
    """Handle the rotation command"""
    if args.enable:
        manager.config.rotation_enabled = True
        print("Rotation enabled")
    elif args.disable:
        manager.config.rotation_enabled = False
        print("Rotation disabled")
    else:
        status = "enabled" if manager.config.rotation_enabled else "disabled"
        print(f"Rotation is currently {status}")


def main():
    """Main entry point for the CLI"""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "generate-config":
        handle_generate_config(args)
        return

    # Initialize configuration
    try:
        config = initialize_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        sys.exit(1)

    # Create manager instance
    manager = MultiZenithManager(config)

    # Handle commands
    if args.command == "list-instances":
        handle_list_instances(args, manager)
    elif args.command == "status":
        handle_status(args, manager)
    elif args.command == "start":
        handle_start(args, manager)
    elif args.command == "connect":
        handle_connect(args, manager)
    elif args.command == "disconnect":
        handle_disconnect(args, manager)
    elif args.command == "add-account":
        handle_add_account(args, manager)
    elif args.command == "remove-account":
        handle_remove_account(args, manager)
    elif args.command == "connect-account":
        handle_connect_account(args, manager)
    elif args.command == "disconnect-account":
        handle_disconnect_account(args, manager)
    elif args.command == "rotation":
        handle_rotation(args, manager)
    elif args.command is None:
        parser.print_help()
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()