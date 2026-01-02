# MultiZenithProxy Collection

This repository contains two independently developed projects that both manage multiple ZenithProxy instances to achieve 24/7 server presence by rotating between multiple Minecraft accounts. Both projects were created independently by different developers to solve the same problem.

## Projects

### 1. Nexus-Manager

Located in the `Nexus-Manager` directory, this is a CLI-based manager that controls multiple ZenithProxy instances by starting/stopping Java processes and communicating with them via HTTP API. It features account management, rotation, and queue time monitoring.

**Features:**
- Multi-Instance Management: Control multiple ZenithProxy instances from a single interface
- Account Rotation: Automatically rotate between accounts before session time limits
- Queue Time Monitoring: Monitor queue times and coordinate account joining
- Smart Rotation: Predict when to connect next account based on server queue times
- Flexible Configuration: Configure multiple accounts and rotation strategies
- Command-Line Interface: Easy-to-use CLI for managing instances

### 2. Proxy-Master

Located in the `Proxy-Master` directory, this is a thread-based manager that runs multiple ZenithProxy instances and coordinates them for account rotation. It directly manages the ZenithProxy processes and handles queue time coordination.

**Features:**
- Multi-Instance Management: Control multiple ZenithProxy instances simultaneously
- Account Rotation: Automatically rotate between accounts before session time limits
- Queue Time Monitoring: Monitor queue times and coordinate account joining
- Advanced Queue Strategy: Implements sophisticated logic for queue management
- Process Management: Directly manages ZenithProxy processes
- Rotation Strategies: Supports different rotation strategies (sequential, random)

## Purpose

Both projects aim to maintain 24/7 server presence by:
1. Tracking account connection durations across all instances
2. Monitoring server queue times when available
3. Automatically rotating between accounts before session time limits
4. Pre-connecting next accounts when queue times are optimal
5. Maintaining 24/7 server presence by coordinating multiple instances

## Usage

For detailed usage instructions, configuration, and installation guides, please refer to the README files within each project directory:

- [Nexus-Manager README](Nexus-Manager/README.md)
- [Proxy-Master README](Proxy-Master/README.md)

## Comparison

| Feature | Nexus-Manager | Proxy-Master |
|---------|---------------|--------------|
| Architecture | Process-based with HTTP API communication | Thread-based with direct process management |
| Interface | CLI-only | CLI with more direct process control |
| Rotation Logic | Session time-based | Queue time and session time-based |
| Configuration | JSON-based | JSON-based |
| Management | HTTP API communication | Direct process communication |

## Contributing

Since these are independent projects, contributions should be made to each project separately. Please see the individual project documentation for contribution guidelines.

## License

Each project may have its own licensing terms. Please check the license files in each project directory.