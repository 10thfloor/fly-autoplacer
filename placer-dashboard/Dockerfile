# syntax=docker/dockerfile:1
FROM denoland/deno:2.9.7 AS build
ENV DENO_DIR=/deno-dir
WORKDIR /app
COPY deno.json deno.lock package.json ./
RUN deno install --frozen --allow-scripts=npm:esbuild
COPY . ./
RUN deno task build && deno cache --frozen server.ts && deno eval --frozen 'await import("./server.ts")'

FROM denoland/deno:2.9.7
ENV DENO_DIR=/deno-dir
WORKDIR /app
COPY --from=build --chown=deno:deno /deno-dir /deno-dir
COPY --from=build --chown=deno:deno /app /app
EXPOSE 8080
USER deno
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD deno eval 'const response = await fetch("http://localhost:8080/health"); Deno.exit(response.ok ? 0 : 1);'
CMD ["deno", "serve", "-A", "--frozen", "--cached-only", "--host", "0.0.0.0", "--port", "8080", "./server.ts"]
