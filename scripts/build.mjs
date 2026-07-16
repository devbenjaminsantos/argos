import { build } from "esbuild";
import { cp, mkdir, rm } from "node:fs/promises";

await rm("dist", { recursive: true, force: true });
await mkdir("dist", { recursive: true });

await build({
  entryPoints: {
    "background/service-worker": "src/background/service-worker.ts",
    "content/mercado-livre": "src/content/mercado-livre.ts",
    "offscreen/offscreen": "src/offscreen/offscreen.ts",
    "popup/popup": "src/popup/popup.ts",
  },
  bundle: true,
  format: "esm",
  outdir: "dist",
  target: "chrome109",
  sourcemap: true,
});

await Promise.all([
  cp("src/manifest.json", "dist/manifest.json"),
  cp("src/popup/popup.html", "dist/popup/popup.html"),
  cp("src/popup/popup.css", "dist/popup/popup.css"),
  cp("src/offscreen/offscreen.html", "dist/offscreen/offscreen.html"),
  cp("src/icons", "dist/icons", { recursive: true }),
]);

