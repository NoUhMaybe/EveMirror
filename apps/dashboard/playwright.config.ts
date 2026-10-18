import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));
const python =
  process.env.EVE_TEST_PYTHON ??
  (process.platform === "win32"
    ? `${root}/.venv-ci311/Scripts/python.exe`
    : `${root}/.venv-dev/bin/python`);
const origin = "http://127.0.0.1:8766";
export default defineConfig({
  testDir: "tests/browser",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  globalTeardown: "./tests/browser/teardown.mjs",
  timeout: 30000,
  expect: { timeout: 10000 },
  outputDir: "test-results",
  reporter: "list",
  use: {
    baseURL: origin,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    launchOptions: {
      args: [
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
        "--disable-gpu-rasterization",
      ],
    },
  },
  projects: [
    { name: "portrait-1080", use: { viewport: { width: 1080, height: 1920 } } },
    { name: "portrait-720", use: { viewport: { width: 720, height: 1280 } } },
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
  ],
  webServer: {
    command: `"${python}" -m tests.browser_fixture_app`,
    cwd: root,
    url: `${origin}/health/live`,
    reuseExistingServer: false,
    timeout: 30000,
    env: { EVE_DASHBOARD_SIMULATION: "1", EVE_DASHBOARD_TEST_ORIGIN: origin },
  },
});
