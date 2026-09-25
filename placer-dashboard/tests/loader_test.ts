import assert from "node:assert/strict";
import { headers, loader } from "../app/routes/_index.tsx";

Deno.test("document responses do not cache traffic snapshots", () => {
  assert.equal(new Headers(headers()).get("Cache-Control"), "no-store");
});

const sample = {
  traffic_data: { fra: 12, iad: 24.5 },
  timestamp: "2026-09-25T10:00:00+00:00",
  dry_run: true,
};

async function withController(
  fetcher: typeof fetch,
  test: () => Promise<void>,
) {
  const originalFetch = globalThis.fetch;
  const originalUrl = Deno.env.get("PLACER_SERVICE_URL");
  const originalToken = Deno.env.get("PLACER_API_TOKEN");
  Deno.env.set("PLACER_SERVICE_URL", "http://controller.internal:8000");
  Deno.env.set("PLACER_API_TOKEN", "secret-controller-token");
  globalThis.fetch = fetcher;
  try {
    await test();
  } finally {
    globalThis.fetch = originalFetch;
    for (
      const [key, value] of [
        ["PLACER_SERVICE_URL", originalUrl],
        ["PLACER_API_TOKEN", originalToken],
      ] as const
    ) {
      if (value === undefined) Deno.env.delete(key);
      else Deno.env.set(key, value);
    }
  }
}

Deno.test("loader uses bearer authentication only on the server and strips extra fields", async () => {
  await withController((input, init) => {
    assert.equal(String(input), "http://controller.internal:8000/metrics");
    assert.equal(
      new Headers(init?.headers).get("Authorization"),
      "Bearer secret-controller-token",
    );
    assert.ok(init?.signal);
    return Promise.resolve(
      Response.json({ ...sample, token: "secret-controller-token" }),
    );
  }, async () => {
    const response = await loader();
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    const body = await response.text();
    assert.ok(!body.includes("secret-controller-token"));
    assert.deepEqual(JSON.parse(body), {
      error: null,
      metrics: { ...sample, timestamp: "2026-09-25T10:00:00.000Z" },
    });
  });
});

Deno.test("missing configuration does not send an upstream request", async () => {
  await withController(() => {
    throw new Error("Unexpected upstream request");
  }, async () => {
    Deno.env.delete("PLACER_API_TOKEN");
    const response = await loader();
    assert.equal(response.status, 503);
    assert.equal((await response.json()).metrics, null);
  });
});

Deno.test("upstream error bodies are not exposed", async () => {
  await withController(
    () =>
      Promise.resolve(new Response("secret-controller-token", { status: 500 })),
    async () => {
      const response = await loader();
      assert.equal(response.status, 502);
      assert.ok(!(await response.text()).includes("secret-controller-token"));
    },
  );
});

Deno.test("network and timeout errors are sanitized", async () => {
  await withController(
    () => Promise.reject(new Error("secret-controller-token")),
    async () => {
      const response = await loader();
      assert.equal(response.status, 502);
      assert.ok(!(await response.text()).includes("secret-controller-token"));
    },
  );
});

for (
  const invalid of [
    {},
    { ...sample, dry_run: "false" },
    { ...sample, timestamp: "invalid" },
    { ...sample, traffic_data: { fra: -1 } },
    { ...sample, traffic_data: { fra: "12" } },
    { ...sample, traffic_data: { invalid_region: 12 } },
  ]
) {
  Deno.test(`rejects malformed metrics: ${JSON.stringify(invalid)}`, async () => {
    await withController(
      () => Promise.resolve(Response.json(invalid)),
      async () => {
        assert.equal((await loader()).status, 502);
      },
    );
  });
}

Deno.test("empty successful metrics are preserved", async () => {
  await withController(
    () => Promise.resolve(Response.json({ ...sample, traffic_data: {} })),
    async () => {
      const response = await loader();
      assert.equal(response.status, 200);
      assert.deepEqual((await response.json()).metrics?.traffic_data, {});
    },
  );
});
