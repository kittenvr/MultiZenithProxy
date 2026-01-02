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


class ZenithInstanceManager:
    """Manages a single ZenithProxy instance process and API"""
    
    def __init__(self, name: str, instance_path: str, server_address: str, server_port: int = 25565, 
                 api_url: str = None, api_token: str = None):
        self.name = name
        self.instance_path = Path(instance_path)
        self.server_address = server_address
        self.server_port = server_port
        self.api_url = api_url  # Will be set after process starts and API port is known
        self.api_token = api_token
        self.process = None
        self.client = None  # Will be initialized after API URL is known
        self.status = ConnectionStatus(connected=False)
        self.last_status_check = 0
        self.connection_start_time = None
        self.session_start_time = None
        self.queue_info = {}
        self.estimated_session_length = 3600  # Default to 1 hour if unknown
        self.auth_code = None
        self.username = None  # Will be set after authentication
    
    def start_instance(self, auth_type: str = "device_code", http_api_port: int = None) -> bool:
        """Start a new ZenithProxy instance with device code authentication and HTTP API"""
        try:
            # Create instance directory if it doesn't exist
            self.instance_path.mkdir(parents=True, exist_ok=True)
            
            # Change to the instance directory
            original_cwd = os.getcwd()
            os.chdir(self.instance_path)
            
            # Determine API port - default to a port based on instance name if not provided
            if http_api_port is None:
                # Generate a port based on the hash of the instance name
                port_base = 8000
                port_offset = abs(hash(self.name)) % 1000
                http_api_port = port_base + port_offset
            
            # Set API URL
            self.api_url = f"http://localhost:{http_api_port}"
            self.client = ZenithHTTPClient(self.api_url, self.api_token)
            
            # Start ZenithProxy with device code auth and HTTP API enabled
            cmd = [
                "java", "-jar", "ZenithProxy.jar",  # Assuming ZenithProxy is distributed as a JAR
                "--server", f"{self.server_address}:{self.server_port}",
                "--auth", auth_type,
                "--http-api-port", str(http_api_port)
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor output to capture auth code, username, etc.
            self._monitor_process_output()
            
            os.chdir(original_cwd)
            return True
        except Exception as e:
            print(f"Failed to start Zenith instance: {str(e)}")
            return False
    
    def _monitor_process_output(self):
        """Monitor process output to capture auth codes and connection info"""
        def monitor():
            if self.process:
                for line in iter(self.process.stdout.readline, ''):
                    line = line.strip()
                    if line:  # Only print non-empty lines
                        print(f"[{self.name}] {line}")
                    
                    # Capture device auth code - try multiple approaches
                    # Approach 1: Look for lines mentioning code/device/auth
                    if "code" in line.lower() and ("device" in line.lower() or "auth" in line.lower() or "microsoft" in line.lower()):
                        # Parse auth code from output - common formats:
                        # - XXXX-XXXX format (e.g., AB12-EF34)
                        # - Single string of alphanumeric chars
                        # - With or without hyphens
                        # Look for various possible patterns
                        patterns = [
                            r'([A-Z0-9]{4}-[A-Z0-9]{4})',                    # AB12-EF34 format
                            r'([A-Z0-9]{3,8}-[A-Z0-9]{3,8})',               # More flexible hyphen format
                            r'\b([A-Z0-9]{8}|[A-Z0-9]{7}|[A-Z0-9]{6}|[A-Z0-9]{5}|[A-Z0-9]{4})\b',  # Standalone codes
                            r'(?:code[:\s]*|is[:\s]*)([A-Z0-9-]{4,15})\b',   # With "code:" prefix
                        ]

                        for pattern in patterns:
                            auth_match = re.search(pattern, line, re.IGNORECASE)
                            if auth_match:
                                auth_code = auth_match.group(1)
                                # Validate it looks like a real auth code (not just random text)
                                if len(auth_code) >= 4 and (auth_code.replace('-', '').isalnum()):
                                    self.auth_code = auth_code
                                    print(f"Device auth code for {self.name}: {self.auth_code}")
                                    break  # Found a valid code, stop checking patterns

                    # Approach 2: If no keyword match, look for likely auth codes in any line
                    if not self.auth_code:  # Only if we haven't found one yet
                        # Look for common auth code patterns in any line
                        patterns = [
                            r'([A-Z0-9]{4}-[A-Z0-9]{4})\b',                  # AB12-EF34 format
                            r'([A-Z0-9]{3,8}-[A-Z0-9]{3,8})\b',             # More flexible hyphen format
                            r'\b([A-Z0-9]{8}|[A-Z0-9]{7}|[A-Z0-9]{6}|[A-Z0-9]{5}|[A-Z0-9]{4})\b',  # Standalone codes
                        ]

                        for pattern in patterns:
                            auth_match = re.search(pattern, line, re.IGNORECASE)
                            if auth_match:
                                auth_code = auth_match.group(1)
                                # Validate it looks like a real auth code (not just random text)
                                if len(auth_code) >= 4 and (auth_code.replace('-', '').isalnum()):
                                    # Additional check: make sure it's reasonably isolated
                                    # (not just part of a longer string like a UUID)
                                    # For this simple approach, accept it
                                    prev_auth_code = getattr(self, 'auth_code', None)
                                    if not prev_auth_code or len(auth_code) > len(prev_auth_code):  # Prefer longer codes if multiple found
                                        self.auth_code = auth_code
                                        print(f"Device auth code for {self.name}: {self.auth_code}")
                                        break  # Found a valid code, stop checking patterns
                    
                    # Capture username after successful auth
                    if any(keyword in line.lower() for keyword in ["logged in", "login", "success", "authenticated", "username", "displayname"]):
                        # Look for username pattern - could be in various formats
                        username_patterns = [
                            r'(?:as|to|user|name|username|displayname)\s+["\']?([a-zA-Z0-9_]{2,16})["\']?',  # Standard format
                            r'([a-zA-Z0-9_]{2,16})\s+(?:logged in|has logged|is now logged)',              # Username before "logged in"
                            r'logged in as\s+["\']?([a-zA-Z0-9_]{2,16})["\']?',                          # After "logged in as"
                            r'authenticat(?:ed|ion successful).*?([a-zA-Z0-9_]{2,16})',                   # After auth success
                        ]

                        for pattern in username_patterns:
                            username_match = re.search(pattern, line, re.IGNORECASE)
                            if username_match:
                                username = username_match.group(1)
                                # Validate it looks like a Minecraft username
                                if 2 <= len(username) <= 16 and re.match(r'^[a-zA-Z0-9_]+$', username):
                                    self.username = username
                                    # Update instance name to username after login
                                    print(f"Instance {self.name} logged in as: {self.username}")
                                    break  # Found username, stop checking patterns
                
                # Process has ended
                if self.client:
                    # Even if process ended, we maintain connection status based on API knowledge
                    try:
                        api_status = self.client.get_status()
                        self.status = api_status
                    except:
                        self.status = ConnectionStatus(connected=False, server_status='stopped')
        
        # Start monitoring in a thread
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    def update_queue_info(self):
        """Update queue information for this instance via HTTP API"""
        try:
            if self.client:
                self.queue_info = self.client.get_queue_info()
                return self.queue_info
            else:
                return {}
        except Exception as e:
            print(f"Failed to get queue info for {self.name}: {str(e)}")
            return {}

    def get_session_duration(self) -> float:
        """Get how long the current session has been active (in seconds)"""
        if self.session_start_time:
            return time.time() - self.session_start_time
        return 0

    def get_connection_duration(self) -> float:
        """Get how long the current connection has been active (in seconds)"""
        if self.connection_start_time:
            return time.time() - self.connection_start_time
        return 0

    def update_status(self) -> ConnectionStatus:
        """Update the status of this instance via HTTP API"""
        if self.client:
            try:
                self.status = self.client.get_status()
                self.last_status_check = time.time()
                
                # Update session start time when connection establishes
                if self.status.connected and self.session_start_time is None:
                    self.session_start_time = time.time()
                elif not self.status.connected:
                    self.session_start_time = None
                    
                # Update connection start time for duration tracking
                if self.status.connected and self.connection_start_time is None:
                    self.connection_start_time = time.time()
                elif not self.status.connected:
                    self.connection_start_time = None
                return self.status
            except Exception as e:
                # If API is not available, fall back to process status
                if self.is_running():
                    return ConnectionStatus(connected=True, server_status='running')
                else:
                    return ConnectionStatus(connected=False, server_status='stopped')
        else:
            # If no client, return based on process status
            connected = self.is_running()
            return ConnectionStatus(connected=connected, server_status='running' if connected else 'stopped')

    def get_status(self):
        """Get the current status - returns ConnectionStatus object"""
        return self.update_status()

    def stop_instance(self) -> bool:
        """Stop this ZenithProxy instance"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                # Update status
                if self.client:
                    try:
                        api_status = self.client.get_status()
                        self.status = ConnectionStatus(connected=False, server_status='stopped')
                    except:
                        self.status = ConnectionStatus(connected=False, server_status='stopped')
                return True
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.status = ConnectionStatus(connected=False, server_status='stopped')
                return True
            except Exception as e:
                print(f"Error stopping instance {self.name}: {str(e)}")
                return False
        return True

    def is_running(self) -> bool:
        """Check if this instance process is running"""
        if self.process:
            return self.process.poll() is None
        return False

    def connect_account(self, account_name: str) -> bool:
        """Connect a specific account through this Zenith instance via HTTP API"""
        if self.client:
            try:
                success = self.client.connect_account(account_name)
                if success:
                    self.connection_start_time = time.time()
                return success
            except Exception as e:
                print(f"Failed to connect account {account_name}: {str(e)}")
                return False
        return False

    def disconnect_account(self, account_name: str = None) -> bool:
        """Disconnect current account from this Zenith instance via HTTP API"""
        if self.client:
            try:
                success = self.client.disconnect_account(account_name)
                if success:
                    self.connection_start_time = None
                return success
            except Exception as e:
                print(f"Failed to disconnect account: {str(e)}")
                return False
        return False