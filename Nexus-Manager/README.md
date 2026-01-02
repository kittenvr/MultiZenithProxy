# Nexus-Manager

Nexus-Manager is an external application that manages multiple ZenithProxy instances to achieve 24/7 server presence by rotating between multiple Minecraft accounts. It communicates with ZenithProxy instances through their HTTP API plugin to connect/disconnect accounts at optimal times.

## Features

- **Multi-Instance Management**: Control multiple ZenithProxy instances from a single interface
- **Account Rotation**: Automatically rotate between accounts before session time limits
- **Queue Time Monitoring**: Monitor queue times and coordinate account joining
- **Smart Rotation**: Predict when to connect next account based on server queue times
- **Flexible Configuration**: Configure multiple accounts and rotation strategies
- **Command-Line Interface**: Easy-to-use CLI for managing instances

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The application uses a JSON configuration file to define ZenithProxy instances and accounts. Generate a sample configuration with:

```bash
python -m src.main generate-config
```

Edit the `config.json` file to configure your ZenithProxy instances and accounts.

## Usage

### Start the Manager
```bash
python -m src.main start
```

### Check Status
```bash
python -m src.main status
```

### Connect All Instances
```bash
python -m src.main connect --all
```

### Disconnect All Instances
```bash
python -m src.main disconnect --all
```

### List Instances
```bash
python -m src.main list-instances
```

### Add/Remove Accounts
```bash
# Add an account to an instance
python -m src.main add-account --instance zenith_instance_1 --account-name NewAccount --auth-type MSA --username user@example.com

# Remove an account from an instance
python -m src.main remove-account --instance zenith_instance_1 --account-name OldAccount

# Connect/disconnect specific accounts
python -m src.main connect-account --instance zenith_instance_1 --account-name Account1
python -m src.main disconnect-account --instance zenith_instance_1 --account-name Account1
```

### Manage Rotation
```bash
# Enable/disable rotation
python -m src.main rotation --enable
python -m src.main rotation --disable
python -m src.main rotation  # Check current rotation status
```

## Configuration Options

- `instances`: List of ZenithProxy instances to manage
- `rotation_enabled`: Enable/disable automatic rotation
- `check_interval`: How often to check instance status (in seconds)
- `queue_check_enabled`: Enable queue time monitoring
- `queue_prediction_threshold`: Queue time threshold to trigger pre-connection (in seconds)

## How It Works

The MultiZenithManager monitors multiple ZenithProxy instances and:

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