import type { MetaFunction } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";

type Traffic = {
  traffic_data: Record<string, number>;
  timestamp: string;
  dry_run: boolean;
};

type DashboardData =
  | { error: string; metrics: null }
  | { error: null; metrics: Traffic };

export const meta: MetaFunction = () => [
  { title: "Fly Auto-Placer · SQLite reader placement" },
  {
    name: "description",
    content:
      "Regional HTTP request demand for SQLite reader placement, with a planned Litestream integration. The dashboard currently reports request demand only.",
  },
];

export const headers = () => ({ "Cache-Control": "no-store" });

export async function loader() {
  const serviceUrl = Deno.env.get("PLACER_SERVICE_URL");
  const token = Deno.env.get("PLACER_API_TOKEN");
  const headers = { "Cache-Control": "no-store" };
  if (!serviceUrl || !token) {
    return json<DashboardData>(
      { error: "The dashboard connection is not configured.", metrics: null },
      { status: 503, headers },
    );
  }
  try {
    const response = await fetch(new URL("/metrics", serviceUrl), {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(15_000),
    });
    if (!response.ok) {
      throw new Error("Controller request failed");
    }
    const data: unknown = await response.json();
    if (!isTraffic(data)) {
      throw new Error("Controller response was invalid");
    }
    return json<DashboardData>(
      {
        error: null,
        metrics: {
          traffic_data: data.traffic_data,
          timestamp: new Date(data.timestamp).toISOString(),
          dry_run: data.dry_run,
        },
      },
      { headers },
    );
  } catch {
    return json<DashboardData>(
      {
        error:
          "Traffic data is unavailable. Check the controller connection and try again.",
        metrics: null,
      },
      { status: 502, headers },
    );
  }
}

function isTraffic(value: unknown): value is Traffic {
  if (!value || typeof value !== "object") return false;
  const data = value as Partial<Traffic>;
  return (
    typeof data.dry_run === "boolean" &&
    typeof data.timestamp === "string" &&
    Number.isFinite(Date.parse(data.timestamp)) &&
    !!data.traffic_data &&
    typeof data.traffic_data === "object" &&
    !Array.isArray(data.traffic_data) &&
    Object.entries(data.traffic_data).every(
      ([region, count]) =>
        /^[a-z]{3}$/.test(region) &&
        typeof count === "number" &&
        Number.isFinite(count) &&
        count >= 0,
    )
  );
}

export default function Index() {
  const { metrics, error } = useLoaderData<typeof loader>();
  const rows = Object.entries(metrics?.traffic_data ?? {}).sort(
    ([firstRegion, firstCount], [secondRegion, secondCount]) =>
      secondCount - firstCount || firstRegion.localeCompare(secondRegion),
  );
  const total = rows.reduce((sum, [, count]) => sum + count, 0);
  const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-16 text-gray-900 dark:text-gray-100">
      <header className="mb-10 flex flex-wrap items-start justify-between gap-6">
        <div>
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">
            Fly Auto-Placer
          </p>
          <h1 className="text-4xl font-bold tracking-tight">
            SQLite reader demand
          </h1>
          <p className="mt-3 text-gray-600 dark:text-gray-400">
            Five-minute regional HTTP request counts to inform SQLite reader
            placement. Litestream replication lag and reader readiness are not
            measured.
          </p>
        </div>
        <a
          href="/"
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
        >
          Refresh
        </a>
      </header>

      {error
        ? (
          <div
            role="alert"
            className="rounded-xl border border-amber-300 bg-amber-50 p-6 text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
          >
            {error}
          </div>
        )
        : metrics && (
          <>
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-3xl font-semibold">{number.format(total)}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  requests across {rows.length} regions
                </p>
              </div>
              <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font-medium text-blue-800 dark:bg-blue-950 dark:text-blue-200">
                {metrics.dry_run
                  ? "Dry run · simulated traffic"
                  : "Live traffic"}
              </span>
            </div>
            <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800">
              {rows.length
                ? (
                  <table className="w-full text-left">
                    <thead className="bg-gray-50 text-sm text-gray-600 dark:bg-gray-900 dark:text-gray-400">
                      <tr>
                        <th scope="col" className="px-6 py-4 font-medium">
                          Region
                        </th>
                        <th
                          scope="col"
                          className="px-6 py-4 text-right font-medium"
                        >
                          Requests
                        </th>
                        <th
                          scope="col"
                          className="px-6 py-4 text-right font-medium"
                        >
                          Share
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                      {rows.map(([region, count]) => (
                        <tr key={region}>
                          <th
                            scope="row"
                            className="px-6 py-4 font-mono font-medium uppercase"
                          >
                            {region}
                          </th>
                          <td className="px-6 py-4 text-right tabular-nums">
                            {number.format(count)}
                          </td>
                          <td className="px-6 py-4 text-right tabular-nums text-gray-600 dark:text-gray-400">
                            {total ? number.format(count / total * 100) : "0"}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
                : (
                  <p className="p-6 text-gray-600 dark:text-gray-400">
                    No traffic samples are available for this window.
                  </p>
                )}
            </div>
            <p className="mt-5 text-sm text-gray-500 dark:text-gray-400">
              Collected{" "}
              <time dateTime={metrics.timestamp}>
                {metrics.timestamp.replace("T", " ").replace("Z", " UTC")}
              </time>. Refresh to fetch another snapshot.
            </p>
          </>
        )}
    </main>
  );
}
