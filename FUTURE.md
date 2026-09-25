# Roadmap: regional SQLite readers with Litestream

Build a small controller that places disposable SQLite read replicas near sustained read demand. A separately operated writer publishes database changes through Litestream; regional readers use Litestream's read-replica/VFS path and disposable local caches. The intended benefit is lower end-to-end read latency without operating a persistent database volume in every reader region.

This is the project's direction, not an integration available today. The controller must never create, move, scale, restart, or remove the writer. Writer availability, backups, recovery, and failover remain outside its scope.

## What exists today

The implementation provides a foundation for controlling a dedicated reader app:

- Explicit target app and process group, validated configuration, and an authenticated trigger API.
- Regional request-count thresholds, chronological traffic averages, persisted cooldowns, and reconciliation against actual Fly Machines.
- Protected placements, minimum and maximum region limits, additions before removals, and removal deferral after failures or while a protected region is missing.
- Fail-closed handling of invalid metrics, empty observations, unsafe Machine inventory, and malformed state; missing regional metrics are not interpreted as zero traffic.
- Atomic state files, separate simulation/live state, and locking for workers sharing one storage directory.

The controller currently supports **stateless process groups only** and rejects attached volumes in the managed group. Retain that restriction for disposable readers. A writer with persistent SQLite storage must be in a separate app outside the controller's target.

The current `dry_run` mode uses synthetic traffic as well as simulated actions. It is not an observe-only mode for production traffic. There is no bundled SQLite reader app, Litestream integration, replication-lag probe, database-readiness gate, warmup budget, or latency/cost optimization.

## Reference architecture

Use a dedicated reader app with the default `app` process group as the first example. The current metric is total HTTP responses for the target app, grouped by **Fly edge region**. It does not distinguish reads from writes, identify process groups, or prove which Machine region served a request. Putting readers and the writer in one app would mix their demand signals.

Keep these boundaries explicit:

- **Writer app:** one active writer with persistent storage; publishes through Litestream to object storage. Applications route writes and reads requiring immediate consistency here. Its deployment policy is independently protected and never managed by this controller.
- **Reader app:** read-only SQLite endpoints using Litestream replicas and ephemeral local caches. Readers may be discarded and rebuilt. They receive only the object-storage access needed to read replication data.
- **Placer:** targets the reader app alone and retains a protected baseline reader placement. That protection applies to provisioned reader capacity; it does not protect the external writer or replace application health checks.

## 1. Ship a reproducible reader example

**Status: planned.** Add a minimal write service and a separate read-only service, pinned to a tested Litestream version. Document how a new reader opens the replica, populates its cache, follows updates, and handles unavailable object storage. Keep the example small enough to run locally before demonstrating Fly placement.

**Acceptance criteria:**

- A record written through the writer becomes queryable from two independent readers within a documented measured interval.
- Readers reject writes. An application path requiring read-your-writes consistency reaches the writer explicitly.
- Deleting a reader and its local cache loses no authoritative data; its replacement rebuilds and resumes following updates.
- The reader runs without an attached volume. The writer has separate storage and deployment credentials, and no controller operation targets it.

## 2. Observe real reader demand without making changes

**Status: planned.** Separate the choice of metric source from permission to mutate infrastructure. Add an explicit observe-only mode that uses real reader-app metrics and produces a proposed placement plan with reasons. Keep its state separate from live deployment membership and action timestamps.

**Acceptance criteria:**

- A complete cycle can fetch real metrics and inspect the reader fleet without issuing any scaling command.
- Reports identify edge-region counts, proposed actions, protected placements, unknown data, and decisions blocked by limits.
- Repeated observation cannot update live cooldowns or deployment state. Network errors and empty results produce no actionable plan.
- Observe a representative traffic period and compare edge-region demand with application request telemetry before treating it as a useful placement signal. Document health-check or other non-user traffic that affects the counts.

## 3. Gate promotion on database readiness and freshness

**Status: planned.** Connect reader health checks and the placement lifecycle to a successful database query and a trustworthy replication position or freshness measurement. Define the application's acceptable staleness before choosing thresholds. A running Machine alone is insufficient evidence that a reader can serve useful data.

**Acceptance criteria:**

- A cold reader is not made routable or counted as safe replacement capacity until its database probe and configured freshness requirement pass.
- Paused replication, an unavailable object store, and missing or invalid freshness data prevent promotion; existing baseline readers are retained.
- A warmup timeout is reported with a reason and does not cause removal of working capacity.
- The example documents what clients experience when a reader falls behind, including where consistency-sensitive reads go. The placer never attempts writer failover.

## 4. Bound reader warmup and replacement work

**Status: planned.** Add persistent reader lifecycle states and explicit limits for concurrent warmups, time spent warming, and placement churn. Preserve the existing region cap and cooldown safeguards. Warmup should complete before another reader is removed, and interrupted cycles should reconcile their pending work after restart.

**Acceptance criteria:**

- A configured warmup limit prevents a traffic spike from starting an unbounded set of cache rebuilds.
- Restarting the controller during warmup does not duplicate provisioning or lose the distinction between pending and ready readers.
- Failed warmups preserve protected capacity and cannot trigger repeated immediate retries.
- Each trial reports time to a usable replica, downloaded data, object-storage requests, and reader lifetime. A stated trial budget stops additional placements when exhausted.

## 5. Demonstrate a measured benefit before enabling automatic placement

**Status: planned.** Run one controlled experiment against a real read-heavy workload: compare its current reader placement with one additional regional reader. Use the same queries, dataset, load, and source locations, and include cold-cache behavior. Define acceptable freshness, error rate, warmup time, and spend before the experiment.

**Acceptance criteria:**

- Report end-to-end read p95 by source region, with the baseline and treatment clearly identified; also report freshness, errors, and sample counts.
- Account for incremental Machine runtime, storage requests, data transfer, and cache rebuilds rather than claiming savings from Machine count alone.
- Record whether the latency improvement remains worthwhile after warmup and under sustained traffic. Repeat the result before widening regional rollout.
- If the gain is immaterial, keep fixed reader placement and the observe-only tooling. Add forecasting or more elaborate placement logic only after measurements expose a specific limitation in the simple policy.
