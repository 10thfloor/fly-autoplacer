# Fly Auto-Placer

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

Fly Auto-Placer is a service that automatically places your [Fly.io](https://fly.io) applications in regions where traffic is originating. By leveraging traffic data from Fly.io's metrics API, it dynamically adds and removes regions based on current traffic patterns. The goal is to seamlessly integrate this tool into your Fly deployments for optimal global performance.

**Note:** This project is currently a work in progress (POC).

## Features

- **Dynamic Region Placement**: Automatically deploys or removes machines in regions based on real-time traffic.
- **Real-Time Traffic Metrics**: Fetches current HTTP response counts per region.
- **Customizable Configuration**: Adjust thresholds, cooldown periods, and specify allowed or excluded regions.
- **Prometheus API Integration**: Connects directly to Fly.io's Prometheus API for up-to-date metrics.
- **Dry Run Mode**: Test the scaling logic without affecting actual deployments.
- **Historical Data Storage**: Keeps a history of traffic data for better scaling decisions.

## Table of Contents

- [Fly Auto-Placer](#fly-auto-placer)
  - [Features](#features)
  - [Table of Contents](#table-of-contents)
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
    - [Example Traffic Data](#example-traffic-data)
  - [Roadmap](#roadmap)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)
  - [License](#license)

## Prerequisites

- **Python 3.8+**
- **Fly.io Account**: Ensure you have access to your application's metrics.
- **Fly.io API Token**: Required for authentication with the Fly.io API.
- **Prometheus Metrics Enabled**: Your application must expose Prometheus metrics.
- **pip**: Python package installer.
- **Flyctl**: Fly.io command-line tool.
- **jq**: Command-line JSON processor (used in deployment scripts).

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

   ```bash
   pip install -r requirements.txt
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

Create a `config.yaml` file in the project root with the following variables:

```yaml
dry_run: true
scale_up_threshold: 50
scale_down_threshold: 30
cooldown_period: 300  # in seconds
fly_app_name: "your-app-name"

allowed_regions:
  - "ams"
  - "fra"
  - "lhr"

excluded_regions:
  - "sin"
  - "nrt"

always_running_regions:
  - "iad"
  - "cdg"
```

**Options**

- `dry_run`: If `true`, the script will not make any changes to the Fly.io API.
- `scale_up_threshold`: The traffic count that triggers a scale-up action.
- `scale_down_threshold`: The traffic count that triggers a scale-down action.
- `cooldown_period`: The number of seconds to wait before allowing another action in the same region.
- `fly_app_name`: The name of your Fly.io application.
- `allowed_regions`: A list of regions to allow deployment to.
- `excluded_regions`: A list of regions to exclude from deployment.
- `always_running_regions`: A list of regions to always keep running.

### 3. Fly.io API Token

- Log in to your Fly.io account.
- Navigate to **Account Settings**.
- Generate a new personal access token with appropriate permissions.

### 4. Prometheus Metrics Setup

- Ensure that your Fly.io application is configured to expose Prometheus metrics.
- Refer to the [Fly.io Metrics Documentation](https://fly.io/docs/reference/metrics/) for details.

### 5. Required Tools

- **Flyctl**: Install the Fly.io command-line tool.

  ```bash
  curl -L https://fly.io/install.sh | sh
  ```

- **jq**: Install `jq` for JSON processing.

  ```bash
  # On macOS
  brew install jq

  # On Ubuntu/Debian
  sudo apt-get install jq
  ```

## Usage

1. **Run the Script**:

   ```bash
   python main.py
   ```

2. **Monitor Logs**:

   Logs are stored in the `logs/auto_placer.log` file for detailed information.

3. **View Current Deployments**:

   The deployment state is saved in `data/deployment_state.json`.

## Understanding the Output

- **Deployment Actions**: The script logs when it deploys or removes machines in regions.
- **Traffic Data**: Aggregated traffic data per region is stored in `data/traffic_history.json`.
- **Logs**: Detailed logs are available in the `logs` directory.

### Example Traffic Data

```json
{
  "2024-10-01T16:03:42.269830": {
    "cdg": 26,
    "ams": 37,
    "sin": 47,
    "nrt": 74,
    "lhr": 51
  },
  "2024-10-01T16:03:36.870259": {
    "cdg": 28,
    "ams": 42,
    "iad": 12,
    "sin": 80,
    "nrt": 91,
    "lhr": 67
  }
}
```

## Roadmap

- **Advanced Traffic Forecasting**: Implement time-series forecasting models for better scaling decisions.
- **Real-Time Monitoring**: Integrate with monitoring tools like Prometheus and Grafana.
- **Improved State Management**: Utilize distributed key-value stores like etcd or Consul.
- **Containerization**: Dockerize the application for easier deployment.
- **Autoscaling Integration**: Explore Fly.io's built-in autoscaling capabilities.

## Troubleshooting

- **Authentication Errors**:

  - Ensure your `FLY_API_TOKEN` is correct and has the necessary permissions.
  - Verify that the token is correctly specified in the `.env` file.

- **Empty Output or Missing Regions**:

  - Confirm that your application is receiving traffic.
  - Check that Prometheus metrics are enabled and accessible.

- **Dependency Issues**:

  - Install required packages manually:

    ```bash
    pip install -r requirements.txt
    ```

- **Flyctl Not Found**:

  - Ensure that `flyctl` is installed and added to your PATH.

- **jq Not Found**:

  - Install `jq` for your operating system.

## Contributing

Contributions are welcome! Please open issues or submit pull requests for enhancements and bug fixes.

1. **Fork the Project**
2. **Create your Feature Branch**:

   ```bash
   git checkout -b feature/YourFeature
   ```

3. **Commit your Changes**:

   ```bash
   git commit -m 'Add YourFeature'
   ```

4. **Push to the Branch**:

   ```bash
   git push origin feature/YourFeature
   ```

5. **Open a Pull Request**

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

Feel free to explore, contribute, and provide feedback to help improve Fly Placer.