# Proxy-Master

Proxy-Master is a thread-based manager that runs multiple ZenithProxy instances to achieve 24/7 server presence by rotating between multiple Minecraft accounts. It directly manages ZenithProxy processes and coordinates account rotation based on connection duration and queue times.

## Features

- **Multi-Instance Management**: Control multiple ZenithProxy instances simultaneously
- **Account Rotation**: Automatically rotate between accounts before session time limits
- **Queue Time Monitoring**: Monitor queue times and coordinate account joining
- **Advanced Queue Strategy**: Implements sophisticated logic for queue management
- **Process Management**: Directly manages ZenithProxy processes
- **Rotation Strategies**: Supports different rotation strategies (sequential, random)
- **Proxy Support**: Supports proxy rotation for additional account management

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The application uses a JSON configuration file to define ZenithProxy instances and accounts. Create a `multi_zenith_config.json` file with your configuration.

## Usage

### Start the Manager
```bash
python multi_zenith_manager.py
```

## Configuration Options

- `instances`: List of ZenithProxy instances to manage
- `rotation_enabled`: Enable/disable automatic rotation
- `rotation_strategy`: Strategy for rotation (sequential, random)
- `rotation_interval`: Interval between rotation checks (in seconds)
- `proxy_pool`: List of proxies to rotate between instances

## How It Works

The MultiZenith-Proxy-Core monitors multiple ZenithProxy instances and:

1. Tracks account connection durations across all instances
2. Monitors server queue times when available
3. Automatically rotates between accounts before session time limits
4. Pre-connects next accounts when queue times are optimal
5. Maintains 24/7 server presence by coordinating multiple instances

## Requirements

- Python 3.7+
- ZenithProxy with HTTP API plugin enabled
- Multiple configured Minecraft accounts in ZenithProxy instances

## License

MIT License