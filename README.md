# Fly Placer

Fly Placer is a service that automatically places your [Fly.io](https://fly.io) applications in regions where traffic is originating, if they're not already deployed there. By leveraging traffic data from Fly.io's metrics API, it dynamically adds and removes regions based on current traffic patterns. The goal is to seamlessly integrate this tool into your Fly deployments for optimal global performance. Currently, it is a work in progress or proof of concept (POC).

## Features

- **Real-Time Traffic Metrics**: Fetches current HTTP response counts per region.
- **Prometheus API Integration**: Connects directly to Fly.io's Prometheus API for up-to-date metrics.
- **Simple Output**: Displays results in an easy-to-read JSON format.

## Prerequisites

- **Python 3.8+**
- **Fly.io Account**: Ensure you have access to your application's metrics.
- **Fly.io API Token**: Required for authentication with the Fly.io API.
- **Prometheus Metrics Enabled**: Your application must have Prometheus metrics available.
- **pip**: Python package installer.

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

Create a `.env` file in the project root with the following variables:

```dotenv
FLY_API_TOKEN=your_fly_api_token
FLY_PROMETHEUS_URL=https://api.fly.io/prometheus/personal
FLY_APP_NAME=your_fly_app_name
```

### Obtaining Your Fly.io API Token

- Log in to your Fly.io account.
- Navigate to **Account Settings**.
- Generate a new personal access token with appropriate permissions.

### Setting Up Prometheus Metrics

- Ensure that your Fly.io application is configured to expose Prometheus metrics.
- Refer to the [Fly.io Metrics Documentation](https://fly.io/docs/reference/metrics/) for details.

## Usage

1. **Run the Script**:

   ```bash
   python main.py
   ```

2. **View the Output**:

   The script will output a JSON object displaying the number of HTTP responses per region over the last 5 minutes.

   Example:

   ```json
   {
     "ams": 150.0,
     "dfw": 200.0,
     "fra": 180.0,
     "lhr": 75.0
   }
   ```

## Understanding the Output

- **Region Codes**: Represent Fly.io data center locations.
- **HTTP Response Counts**: Indicate the volume of traffic handled in each region.

### Use Cases

- **Traffic Analysis**: Identify where your users are located to optimize performance.
- **Scaling Decisions**: Determine which regions may require additional resources.

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
    pip install requests python-dotenv
    ```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests for enhancements and bug fixes.

## License

This project is licensed under the MIT License.

