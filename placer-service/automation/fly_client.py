"""A narrowly scoped Fly CLI adapter for stateless regional placements."""

import json
import re
import subprocess


class FlyError(RuntimeError):
    pass


class FlyClient:
    def __init__(self, app_name, process_group="app", timeout=120):
        for value in (app_name, process_group):
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
                raise ValueError("Invalid Fly target or process group")
        self.app_name = app_name
        self.process_group = process_group
        self.timeout = timeout

    def _run(self, arguments):
        try:
            return subprocess.run(
                ["fly", *arguments, "--app", self.app_name],
                check=True, text=True, capture_output=True, timeout=self.timeout,
            ).stdout
        except subprocess.TimeoutExpired as exc:
            raise FlyError("Fly command timed out; the next run will reconcile actual placement") from exc
        except FileNotFoundError as exc:
            raise FlyError("Fly CLI is not installed") from exc
        except subprocess.CalledProcessError as exc:
            # CLI output can contain environment variables or credentials.
            raise FlyError(f"Fly command failed with exit status {exc.returncode}") from exc

    def regions(self):
        try:
            machines = json.loads(self._run(["machines", "list", "--json"]))
            if not isinstance(machines, list):
                raise ValueError
            regions = set()
            for machine in machines:
                if not isinstance(machine, dict) or not isinstance(machine.get("config"), dict):
                    raise ValueError
                config = machine["config"]
                metadata = config.get("metadata") or {}
                if not isinstance(metadata, dict):
                    raise ValueError
                # Match fly scale count's Fly Launch inventory filter exactly.
                if metadata.get("fly_platform_version") != "v2":
                    continue
                group = metadata.get("fly_process_group") or metadata.get("process_group")
                if group != self.process_group:
                    continue
                if machine.get("state") == "destroyed":
                    continue
                if machine.get("state") not in ("started", "stopped", "suspended"):
                    raise FlyError("Target Machines are unhealthy or changing state; retry after they stabilize")
                region = machine.get("region")
                if not isinstance(region, str) or not re.fullmatch(r"[a-z0-9]{3}", region):
                    raise ValueError
                if config.get("mounts"):
                    raise FlyError("Automatic placement supports stateless process groups only; a Machine has a volume")
                regions.add(region)
            if not regions:
                raise FlyError("Use fly deploy to create at least one managed Machine in the target process group before enabling live placement")
            return regions
        except (ValueError, TypeError, KeyError) as exc:
            raise FlyError("Fly returned invalid Machine data; placement was not changed") from exc

    def scale_region(self, region, count):
        if not re.fullmatch(r"[a-z0-9]{3}", region) or count not in (0, 1):
            raise ValueError("Invalid regional placement request")
        self._run(["scale", "count", str(count), "--process-group", self.process_group,
                   "--region", region, "--yes"])
