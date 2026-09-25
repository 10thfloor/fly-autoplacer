import type { AppLoadContext, EntryContext } from "@remix-run/node";
import { RemixServer } from "@remix-run/react";
import { isbot } from "isbot";
import { renderToReadableStream } from "react-dom/server";

const ABORT_DELAY = 5_000;

export default async function handleRequest(
  request: Request,
  responseStatusCode: number,
  responseHeaders: Headers,
  remixContext: EntryContext,
  _loadContext: AppLoadContext,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ABORT_DELAY);
  try {
    const body = await renderToReadableStream(
      <RemixServer
        context={remixContext}
        url={request.url}
        abortDelay={ABORT_DELAY}
      />,
      {
        signal: controller.signal,
        onError() {
          responseStatusCode = 500;
          console.error("Server rendering failed");
        },
      },
    );

    // Finished renders must not be aborted after their response has succeeded.
    body.allReady.then(() => clearTimeout(timer), () => clearTimeout(timer));

    if (isbot(request.headers.get("user-agent") || "")) {
      await body.allReady;
    }

    responseHeaders.set("Content-Type", "text/html; charset=utf-8");
    return new Response(body, {
      headers: responseHeaders,
      status: responseStatusCode,
    });
  } catch {
    clearTimeout(timer);
    console.error("Server rendering failed");
    return new Response("The page could not be rendered.", {
      status: 500,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  }
}
