import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AccountConfig:
    """Configuration for a single Minecraft account"""
    name: str
    auth_type: str  # 'MSA', 'device_code', 'prism', 'offline'
    username: Optional[str] = None
    password: Optional[str] = None  # Only for certain auth types
    access_token: Optional[str] = None
    client_token: Optional[str] = None
    uuid: Optional[str] = None
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None


@dataclass
class InstanceConfig:
    """Configuration for a single ZenithProxy instance"""
    name: str
    api_url: str  # The HTTP API endpoint of the Zenith instance
    api_token: Optional[str] = None
    server_address: str = ""  # Target server address
    server_port: int = 25565
    accounts: List[AccountConfig] = None
    enabled: bool = True
    max_connections: int = 1
    rotation_strategy: str = "sequential"  # 'sequential', 'random', 'round_robin'
    rotation_buffer_time: int = 300  # Buffer time in seconds before rotation (default 5 minutes)

    def __post_init__(self):
        if self.accounts is None:
            self.accounts = []


@dataclass
class MultiZenithConfig:
    """Main configuration for MultiZenithProxy manager"""
    instances: List[InstanceConfig]
    rotation_enabled: bool = True
    default_rotation_strategy: str = "sequential"
    default_buffer_time: int = 300  # 5 minutes default
    check_interval: int = 30  # Check every 30 seconds
    queue_check_enabled: bool = True
    queue_prediction_threshold: int = 120  # Predict when queue time is under 2 minutes

    def save_to_file(self, filepath: str):
        """Save configuration to a JSON file"""
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'MultiZenithConfig':
        """Load configuration from a JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        # Convert nested dicts back to dataclass instances
        instances = []
        for instance_data in data['instances']:
            accounts = []
            for account_data in instance_data.get('accounts', []):
                accounts.append(AccountConfig(**account_data))
            instance_data['accounts'] = accounts
            instances.append(InstanceConfig(**instance_data))
        data['instances'] = instances
        return cls(**data)

    @classmethod
    def create_sample_config(cls) -> 'MultiZenithConfig':
        """Create a sample configuration for demo purposes"""
        return cls(
            instances=[
                InstanceConfig(
                    name="zenith_instance_1",
                    api_url="http://localhost:8080",  # Default HTTP API port for Zenith
                    server_address="2b2t.org",
                    server_port=25565,
                    accounts=[
                        AccountConfig(
                            name="Account1",
                            auth_type="MSA",
                            username="user1@example.com"
                        ),
                        AccountConfig(
                            name="Account2", 
                            auth_type="MSA",
                            username="user2@example.com"
                        )
                    ],
                    rotation_strategy="sequential",
                    rotation_buffer_time=300
                ),
                InstanceConfig(
                    name="zenith_instance_2",
                    api_url="http://localhost:8081",
                    server_address="2b2t.org",
                    server_port=25565,
                    accounts=[
                        AccountConfig(
                            name="Account3",
                            auth_type="MSA",
                            username="user3@example.com"
                        )
                    ],
                    rotation_strategy="sequential",
                    rotation_buffer_time=300
                )
            ],
            rotation_enabled=True,
            default_rotation_strategy="sequential",
            default_buffer_time=300,
            check_interval=30,
            queue_check_enabled=True,
            queue_prediction_threshold=120
        )


def initialize_config(config_path: str = "config.json"):
    """Initialize configuration file if it doesn't exist"""
    if not os.path.exists(config_path):
        config = MultiZenithConfig.create_sample_config()
        config.save_to_file(config_path)
        print(f"Created sample configuration file at {config_path}")
        print("Please edit the configuration with your actual instance settings")
        return config
    else:
        return MultiZenithConfig.load_from_file(config_path)


if __name__ == "__main__":
    # Create sample config for testing
    config_path = Path(__file__).parent / "sample_config.json"
    config = MultiZenithConfig.create_sample_config()
    config.save_to_file(config_path)
    print(f"Sample configuration saved to {config_path}")