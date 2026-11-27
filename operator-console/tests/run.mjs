// `pnpm run test`: the console's TypeScript tests, with no test dependency. The installed Vite loads every
// tests/*.test.ts file, and the src modules it imports, with its SSR module loader (ssrLoadModule). Node's built-in
// node:test runs the tests that the files register, and they check with node:assert. Vite runs without a config file,
// in middleware mode, with no port, HMR, file watcher or dependency pre-bundling: nothing listens and nothing is
// written.
import { readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const files = readdirSync(new URL(".", import.meta.url)).filter((name) => name.endsWith(".test.ts")).sort();
if (files.length === 0) throw new Error("no tests/*.test.ts file");
const server = await createServer({
  configFile: false, root: fileURLToPath(new URL("..", import.meta.url)), logLevel: "error", clearScreen: false,
  appType: "custom", server: { middlewareMode: true, hmr: false, ws: false, watch: null },
  optimizeDeps: { noDiscovery: true, include: [] },
});
try {
  // A file registers its tests while it loads; node:test runs them and sets a failing exit code. The loaded
  // modules need no server afterwards.
  for (const name of files) await server.ssrLoadModule(`/tests/${name}`);
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await server.close();
}
