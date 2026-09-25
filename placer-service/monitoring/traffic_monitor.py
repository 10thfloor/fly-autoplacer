"""Fetch traffic with the configuration supplied for this run."""

from utils.metrics_fetcher import MetricsFetcher


def collect_region_traffic(config=None, dry_run=None):
    return MetricsFetcher(dry_run=dry_run, config=config).fetch_region_traffic()
