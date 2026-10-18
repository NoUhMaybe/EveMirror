export default async function teardown() {
  try {
    await fetch("http://127.0.0.1:8766/__test__/shutdown", {
      method: "POST",
      signal: AbortSignal.timeout(5000),
      headers: {
        Authorization: "Bearer loopback-dashboard-fixture-" + "x".repeat(32),
      },
    });
  } catch {
    /* A failed startup may have no server to stop. */
  }
}
