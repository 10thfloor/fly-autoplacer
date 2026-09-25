"""Reconcile observed traffic with safe, bounded regional placements."""

from datetime import datetime, timezone
import logging
import os

from automation.fly_client import FlyClient, FlyError
from prediction.placement_predictor import PlacementPredictor
from utils.config_loader import Config
from utils.history_manager import update_traffic_history, calculate_region_averages
from utils.metrics_fetcher import MetricsFetcher
from utils.state_manager import load_placement_state, save_placement_state, placement_lock


logger = logging.getLogger(__name__)


class AutoPlacer:
    def __init__(self, config, *, metrics_fetcher=None, fly_client=None, clock=None):
        self.config = Config.validate(config)
        self.dry_run = self.config["dry_run"]
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.metrics = metrics_fetcher or MetricsFetcher(dry_run=self.dry_run, config=self.config)
        self.app_name = self.metrics.get_app_name()
        if not self.dry_run:
            target = os.environ.get("PLACER_TARGET_APP")
            if not target or target != self.app_name:
                raise ValueError("Live placement requires an explicit PLACER_TARGET_APP")
        self.scope = {"app_name": self.app_name, "process_group": self.config["process_group"],
                      "data_dir": self.config["data_dir"]}
        self.fly = fly_client or FlyClient(self.app_name, self.config["process_group"],
                                           self.config["command_timeout"])
        self.predictor = PlacementPredictor(self.config)

    async def process_traffic_data(self):
        # File locking also serializes separate workers sharing this data directory.
        with placement_lock(self.dry_run, **self.scope):
            state = load_placement_state(self.dry_run, **self.scope)
            if not self.dry_run:
                actual = self.fly.regions()
                state["deployed"] = {region: state["deployed"].get(region) for region in actual}

            traffic = self.metrics.fetch_region_traffic()
            if not traffic:
                return self._result(state, [], {"deployed": [], "removed": [], "errors": [],
                    "skipped": [{"region": "*", "action": "none", "reason": "No traffic observations; placement left unchanged"}]})

            history = update_traffic_history(
                traffic, self.dry_run, **self.scope, max_entries=self.config["long_term_window"] + 1)
            averages = calculate_region_averages(history, self.config)
            actions = []
            # Protected regions are required placements even without a regional sample.
            for region in self.config["always_running_regions"]:
                if region not in state["deployed"]:
                    actions.append((region, "scale_up"))
            for region, values in sorted(averages.items(), key=lambda item: (-item[1]["short"], item[0])):
                if self._should_process_region(region):
                    action = self.predictor.predict_placement_actions(region, values)
                    if action and (region, action) not in actions:
                        actions.append((region, action))
            # Validate storage before the first possible infrastructure mutation.
            save_placement_state(state, self.dry_run, **self.scope)
            return self._execute_actions(actions, state)

    def _should_process_region(self, region):
        allowed = self.config["allowed_regions"]
        return region not in self.config["excluded_regions"] and (not allowed or region in allowed)

    def _is_in_cooldown(self, region, state):
        timestamp = state["last_actions"].get(region)
        if not timestamp:
            return False
        previous = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=timezone.utc)
        return (self.clock() - previous).total_seconds() < self.config["cooldown_period"]

    def _execute_actions(self, actions, state):
        results = {"deployed": [], "removed": [], "skipped": [], "errors": []}
        updated = []
        missing = set(self.config["always_running_regions"]) - state["deployed"].keys()
        maximum = self.config["max_regions"]
        if maximum is not None and len(state["deployed"]) + len(missing) > maximum:
            results["errors"] = [{"region": region, "action": "scale_up",
                "error": "Cannot restore protected region within max_regions; increase the limit or reconcile placement"}
                for region in sorted(missing)]
            if results["errors"]:
                return self._result(state, updated, results)
        # Add capacity before removing capacity. Required regions were queued first.
        actions = sorted(dict.fromkeys(actions), key=lambda item: item[1] != "scale_up")
        for region, action in actions:
            reason = None
            if action not in ("scale_up", "scale_down"):
                reason = "Unknown action"
            elif not self._should_process_region(region):
                reason = "Region is not permitted by configuration"
            elif action == "scale_down" and region in self.config["always_running_regions"]:
                reason = "Region is protected by always_running_regions"
            elif self._is_in_cooldown(region, state):
                reason = "Region is in cooldown"
            elif action == "scale_up" and region in state["deployed"]:
                reason = "Region is already deployed"
            elif action == "scale_down" and region not in state["deployed"]:
                reason = "Region is not deployed"
            elif action == "scale_down" and set(self.config["always_running_regions"]) - state["deployed"].keys():
                reason = "Removal deferred until all protected regions are deployed"
            elif action == "scale_up" and self.config["max_regions"] is not None and len(state["deployed"]) >= self.config["max_regions"]:
                reason = "Maximum region count reached"
            elif action == "scale_down" and len(state["deployed"]) <= self.config["min_regions"]:
                reason = "Minimum region count must be preserved"
            elif action == "scale_down" and results["errors"]:
                reason = "Removal deferred because an earlier operation failed"
            if reason:
                results["skipped"].append({"region": region, "action": action, "reason": reason})
                continue

            timestamp = self.clock().isoformat()
            # Persist the attempt before calling Fly. A timeout may have applied the
            # command; retain cooldown while the next run reconciles actual state.
            state["last_actions"][region] = timestamp
            save_placement_state(state, self.dry_run, **self.scope)
            try:
                if not self.dry_run:
                    self.fly.scale_region(region, 1 if action == "scale_up" else 0)
            except FlyError as exc:
                logger.warning("Placement action failed: app=%s process=%s region=%s action=%s: %s",
                               self.app_name, self.config["process_group"], region, action, exc)
                results["errors"].append({"region": region, "action": action, "error": str(exc)})
                continue
            if action == "scale_up":
                state["deployed"][region] = timestamp
                results["deployed"].append(region)
            else:
                del state["deployed"][region]
                results["removed"].append(region)
            save_placement_state(state, self.dry_run, **self.scope)
            logger.info("Placement action completed: app=%s process=%s region=%s action=%s dry_run=%s",
                        self.app_name, self.config["process_group"], region, action, self.dry_run)
            updated.append(region)
        return self._result(state, updated, results)

    def _result(self, state, updated, results):
        return {"app": self.app_name, "process_group": self.config["process_group"],
                "dry_run": self.dry_run, "actions_taken": results, "updated_regions": updated,
                "current_regions": sorted(state["deployed"]), "timestamp": self.clock().isoformat()}
