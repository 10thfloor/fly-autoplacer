# Fly Auto-Placer

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

Fly Auto-Placer is a service that automatically places your [Fly.io](https://fly.io) applications in regions where traffic is originating. By leveraging traffic data from Fly.io's metrics API, it dynamically adds and removes regions based on current traffic patterns. The goal is to seamlessly integrate this tool into your Fly deployments for optimal global performance.

**Note:** This project is currently a work in progress (POC).


## How to use this service

```bash
poetry install
poetry run python3 main.py
```

This will start the auto-placer service in dry-run mode using the default config in `config/config.yml`. <br/>
**Currently, the service will not make any changes to your Fly.io application.**

#### In another terminal:

```bash
curl -X POST http://localhost:8000/trigger
```

This will trigger the auto-placer service and return the current deployment state. <br/>
You can run this multiple times to see the **adaptive thresholds** in action.

## Table of Contents

- [Fly Auto-Placer](#fly-auto-placer)
  - [How to use this service](#how-to-use-this-service)
  - [Placement Logic](#placement-logic)
  - [Run in Docker](#run-in-docker)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
    - [1. Environment Variables](#1-environment-variables)
    - [2. Application Configuration](#2-application-configuration)
    - [3. Fly.io API Token](#3-flyio-api-token)
    - [4. Prometheus Metrics Setup](#4-prometheus-metrics-setup)
    - [5. Required Tools](#5-required-tools)
  - [Usage](#usage)
  - [Understanding the Output](#understanding-the-output)
  - [Roadmap](#roadmap)
  - [Troubleshooting](#troubleshooting)
  - [License](#license)

## Placement Logic

The placement algorithm is simple and can be found in [prediction/placement_predictor.py](prediction/placement_predictor.py).

`fly-autoplacer` uses a combination of **short-term and long-term average traffic** to make placement decisions, as well as a **cooldown** period to prevent rapid re-deployment of regions.

These settings can be adjusted in the `config/config.yml` file.


## Run in Docker

The auto-placer can be run in a Docker container.

```bash
docker build -t fly-autoplacer .
docker run -p 8000:8000 fly-autoplacer
```

---

## Features

- **Dynamic Region Placement**: Automatically deploys or removes machines in regions based on real-time traffic.
- **Real-Time Traffic Metrics**: Fetches current HTTP response counts per region.
- **Customizable Configuration**: Adjust thresholds, cooldown periods, and specify allowed or excluded regions.
- **Prometheus API Integration**: Connects directly to Fly.io's Prometheus API for up-to-date metrics.
- **Dry Run Mode**: Test the scaling logic without affecting actual deployments.
- **Historical Data Storage**: Keeps a history of traffic data for better scaling decisions.

## Prerequisites

- **Python 3.11+**
- **Fly.io Account**: Ensure you have access to your application's metrics.
- **Fly.io API Token**: Required for authentication with the Fly.io API.
- **Prometheus Metrics Enabled**: Your application must expose Prometheus metrics.
- **poetry**: Python package installer.
- **Fly CLI**: Fly.io command-line tool.

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/fly-placer.git
   ```

2. **Navigate to the Project Directory**:

   ```bash
   cd fly-placer
   ```

3. **Install Dependencies**:

   This project uses [Poetry](https://python-poetry.org/) for dependency management.

   ```bash
   poetry install
   ```

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root with the following variables:

```dotenv
FLY_API_TOKEN=your_fly_api_token
FLY_PROMETHEUS_URL=https://api.fly.io/prometheus/personal
FLY_APP_NAME=your_fly_app_name
```

### 2. Application Configuration

Update the `config/config.yml` to tweak the placement logic. <br/>
There is a file watcher in place so any changes made while the service is running will be applied automatically.

```yaml
# Configuration settings for the auto-placer

dry_run: True

# Cooldown period to prevent rapid re-deployment
# Used as a safeguard to prevent rapid re-deployment of regions when traffic
# exceeds the adaptive threshold settings.
cooldown_period: 10  # Cooldown period in seconds

# Define parameters for calculating short-term and long-term traffic averages
# These parameters are used to analyze recent trends and overall patterns in traffic data
short_term_window: 5  # Number of recent data points to consider for short-term analysis
long_term_window: 20  # Number of data points to consider for long-term analysis
alpha_short: 0.3  # Exponential smoothing factor for short-term average (higher weight to recent data)
alpha_long: 0.1  # Exponential smoothing factor for long-term average (more stable, less reactive)

# Thresholds for traffic-based placement decisions
traffic_threshold: 50         # Deploy to regions with average traffic >= 50
deployment_threshold: 10      # Remove from regions with average traffic <= 10

# Optional: Define allowed or excluded regions
allowed_regions:
  - iad
  - cdg
  - lhr
  - fra
  - sfo

excluded_regions:
  - nrt

always_running_regions:
  - fra

```

### 3. Fly.io API Token

- Log in to your Fly.io account.
- Navigate to **Account Settings**.
- Generate a new personal access token with appropriate permissions.

### 4. Prometheus Metrics Setup

- Ensure that your Fly.io application is configured to expose Prometheus metrics.
- Refer to the [Fly.io Metrics Documentation](https://fly.io/docs/reference/metrics/) for details.

### 5. Required Tools

- **Fly CLI**: Install the Fly.io command-line tool.

  ```bash
  curl -L https://fly.io/install.sh | sh
  ```

## Usage

Currently only works in dry-run mode. Won't make any changes to your Fly.io application.

1. **Run the Auto-Placer Service**:

   ```bash
   poetry run python3 main.py
   ```

   This will start the auto-placer service in dry-run mode using the default config in `config/config.yml`.
   **Currently, the service will not make any changes to your Fly.io application.**

2. **Monitor Logs**:

   Logs are stored in the `logs/auto_placer.log` file for detailed information.

3. **View Current Deployments**:

   The deployment state is saved in `data/deployment_state_dry_run.json`.

## Understanding the Output

Here is some example output from the auto-placer:

```json
{
    "deployed": [],
    "removed": [],
    "skipped": [
        {
            "region": "cdg",
            "action": "none",
            "reason": "Traffic does not meet adaptive thresholds. Current avg: 36.65, Long-term avg: 39.29"
        },
        {
            "region": "ams",
            "action": "deploy",
            "reason": "Region is not in allowed_regions list"
        },
        {
            "region": "iad",
            "action": "none",
            "reason": "Traffic does not meet adaptive thresholds. Current avg: 30.26, Long-term avg: 37.77"
        },
        {
            "region": "sin",
            "action": "deploy",
            "reason": "Region is not in allowed_regions list"
        },
        {
            "region": "nrt",
            "action": "deploy",
            "reason": "Region is in excluded_regions list"
        },
        {
            "region": "lhr",
            "action": "none",
            "reason": "Traffic does not meet adaptive thresholds. Current avg: 43.11, Long-term avg: 21.10"
        },
        {
            "region": "fra",
            "action": "none",
            "reason": "Traffic does not meet adaptive thresholds. Current avg: 19.12, Long-term avg: 38.01"
        },
        {
            "region": "sfo",
            "action": "none",
            "reason": "Traffic does not meet adaptive thresholds. Current avg: 27.22, Long-term avg: 35.91"
        }
    ],
    "current_deployment": [
        "fra",
        "iad",
        "lhr",
        "cdg"
    ],
    "updated_deployment": [
        "fra",
        "iad",
        "lhr",
        "cdg"
    ]
}
```

The `deployed` and `removed` lists show the regions that were deployed or removed.
The `skipped` list shows the regions that were skipped due to not meeting the adaptive thresholds or being in the excluded regions list. 
The `current_deployment` and `updated_deployment` lists show the current and updated deployment state respectively.

**Note: This is dry-run output. No changes will be made to your Fly.io application.**

## Roadmap

- **Advanced Traffic Forecasting**: Implement time-series forecasting models for better scaling decisions.
- **Real-Time Monitoring**: Integrate with monitoring tools like Prometheus and Grafana.
- **Improved State Management**: Utilize distributed key-value stores like etcd or Consul.
- **Autoscaling Integration**: Explore Fly.io's built-in autoscaling capabilities.

## Troubleshooting

- **Authentication Errors**:

  - Ensure your `FLY_API_TOKEN` is correct and has the necessary permissions.
  - Verify that the token is correctly specified in the `.env` file.

- **Empty Output or Missing Regions**:

  - Confirm that your application is receiving traffic.
  - Check that Prometheus metrics are enabled and accessible.


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

Feel free to explore, contribute, and provide feedback to help improve Fly Placer.