# Fly Auto-Placer

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Deno Version](https://img.shields.io/badge/deno-2.0%2B-blue.svg)](https://deno.land/)

Fly Auto-Placer is a service that automatically places your [Fly.io](https://fly.io) applications in regions where traffic is originating. By leveraging traffic data from Fly.io's metrics API, it dynamically adds and removes regions based on current traffic patterns.

**Note:** This project is currently a work in progress (POC).

## Getting Started

You'll need to install the following tools:

- [Deno v2+](https://deno.com/)
- [Poetry](https://python-poetry.org/)
- [Fly.io Account + CLI](https://fly.io)

## Configuration

### Environment Variables

Create a `.env` file in the `placer-service` root with the following variables:

```dotenv
FLY_API_TOKEN=your_fly_api_token
FLY_PROMETHEUS_URL=https://api.fly.io/prometheus/personal
FLY_APP_NAME=your_fly_app_name
```

Create a `.env` file in the `placer-dashboard` root with the following variables:

```dotenv
PLACER_SERVICE_URL=http://localhost:8000
```

## Local Development

Installs dependencies in both apps and starts up the servers.

```bash
deno -A local-dev.ts
```

This will start the auto-placer service in dry-run mode using the [default config](#configuration) in [`placer-service/config/config.yaml`](placer-service/config/config.yaml) on [http://localhost:8000](http://localhost:8000)

**Currently, the service will not make any changes to your Fly.io application.**

It will also start the placer-dashboard (Remix.run) in watch mode. <br/>
Open [http://localhost:8080](http://localhost:8080) to view it in the browser.

## Triggering the auto-placer

```bash
curl -X POST http://localhost:8000/trigger
```

This will trigger the auto-placer service and return the current deployment state. <br/>
You can run this _multiple times_ to see the [**adaptive thresholds**](#placement-logic) in action.

## Table of Contents

- [Fly Auto-Placer](#fly-auto-placer)
  - [Getting Started](#getting-started)
  - [Configuration](#configuration)
    - [Environment Variables](#environment-variables)
  - [Local Development](#local-development)
  - [Triggering the auto-placer](#triggering-the-auto-placer)
  - [Table of Contents](#table-of-contents)
  - [Placement Logic](#placement-logic)
  - [Features](#features)
  - [Application Configuration](#application-configuration)
  - [Fly.io Setup](#flyio-setup)
    - [Fly CLI](#fly-cli)
    - [Fly.io API Token](#flyio-api-token)
    - [Prometheus Metrics Setup](#prometheus-metrics-setup)
  - [Understanding the Output](#understanding-the-output)
  - [Roadmap](#roadmap)
  - [License](#license)

## Placement Logic

The placement algorithm is simple and can be found in [`prediction/placement_predictor.py`](placer-service/prediction/placement_predictor.py).

`fly-autoplacer` uses a combination of **short-term and long-term average traffic** to make placement decisions, as well as a **cooldown** period to prevent rapid re-deployment of regions.

These settings can be adjusted in the [`config/config.yml`](placer-service/config/config.yml) file.

## Features

- **Dynamic Region Placement**: Automatically deploys or removes machines in regions based on real-time traffic.
- **Real-Time Traffic Metrics**: Fetches current HTTP response counts per region.
- **Customizable Configuration**: Adjust thresholds, cooldown periods, and specify allowed or excluded regions.
- **Prometheus API Integration**: Connects directly to Fly.io's Prometheus API for up-to-date metrics.
- **Dry Run Mode**: Test the scaling logic without affecting actual deployments.
- **Historical Data Storage**: Keeps a history of traffic data for better scaling decisions.

## Application Configuration

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

## Fly.io Setup

### Fly CLI

- **Fly CLI**: Install the Fly.io command-line tool.

  ```bash
  curl -L https://fly.io/install.sh | sh
  ```

### Fly.io API Token

- Log in to your Fly.io account.
- Navigate to **Account Settings**.
- Generate a new personal access token with read/write permissions.

### Prometheus Metrics Setup

- Ensure that your Fly.io application is configured to expose Prometheus metrics.
- Refer to the [Fly.io Metrics Documentation](https://fly.io/docs/reference/metrics/) for details.

## Understanding the Output

**Monitor Logs**:
   Logs are stored in the [`placer-service/data/logs/auto_placer.log`](placer-service/data/logs/auto_placer.log) file for detailed information.

**View Current Deployments**:
   The deployment state is saved in [`placer-service/data/deployment_state_dry_run.json`](placer-service/data/deployment_state_dry_run.json).

Here is some example output from the auto-placer after triggering:

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

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

Feel free to explore, contribute, and provide feedback to help improve Fly Placer.
