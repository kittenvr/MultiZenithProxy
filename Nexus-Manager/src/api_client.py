import requests
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json


class ZenithAPIError(Exception):
    """Custom exception for Zenith API errors"""
    pass


@dataclass
class ConnectionStatus:
    """Represents the connection status of a Zenith instance"""
    connected: bool
    account_name: Optional[str] = None
    connection_time: Optional[float] = None  # Unix timestamp
    server_status: Optional[str] = None  # Connected to server, in queue, etc.
    queue_position: Optional[int] = None
    estimated_wait_time: Optional[int] = None  # in seconds


class ZenithHTTPClient:
    """HTTP client for communicating with ZenithProxy instances via HTTP API"""
    
    def __init__(self, api_url: str, api_token: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        
        # Set up authentication headers if token is provided
        if api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            })
        else:
            self.session.headers.update({
                'Content-Type': 'application/json'
            })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an HTTP request to the Zenith API"""
        url = f"{self.api_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ZenithAPIError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise ZenithAPIError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except requests.exceptions.ConnectionError:
            raise ZenithAPIError(f"Could not connect to {url}")
        except requests.exceptions.Timeout:
            raise ZenithAPIError(f"Request to {url} timed out")
        except requests.exceptions.RequestException as e:
            raise ZenithAPIError(f"Request error: {str(e)}")
        except json.JSONDecodeError:
            raise ZenithAPIError(f"Invalid JSON response from {url}")
    
    def get_status(self) -> ConnectionStatus:
        """Get the current connection status of the Zenith instance"""
        try:
            # This endpoint is hypothetical - based on common HTTP API patterns
            data = self._make_request('GET', '/api/status')
            
            return ConnectionStatus(
                connected=data.get('connected', False),
                account_name=data.get('account_name'),
                connection_time=data.get('connection_time'),
                server_status=data.get('server_status', 'unknown'),
                queue_position=data.get('queue_position'),
                estimated_wait_time=data.get('estimated_wait_time')
            )
        except Exception as e:
            # If we can't get detailed status, at least check if the API is reachable
            try:
                self._make_request('GET', '/api/health')
                return ConnectionStatus(connected=True, server_status="unknown")
            except:
                return ConnectionStatus(connected=False, server_status="offline")
    
    def connect_account(self, account_name: str) -> bool:
        """Connect a specific account through this Zenith instance"""
        try:
            data = self._make_request('POST', '/api/connect', {
                'account': account_name
            })
            return data.get('success', False)
        except Exception as e:
            print(f"Failed to connect account {account_name}: {str(e)}")
            return False
    
    def disconnect_account(self, account_name: str = None) -> bool:
        """Disconnect from the server. If account_name is provided, disconnect that specific account."""
        try:
            endpoint = '/api/disconnect'
            payload = {'account': account_name} if account_name else {}
            
            if account_name:
                data = self._make_request('POST', endpoint, payload)
            else:
                data = self._make_request('POST', endpoint)
                
            return data.get('success', False)
        except Exception as e:
            print(f"Failed to disconnect: {str(e)}")
            return False
    
    def get_connected_accounts(self) -> list:
        """Get list of currently connected accounts"""
        try:
            data = self._make_request('GET', '/api/connected-accounts')
            return data.get('accounts', [])
        except Exception as e:
            print(f"Failed to get connected accounts: {str(e)}")
            return []
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information if available"""
        try:
            # This is hypothetical - Zenith API may have different endpoint for queue info
            data = self._make_request('GET', '/api/queue')
            return data
        except Exception:
            # Queue info might not be directly available - return empty dict
            return {}

    def get_server_status(self) -> Dict[str, Any]:
        """Get server status information"""
        try:
            # Get information about the server that the instance is connected to
            data = self._make_request('GET', '/api/server')
            return data
        except Exception:
            # Server status might not be available - return empty dict
            return {}

    def set_rotation_enabled(self, enabled: bool) -> bool:
        """Enable/disable rotation for this instance"""
        try:
            data = self._make_request('POST', '/api/rotation', {
                'enabled': enabled
            })
            return data.get('success', False)
        except Exception as e:
            print(f"Failed to set rotation enabled: {str(e)}")
            return False

    def get_instance_info(self) -> Dict[str, Any]:
        """Get information about the Zenith instance itself"""
        try:
            data = self._make_request('GET', '/api/info')
            return data
        except Exception:
            # Instance info might not be available - return empty dict
            return {}
    
    def get_accounts(self) -> list:
        """Get list of configured accounts in this Zenith instance"""
        try:
            data = self._make_request('GET', '/api/accounts')
            return data.get('accounts', [])
        except Exception as e:
            print(f"Failed to get accounts: {str(e)}")
            return []
    
    def add_account(self, account_config: Dict[str, Any]) -> bool:
        """Add a new account to this Zenith instance"""
        try:
            data = self._make_request('POST', '/api/accounts', account_config)
            return data.get('success', False)
        except Exception as e:
            print(f"Failed to add account: {str(e)}")
            return False
    
    def remove_account(self, account_name: str) -> bool:
        """Remove an account from this Zenith instance"""
        try:
            data = self._make_request('DELETE', f'/api/accounts/{account_name}')
            return data.get('success', False)
        except Exception as e:
            print(f"Failed to remove account {account_name}: {str(e)}")
            return False
    
    def restart_instance(self) -> bool:
        """Restart this Zenith instance"""
        try:
            data = self._make_request('POST', '/api/restart')
            return data.get('success', False)
        except Exception as e:
            print(f"Failed to restart instance: {str(e)}")
            return False
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a command on the Zenith instance (if supported)"""
        try:
            data = self._make_request('POST', '/api/command', {
                'command': command
            })
            return data
        except Exception as e:
            print(f"Failed to execute command '{command}': {str(e)}")
            return {}