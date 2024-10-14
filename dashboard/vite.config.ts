import { vitePlugin as remix } from "@remix-run/dev";
import { defineConfig, type PluginOption } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [
    remix({
      future: {
        v3_fetcherPersist: true,
        v3_relativeSplatPath: true,
        v3_throwAbortReason: true,
      },
    }) as PluginOption,
    tsconfigPaths() as PluginOption,
  ],
});
