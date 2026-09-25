# Fly Auto-Placer dashboard

This read-only dashboard shows regional HTTP request demand to inform placement
of SQLite reader Machines on Fly.io. SQLite readers backed by Litestream are the
intended deployment model. The current dashboard reports request counts; it does
not integrate with Litestream or inspect SQLite databases.

## What it shows

- Request counts by region over the most recent five minutes, with totals and
  each region’s share.
- A dry-run badge for simulated traffic, or a live-traffic badge for real
  metrics.
- The snapshot timestamp and a Refresh link to collect another snapshot.

These are demand signals, not measurements of SQLite reads, replication lag, or
reader readiness. The dashboard has no placement controls.

Counts cover all HTTP requests for the configured target app. A dedicated reader
app keeps that signal focused on reader demand instead of mixing writer traffic
into placement decisions.

The Remix loader fetches the controller’s authenticated `GET /metrics` endpoint
on the server. `PLACER_API_TOKEN` stays server-side and is not included in
browser responses. The displayed traffic statistics are publicly readable
wherever the dashboard is exposed.

## Local development

Use Deno **2.9.7**. First start the controller using the
[root setup guide](../README.md), then run these commands from
`placer-dashboard/`:

```sh
cp .env.example .env
```

Set the following in `.env`:

- `PLACER_SERVICE_URL`: the controller’s base URL, usually
  `http://127.0.0.1:8000` locally.
- `PLACER_API_TOKEN`: the same generated token configured on the controller.

Then install the locked dependencies and start the development server:

```sh
deno install --frozen --allow-scripts=npm:esbuild
deno task dev
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080). The development task loads
`.env` and binds to the local interface.

## Checks and deployment

```sh
deno task test
deno task build
deno task typecheck
```

The production server uses the generated `build/client` and `build/server`
artifacts and serves a public `/health` endpoint. Follow the
[root deployment guide](../README.md) for Docker, Fly.io process groups,
environment variables, and secrets.

## Future scope

A Litestream-aware reader-placement workflow needs database restore and catch-up
checks, replication-lag measurements, and readiness gates before readers receive
traffic. Those integrations are future work; the current view supplies
request-demand context only. See the [project roadmap](../FUTURE.md)
for the broader plan.
