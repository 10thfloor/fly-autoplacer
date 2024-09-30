# Fly Scaler

Fly Scaler is a simple predictive smart region placement service for [Fly.io](https://fly.io). It automatically scales machines across regions based on traffic patterns, optimizing resource utilization and improving application performance globally.

## Features

- **Predictive Scaling**: Utilizes historical traffic data to forecast demand and adjust resources proactively.
- **Automatic Region Management**: Scales machines up or down across different regions based on real-time metrics.
- **Dry Run Mode**: Allows testing of scaling strategies without affecting live deployments.
- **Fly.io CLI Integration**: Seamlessly interacts with Fly.io's command-line interface for efficient machine management.

## Prerequisites

- **Python 3.8+**
- **Fly.io CLI**: Install [here](https://fly.io/docs/hands-on/install-flyctl/).
- **Poetry**: Dependency management tool. Install with:

  ```bash
  pip install poetry
  ```

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/fly-scaler.git
   ```

2. **Navigate to the Project Directory**:

   ```bash
   cd fly-scaler
   ```

3. **Install Dependencies**:

   ```bash
   poetry install
   ```

## Configuration

Customize the scaler by modifying the `config.yaml` file.

## Configuration Options

The `config.yaml` file allows you to customize the behavior of Fly Scaler. Here are the available configuration options:

- `app_name`: The name of your Fly.io application.
- `regions`: List of regions to monitor and scale.
- `scaling_interval`: Time interval (in minutes) between scaling decisions.
- `traffic_threshold`: Traffic threshold to trigger scaling actions.
- `max_machines_per_region`: Maximum number of machines allowed in each region.
- `min_machines_per_region`: Minimum number of machines to maintain in each region.
- `dry_run`: Boolean flag to enable or disable dry run mode.

Example `config.yaml`:
