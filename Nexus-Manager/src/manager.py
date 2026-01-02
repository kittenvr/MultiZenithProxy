from typing import Dict, List, Optional, Any
from config import MultiZenithConfig, InstanceConfig, AccountConfig
from api_client import ZenithHTTPClient, ConnectionStatus
import time
import threading
import random
from datetime import datetime, timedelta
import subprocess
import os
from pathlib import Path
import uuid
import re
from zenith_instance_manager import ZenithInstanceManager


class MultiZenithManager:
    """Main class to manage multiple ZenithProxy instances"""

    def __init__(self, config: MultiZenithConfig):
        self.config = config
        self.instances: Dict[str, ZenithInstanceManager] = {}
        self.running = False
        self.main_thread = None

        # Initialize instance managers
        for instance_config in config.instances:
            if instance_config.enabled:
                instance_path = f"instances/{instance_config.name}"
                # Use API URL from config if available
                api_url = instance_config.api_url if hasattr(instance_config, 'api_url') else None
                api_token = instance_config.api_token if hasattr(instance_config, 'api_token') else None

                self.instances[instance_config.name] = ZenithInstanceManager(
                    instance_config.name,
                    instance_path,
                    instance_config.server_address,
                    instance_config.server_port,
                    api_url,
                    api_token
                )

    def start(self):
        """Start the multi-zenith manager"""
        self.running = True
        self.main_thread = threading.Thread(target=self._main_loop)
        self.main_thread.start()
        print("MultiZenith Manager started")

    def stop(self):
        """Stop the multi-zenith manager"""
        self.running = False
        if self.main_thread:
            self.main_thread.join()
        print("MultiZenith Manager stopped")

    def _main_loop(self):
        """Main management loop"""
        while self.running:
            # Update statuses for all instances and handle username-based renaming
            instances_to_rename = {}
            for name, instance in list(self.instances.items()):  # Use list() to avoid modification during iteration
                try:
                    status = instance.get_status()
                    # Check if this instance has been authenticated and needs renaming
                    if instance.username and name.startswith("unauth_"):
                        new_name = instance.username
                        # Ensure new name is unique
                        counter = 1
                        original_new_name = new_name
                        while new_name in self.instances:
                            new_name = f"{original_new_name}_{counter}"
                            counter += 1

                        # Rename the instance
                        instances_to_rename[name] = new_name
                        print(f"Renaming instance from '{name}' to '{new_name}' based on logged-in username")

                    # Update queue info periodically
                    if hasattr(instance, 'last_queue_check'):
                        if time.time() - getattr(instance, 'last_queue_check', 0) > 60:  # Update every minute
                            instance.update_queue_info()

                except Exception as e:
                    print(f"Error getting status for instance {name}: {str(e)}")

            # Perform renames after checking all instances
            for old_name, new_name in instances_to_rename.items():
                if old_name in self.instances:
                    self.instances[new_name] = self.instances.pop(old_name)
                    # Update the instance's internal name as well
                    self.instances[new_name].name = new_name

            if self.config.rotation_enabled:
                self._rotation_cycle()

            # Check queue times and coordinate account joining
            if self.config.queue_check_enabled:
                self._queue_time_coordination()

            time.sleep(self.config.check_interval)

    def _rotation_cycle(self):
        """Perform a rotation cycle to maintain 24/7 presence"""
        # Check if any instances need rotation
        for name, instance in self.instances.items():
            status = instance.get_status()
            if status.connected:
                session_duration = instance.get_session_duration()

                # Check if we should rotate based on time limits
                if session_duration >= (instance.estimated_session_length - 300):  # 5 min buffer
                    print(f"Instance {name} has been connected for {session_duration:.0f}s, considering rotation...")
                    # For process-based approach, rotation means starting a new instance if available
                    self._consider_rotation(instance)

    def _queue_time_coordination(self):
        """Coordinate account joining based on queue times by monitoring external queue sources"""
        # This function will monitor queue times for the target server
        # In a real implementation, this might query the server status API or other sources
        # For now, we'll simulate queue monitoring

        # Get the target server from the first instance to monitor queue for
        if not self.instances:
            return

        # For demonstration purposes, let's assume we're monitoring queue time for the first server
        first_instance = next(iter(self.instances.values()))
        server_address = first_instance.server_address

        # In a real implementation, this would call a function that:
        # 1. Queries the server's queue information (if available via API)
        # 2. Or scrapes a queue monitoring service
        # 3. Or makes other checks to determine queue status
        estimated_queue_time = self._check_queue_time(server_address)

        # If queue time is low, we might want to start preparing additional instances
        if estimated_queue_time and estimated_queue_time <= self.config.queue_prediction_threshold:
            print(f"Queue time is low ({estimated_queue_time}s), preparing additional accounts...")
            # For now, just a placeholder for when queue time is favorable
            self._prepare_accounts_for_queue(estimated_queue_time)

    def _check_queue_time(self, server_address: str) -> Optional[int]:
        """Check queue time for the given server - this connects to queue monitoring services"""
        # For servers like 2b2t.org, there might be public APIs or websites that expose queue information
        # This is a simplified example - a real implementation would connect to the specific server's
        # queue monitoring system or website

        import requests
        try:
            # Example: some servers have queue info APIs (this is just an example structure)
            # For 2b2t specifically, they have public queue monitoring on their website
            # This is a placeholder for actual implementation
            if "2b2t" in server_address.lower():
                # Example of how to check 2b2t queue time (actual API implementation would vary)
                # This is just a simulation
                return None  # Return None since there's no standard public API
            else:
                # For other servers, there might be different ways to check queue time
                return None
        except Exception:
            return None

    def _prepare_accounts_for_queue(self, queue_time: int):
        """Prepare accounts when queue time is favorable"""
        # When queue time is low, we might want to start more instances
        # to maintain presence after the current one finishes
        # Start a new account for the same server
        first_instance = next(iter(self.instances.values()), None)
        if first_instance:
            new_instance_name = self.start_new_account(
                first_instance.server_address,
                first_instance.server_port
            )
            if new_instance_name:
                print(f"Started new account instance '{new_instance_name}' for queue preparation")

    def _prepare_next_account(self, current_instance: ZenithInstanceManager):
        """Prepare the next account to join when the current one is about to finish - not applicable in process-based approach"""
        # For process-based approach, this would involve starting a new instance
        pass

    def get_account_status(self) -> Dict[str, Any]:
        """Get detailed status of all accounts across all instances"""
        status = {}
        for instance_name, instance in self.instances.items():
            instance_status = instance.get_status()
            accounts_info = []

            if instance_status.account_name:
                accounts_info.append({
                    'name': instance_status.account_name,
                    'connection_duration': instance.get_connection_duration(),
                    'session_duration': instance.get_session_duration()
                })

            status[instance_name] = {
                'connected': instance_status.connected,
                'server_status': instance_status.server_status,
                'auth_code': getattr(instance, 'auth_code', None),
                'running': instance.is_running(),
                'accounts': accounts_info
            }

        return status
    
    def _consider_rotation(self, current_instance: ZenithInstanceManager):
        """Consider if rotation is needed and perform it if necessary"""
        # Check if rotation is enabled
        if not self.config.rotation_enabled:
            return

        session_duration = current_instance.get_session_duration()

        # Check if we should rotate based on session duration and buffer time
        if session_duration >= (current_instance.estimated_session_length - 300):  # 5 min buffer
            print(f"Instance {current_instance.name} approaching session limit, initiating rotation...")

            # For process-based approach, we need to start new instances rather than connect/disconnect
            # This means we start a new instance in a new directory
            new_instance_name = f"{current_instance.name}_rotation"
            new_instance_path = f"instances/{new_instance_name}"

            # Start a new instance with same server settings
            new_instance = ZenithInstanceManager(
                new_instance_name,
                new_instance_path,
                current_instance.server_address,
                current_instance.server_port
            )

            # Start the new instance with device code auth
            if new_instance.start_instance("device_code"):
                print(f"Started new instance {new_instance_name} for rotation")
                self.instances[new_instance_name] = new_instance

                # Eventually stop the old instance after some time
                def stop_old_instance():
                    time.sleep(30)  # Wait 30 seconds before stopping old instance
                    current_instance.stop_instance()
                    print(f"Stopped old instance {current_instance.name}")

                stop_thread = threading.Thread(target=stop_old_instance, daemon=True)
                stop_thread.start()

    def _select_next_instance(self, available_instances: List[ZenithInstanceManager], 
                             current_instance: ZenithInstanceManager) -> Optional[ZenithInstanceManager]:
        """Select the next instance based on rotation strategy - for process-based approach"""
        if not available_instances:
            return None

        strategy = self.config.default_rotation_strategy

        if strategy == "random":
            return random.choice(available_instances)
        elif strategy == "round_robin":
            # For simplicity, just return first available
            return available_instances[0]
        else:  # sequential/default
            # Return the first one in the list
            return available_instances[0]

    def start_new_account(self, server_address: str, server_port: int = 25565):
        """Start a new account instance with device code authentication"""
        # Create a unique temporary name - will be renamed when username is known
        temp_name = f"unauth_{int(time.time())}"
        instance_path = f"instances/{temp_name}"

        # Create the new instance with available API configuration
        new_instance = ZenithInstanceManager(
            temp_name,
            instance_path,
            server_address,
            server_port
        )

        # Start the new instance with device code authentication
        success = new_instance.start_instance("device_code")

        if success:
            # Add to our instances
            self.instances[temp_name] = new_instance
            print(f"Started new account instance '{temp_name}' with device code auth")
            print(f"Auth code: {new_instance.auth_code if new_instance.auth_code else 'not available yet'}")
            return temp_name
        else:
            print(f"Failed to start new account instance")
            return None

    def stop_all_instances(self):
        """Stop all running instances"""
        for name, instance in self.instances.items():
            if instance.is_running():
                instance.stop_instance()
                print(f"Stopped instance {name}")

    def get_status_report(self) -> Dict[str, Any]:
        """Get a comprehensive status report of all instances"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'instances': {}
        }

        for name, instance in self.instances.items():
            status = instance.get_status()
            report['instances'][name] = {
                'connected': status.connected,
                'account': status.account_name,
                'server_status': status.server_status,
                'auth_code': getattr(instance, 'auth_code', None),
                'running': instance.is_running() if hasattr(instance, 'is_running') else instance.process and instance.process.poll() is None
            }

        return report

    def add_instance(self, instance_config: InstanceConfig):
        """Add a new Zenith instance to management - not needed in process-based approach"""
        # In process-based approach, new instances are started with start_new_account
        pass

    def remove_instance(self, instance_name: str):
        """Remove an instance from management"""
        if instance_name in self.instances:
            if self.instances[instance_name].is_running():
                self.instances[instance_name].stop_instance()
            del self.instances[instance_name]

    def get_connected_accounts(self) -> Dict[str, List[str]]:
        """Get all connected accounts across all instances"""
        connected_accounts = {}
        for name, instance in self.instances.items():
            status = instance.get_status()
            if status.account_name:
                connected_accounts[name] = [status.account_name]
            else:
                connected_accounts[name] = []
        return connected_accounts

    def add_account_to_instance(self, instance_name: str, account_config: AccountConfig) -> bool:
        """Add an account to a specific instance - not applicable for process-based approach"""
        # In process-based approach, accounts are added by starting new instances
        return False

    def remove_account_from_instance(self, instance_name: str, account_name: str) -> bool:
        """Remove an account from a specific instance - not applicable for process-based approach"""
        return False

    def connect_specific_account(self, instance_name: str, account_name: str) -> bool:
        """Connect a specific account to a specific instance"""
        # In process-based approach, this means starting a new instance
        if instance_name in self.instances:
            instance = self.instances[instance_name]
            # Account is connected when the instance is started
            return instance.is_running()
        return False

    def disconnect_specific_account(self, instance_name: str, account_name: str = None) -> bool:
        """Disconnect a specific account from a specific instance"""
        if instance_name in self.instances:
            instance = self.instances[instance_name]
            return instance.stop_instance()
        return False