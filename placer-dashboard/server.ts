import type { ServerBuild } from "@remix-run/server-runtime";
import { createRequestHandler } from "@remix-run/server-runtime";
import { serveFile } from "@std/http/file-server";
import { join } from "@std/path/join";

const handleRequest = createRequestHandler(
  (await import("./build/server/index.js")) as ServerBuild,
  "production"
);

export default {
  fetch: async (request: Request) => {
    const pathname = new URL(request.url).pathname;

    try {
      const filePath = join("./build/client", pathname);
      const fileInfo = await Deno.stat(filePath);

      if (fileInfo.isDirectory) {
        throw new Deno.errors.NotFound();
      }

      const response = await serveFile(request, filePath, { fileInfo });

      if (pathname.startsWith("/assets/")) {
        response.headers.set(
          "cache-control",
          "public, max-age=31536000, immutable"
        );
      } else {
        response.headers.set("cache-control", "public, max-age=600");
      }

      response.headers.set("X-Content-Type-Options", "nosniff");
      response.headers.set("X-Frame-Options", "DENY");
      response.headers.set(
        "Referrer-Policy",
        "strict-origin-when-cross-origin"
      );

      return response;
    } catch (error) {
      if (!(error instanceof Deno.errors.NotFound)) {
        console.error("Unexpected error:", error);
        throw error;
      }
    }

    return handleRequest(request);
  },
} satisfies Deno.ServeDefaultExport;
