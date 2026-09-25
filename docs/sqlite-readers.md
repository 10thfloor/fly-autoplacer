# Placing SQLite read replicas near demand

Fly Auto-Placer's focus is a fleet of disposable SQLite readers on Fly.io, backed by Litestream replication to object storage. The writer stays fixed and separately managed while regional readers follow sustained HTTP demand.

This is the reference architecture and configuration contract. The repository currently ships the placement controller and traffic dashboard. It does not yet include a runnable SQLite/Litestream application or database-aware placement gates. Track that work in the [roadmap](../FUTURE.md).

## Responsibilities

| Component | Responsibility | Managed by the placer? |
| --- | --- | --- |
| Writer app | Persistent SQLite database, writes, replication, backups, and recovery | No |
| Object storage | Litestream replica files used to reconstruct readers | No |
| Reader app | Serve reads through Litestream VFS; forward writes and reads requiring immediate consistency to the writer | Regional Machine placement only |
| Reader cache | Rebuildable cached pages or hydrated database on local ephemeral disk | Removed along with a reader; never the authoritative copy |
| Controller | Observe regional HTTP demand and add/remove reader placements within limits | One persistent controller per target app/process group |

Use separate writer and reader apps for the initial deployment. `PLACER_TARGET_APP` must name the reader app, and `process_group` selects the group to scale inside it. The controller rejects selected Machines with mounted volumes. This deliberately excludes a typical persistent SQLite writer from its supported target set; target selection remains an operator responsibility.

The `always_running_regions` setting preserves reader placements. It does not detect a writer or provide writer failover. It also does not override Fly's autostop policy.

## Reader data path

1. The writer commits to its persistent SQLite database and Litestream asynchronously replicates changes to object storage.
2. Each regional reader opens the replica using Litestream VFS. Pages are fetched on demand and cached locally, with new replica files discovered by polling.
3. Optional hydration reconstructs the full database locally while reads continue. After hydration, reads use the local file and subsequent changes keep that file updated.
4. When a reader is removed, its cache can be discarded. A replacement reconstructs its view from the replica.

See the official [VFS read-replica guide](https://litestream.io/guides/vfs/), [hydration guide](https://litestream.io/guides/vfs-hydration/), and [extension reference](https://litestream.io/reference/vfs/) for installation and configuration. Pin and test a compatible Litestream release in the reader image. Running `litestream restore` once does not keep a reader synchronized.

Readers should have read-only object-storage access and must not enable VFS write mode. Route writes through the separately managed writer. Requests that must observe a just-completed write should use the writer or an application-level consistency mechanism; asynchronous replicas do not automatically provide immediate read-after-write consistency.

## Readiness, freshness, and warmup

The reader application must expose an application readiness check and connect it to the target's Fly service health checks. Before accepting traffic, the reader should be able to execute a representative query and satisfy the application's freshness requirement. Use a policy appropriate to the workload: full hydration may be unnecessary for a small working set, while a large cold database can make initial queries expensive.

Monitor replica position and successful synchronization separately. Litestream's `litestream_lag` reports time since the last successful poll; by itself it does not prove that the writer has uploaded every committed transaction. End-to-end freshness may require comparing a writer position or a replicated application heartbeat with the reader's view.

The controller currently checks Machine state and command success. It does not inspect SQLite, wait for hydration, compare writer/reader positions, or gate removals on those signals. Application health checks are required for an initial controlled trial. Controller-side replica checks and explicit warmup/retirement gates are planned, not implemented.

## Configure the existing controller

The [example configuration](../examples/sqlite-readers/placer-config.yml) is valid for the current controller. Its values illustrate one deployment; they are not measured production thresholds.

From the repository root:

```sh
cp examples/sqlite-readers/placer-config.yml placer-service/config/config.yml
cp placer-service/.env.example placer-service/.env
cp placer-dashboard/.env.example placer-dashboard/.env
```

Generate and set the same `PLACER_API_TOKEN` in both environment files using the [local setup instructions](../README.md#start-locally). Leave `dry_run: true` while verifying the controller. This uses synthetic metrics and simulated actions; it cannot evaluate real reader demand.

Before enabling live mode:

1. Deploy the writer and its persistent storage independently. Verify Litestream replication and recovery.
2. Deploy at least one Fly Launch-managed Machine in the dedicated reader app's chosen process group. Configure Litestream VFS, disposable local caching, write routing, and application readiness in that app. The reference reader implementation is still to be built.
3. Set `PLACER_TARGET_APP` to the reader app. Set `FLY_API_TOKEN` and `FLY_PROMETHEUS_URL` for its metrics and scaling permissions.
4. For the first trial, include every existing serving reader region in both the permitted regions and `always_running_regions`. Set `max_regions` high enough to retain those regions and add the trial region. This prevents the same cycle from removing existing reader capacity while a new reader warms up. Choose a cooldown appropriate to measured warmup time and keep one controller replica with persistent state.
5. Set `dry_run: false` only for a controlled trial. Inspect authenticated metrics and invoke a placement cycle manually before scheduling further cycles.

The controller's `/health` checks controller configuration. It is not the reader's database readiness endpoint. A single trigger can otherwise both add and remove placements; there is no pause for a database readiness check between those actions. Keep the temporary protection on existing regions until the new reader's readiness and freshness have been verified, then deliberately choose the ongoing protected baseline.

## What the placement signal means

The current query measures five-minute HTTP response counts by Fly edge region for the entire target app. `process_group` scopes scaling commands and Machine inventory, but does not filter the metric query. Requests that forward writes, errors, bots, and health traffic can all contribute when they traverse the app's HTTP edge.

A dedicated reader app is the clearest initial deployment. Its request volume is still a proxy for read demand, not a count of SQL reads or their execution cost. Separating read traffic and accounting for query cost is future work where the workload requires it. Missing metrics remain unknown rather than zero.

## Prove the benefit

Compare a fixed regional reader deployment with one controlled additional placement, using the same workload. Record user-visible p95 read latency, errors, data freshness, warmup duration, Machine hours, object-storage requests/transfer, and placement churn. Use the temporary region protections above to retain existing capacity until the new reader passes the application's readiness criteria.

Frequent creation can repeatedly discard warm caches. Let measured warmup and useful serving time inform cooldowns and the regional budget. This architecture is most promising when sustained regional read demand justifies warming a nearby replica; it does not eliminate network latency for writes or uncached object-storage reads.
