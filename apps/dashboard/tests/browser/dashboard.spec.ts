import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";

const fixture = {
  Authorization: "Bearer loopback-dashboard-fixture-" + "x".repeat(32),
};
const operator = {
  Authorization: "Bearer operator-test-token-" + "b".repeat(32),
};
async function control(request: APIRequestContext, action: string) {
  const result = await request.post(`/__test__/${action}`, {
    headers: fixture,
  });
  expect(result.ok(), await result.text()).toBeTruthy();
  return result;
}
async function pair(page: Page, request: APIRequestContext) {
  await page.goto("/");
  await page.getByRole("button", { name: "Pair this display" }).click();
  const code = await page.getByTestId("pair-code").textContent();
  expect(code).toMatch(/^[A-Z2-9]{8}$/);
  const approve = await request.post("/api/operator/browser/pairings/approve", {
    headers: operator,
    data: { code, device_id: "mirror-1" },
  });
  expect(approve.ok()).toBeTruthy();
  await expect(
    page.getByRole("button", { name: "This week", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Connected", { exact: true })).toBeVisible();
}
async function layout(page: Page) {
  await page.getByTestId("context").evaluate(async (element) => {
    await Promise.all(
      element
        .getAnimations({ subtree: true })
        .filter(
          (animation) =>
            animation.effect?.getComputedTiming().iterations !== Infinity,
        )
        .map((animation) => animation.finished.catch(() => {})),
    );
  });
  const boxes = await Promise.all(
    ["clock", "assistant", "context"].map((id) =>
      page.getByTestId(id).boundingBox(),
    ),
  );
  const view = page.viewportSize()!;
  boxes.forEach((box) => {
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(view.width + 1);
    expect(box!.y + box!.height).toBeLessThanOrEqual(view.height + 1);
  });
  const [clock, assistant, context] = boxes;
  for (const locator of [
    page.locator(".forecast-day").last(),
    page.getByTestId("timer-row").first(),
    page.getByTestId("timer-row").last(),
  ]) {
    if (await locator.count()) {
      const child = await locator.boundingBox();
      expect(child!.y + child!.height).toBeLessThanOrEqual(
        context!.y + context!.height + 1,
      );
    }
  }
  const overlap = (
    a: NonNullable<typeof clock>,
    b: NonNullable<typeof clock>,
  ) =>
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y;
  expect(overlap(clock!, assistant!)).toBeFalsy();
  expect(overlap(assistant!, context!)).toBeFalsy();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
}

test.beforeEach(async ({ request }) => {
  await control(request, "reset");
});

test("presence settings show sensor health and journaled backlight transitions", async ({
  page,
  request,
}) => {
  await pair(page, request);
  await page
    .getByRole("button", { name: "Display settings", exact: true })
    .click();
  await page.getByLabel("Preferred brightness (%)").fill("42");
  await page.getByLabel("Enable presence automation").check();
  await page.getByRole("button", { name: "Save display policy" }).click();
  const diagnostics = page.getByRole("region", {
    name: "Presence and backlight",
  });
  await expect(diagnostics).toContainText("healthy · PRESENT · simulated");
  await expect(diagnostics).toContainText("42%");
  await control(request, "presence-absent");
  await expect(page.getByTestId("presence-status")).toContainText(
    "Backlight asleep",
  );
  await control(request, "presence-unknown");
  await expect(page.getByTestId("presence-status")).toContainText(
    "Backlight awake",
  );
  await page.getByRole("button", { name: "Backlight off temporarily" }).click();
  await control(request, "presence-present");
  await expect(page.getByTestId("presence-status")).toContainText(
    "Backlight asleep",
  );
  await page.getByRole("button", { name: "Resume automatic policy" }).click();
  await expect(page.getByTestId("presence-status")).toContainText(
    "Backlight awake",
  );
  await page.screenshot({
    path: `test-results/presence-${test.info().project.name}.png`,
  });
});

test("paired browser follows a complete voice weather/timer turn, reload and alarm", async ({
  page,
  request,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const contacted: string[] = [];
  page.on("request", (request) => contacted.push(request.url()));
  await pair(page, request);
  const cookies = await page.context().cookies();
  const cookie = cookies.find((x) => x.name === "eve_browser_session");
  expect(cookie?.httpOnly).toBeTruthy();
  expect(cookie?.sameSite).toBe("Strict");
  expect(await page.evaluate(() => document.cookie)).not.toContain(
    "eve_browser_session",
  );
  await control(request, "speak");
  await expect(page.getByTestId("weather")).toContainText("The week ahead");
  await expect(page.getByTestId("timers")).toContainText("Tea");
  await expect(page.getByTestId("voice-label")).toHaveText("Speaking");
  await expect(page.getByTestId("subtitles")).toContainText(
    "ten-minute tea timer",
  );
  await expect(
    page.getByTestId("subtitles").locator(".spoken").first(),
  ).toBeVisible();
  await layout(page);
  await page.screenshot({
    path: info.outputPath("weekly-speaking.png"),
    fullPage: true,
    animations: "disabled",
  });
  await control(request, "finish");
  await expect(page.getByTestId("voice-label")).toHaveText("Anything else?");
  await expect(page.getByTestId("subtitles")).not.toContainText(
    "ten-minute tea timer",
  );
  await page.reload();
  await expect(page.getByTestId("timers")).toContainText("Tea");
  await expect(page.getByTestId("weather")).toContainText("The week ahead");
  await page.locator(".orb-canvas canvas").evaluate((element) => {
    const gl = (element as HTMLCanvasElement).getContext("webgl2");
    const extension = gl?.getExtension("WEBGL_lose_context");
    if (!extension)
      throw Error("Test renderer cannot exercise WebGL context loss");
    extension.loseContext();
  });
  await expect(page.locator(".static-orb")).toBeVisible();
  await page.context().setOffline(true);
  await expect(page.getByText("Reconnecting", { exact: true })).toBeVisible();
  await control(request, "expire");
  await page.screenshot({
    path: info.outputPath("offline.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.context().setOffline(false);
  await expect(page.getByTestId("timers")).toContainText("Your timer is ready");
  await expect(
    page.getByRole("button", { name: "This week", exact: true }),
  ).toBeDisabled();
  await layout(page);
  await page.screenshot({
    path: info.outputPath("alarm.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Dismiss alarm" }).click();
  await expect(page.getByTestId("timers")).not.toContainText(
    "Your timer is ready",
  );
  expect(contacted.some((url) => url.includes(":8765"))).toBeFalsy();
  expect(
    contacted.every(
      (url) =>
        url.startsWith("http://127.0.0.1:8766/") || url.startsWith("data:"),
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});

test("long playback captions stay contained, cancellation and revocation clear private state", async ({
  page,
  request,
}, info) => {
  await pair(page, request);
  await control(request, "long-speak");
  await expect(page.getByTestId("voice-label")).toHaveText("Speaking");
  const subtitles = page.getByTestId("subtitles");
  await expect(subtitles).toContainText("A little more detail");
  await expect
    .poll(() => subtitles.evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  const box = await subtitles.boundingBox();
  expect(box!.height).toBeLessThanOrEqual(175);
  await layout(page);
  await page.screenshot({
    path: info.outputPath("long-response.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Stop Eve" }).click();
  await expect(subtitles).not.toContainText("A little more detail");
  await page.getByRole("button", { name: "Timers", exact: true }).click();
  await page.getByLabel("Timer name").fill("Water");
  await page.getByLabel("Minutes", { exact: true }).fill("40");
  await page.getByRole("button", { name: "Start timer" }).click();
  await expect(page.getByTestId("timer-row")).toHaveCount(2);
  const water = page.getByTestId("timer-row").filter({ hasText: "Water" });
  await water.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(water).toContainText("Paused");
  await water.getByRole("button", { name: "Resume", exact: true }).click();
  await expect(water).toContainText("Counting down");
  await layout(page);
  await page.screenshot({
    path: info.outputPath("multiple-timers.png"),
    fullPage: true,
    animations: "disabled",
  });
  await control(request, "expire");
  await expect(page.getByTestId("timers")).toContainText("Your timer is ready");
  await page.getByRole("button", { name: "Dismiss alarm" }).click();
  await expect(page.getByTestId("timers")).not.toContainText(
    "Your timer is ready",
  );
  const sessions = await request.get("/api/operator/browser/sessions", {
    headers: operator,
  });
  const list = (await sessions.json()).sessions;
  for (const session of list.filter(
    (item: { revoked: boolean }) => !item.revoked,
  )) {
    expect(
      (
        await request.post(
          `/api/operator/browser/sessions/${session.id}/revoke`,
          { headers: operator },
        )
      ).ok(),
    ).toBeTruthy();
  }
  await expect(
    page.getByRole("button", { name: "Pair this display" }),
  ).toBeVisible();
  await expect(page.getByTestId("weather")).toHaveCount(0);
  await expect(page.getByTestId("timers")).toHaveCount(0);
});

test("weather, approved home/media, mute, settings and reduced motion", async ({
  page,
  request,
}, info) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await pair(page, request);
  await expect(page.locator(".static-orb")).toBeVisible();
  await page.getByRole("button", { name: "Weather", exact: true }).click();
  await expect(page.getByTestId("weather")).toContainText("Right now");
  await page.screenshot({
    path: info.outputPath("current.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Today", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /Hourly temperature forecast/ }),
  ).toBeVisible();
  // A constant real forecast paints a horizontal path with a zero-height box.
  await expect(page.locator(".chart-line").last()).toHaveAttribute("d", / L/);
  await expect(page.locator(".chart-line").last()).toHaveCSS(
    "stroke",
    "rgb(143, 221, 240)",
  );
  await expect(page.locator(".hour-labels span").first()).toBeVisible();
  await layout(page);
  await page.screenshot({
    path: info.outputPath("daily.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "My space", exact: true }).click();
  await expect(page.getByTestId("smart-home")).toContainText("Bedroom lights");
  await page.getByRole("button", { name: "Off", exact: true }).click();
  await expect(page.getByTestId("smart-home")).toContainText("off");
  await page.getByRole("button", { name: "Media", exact: true }).click();
  await expect(page.getByTestId("media")).toContainText("TV");
  await expect(
    page.getByRole("button", { name: "Pause", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("media.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Mute mic", exact: true }).click();
  await expect(page.getByTestId("voice-label")).toHaveText("Microphone muted");
  await page.getByRole("button", { name: "Display settings" }).click();
  await expect(page.getByRole("dialog")).toContainText("Display settings");
  await expect(page.getByRole("dialog")).not.toContainText(
    "operator-test-token",
  );
  await page.screenshot({
    path: info.outputPath("settings.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Unpair this display" }).click();
  await expect(
    page.getByRole("button", { name: "Pair this display" }),
  ).toBeVisible();
});
