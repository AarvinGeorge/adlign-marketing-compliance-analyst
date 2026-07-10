// meta: E1 end-to-end journey. Drives the real UI (no fixtures, API on :8000)
// through the full compliance loop and asserts each step against live data:
// create a new product via the modal -> live run starts -> run parks awaiting
// input -> paste content for each parked property -> run completes -> product
// detail lists flags (By cluster and By property) -> dismiss one flag, confirm
// one with a team -> verified score changes -> reload persists both -> flag
// detail highlights an evidence substring. Re-runnable: unique product name per
// run. Screenshots per step in e2e/.artifacts.

import { test, expect, type Page } from "@playwright/test";
import path from "node:path";

const ARTIFACTS = path.join(__dirname, ".artifacts");
const shot = (page: Page, name: string) =>
  page.screenshot({ path: path.join(ARTIFACTS, name), fullPage: true });

// A single caption that trips three rules: R-01 free claim without the ~37%
// disclosure (fail), R-03 deposit product with the wrong FDIC formulation
// (fail), and R-02 finance charge stated correctly as an APR (pass, so the
// score has a nonzero denominator and a dismissal visibly moves it).
const PASTE_TEXT =
  "File your taxes for free with TurboTax Free Edition. Start filing now. " +
  "Open a Credit Karma Money checking account. Your funds are FDIC insured " +
  "up to 5 million dollars through a network of partner banks. Plus get a " +
  "Refund Advance loan at 0% APR with no loan fees.";

function verifiedScore(page: Page) {
  // MetricCard renders label, value, sublabel on separate lines; value is the
  // second line of the "Verified score" card.
  const card = page
    .getByText("Verified score", { exact: true })
    .locator("xpath=ancestor::div[contains(@class,'rounded-md')][1]");
  return card.innerText().then((t) => {
    const lines = t.split("\n").map((s) => s.trim()).filter(Boolean);
    return lines[1] ?? "";
  });
}

test("full compliance journey against the live API", async ({ page }) => {
  const stamp = Date.now();
  const productName = `Journey ${stamp}`;
  const igHandle = `journey${stamp}`;

  // --- Step 1: open the New check modal and create a new product -----------
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Marketing compliance" })
  ).toBeVisible();
  await page.getByRole("button", { name: "New check" }).first().click();

  await expect(
    page.getByRole("heading", { name: "New check" })
  ).toBeVisible();
  await page.getByRole("combobox").first().click();
  await page.getByRole("option", { name: "Create new product" }).click();
  await page.getByPlaceholder("Product name").fill(productName);
  await page
    .getByPlaceholder(/Paste links/)
    .fill(`https://example.com and instagram.com/${igHandle}`);
  // chips appear (website + instagram)
  await expect(page.getByText("example.com").first()).toBeVisible();
  await expect(page.getByText(`@${igHandle}`).first()).toBeVisible();
  await shot(page, "01-new-check-modal.png");
  await page.getByRole("button", { name: "Start check" }).click();

  // --- Step 2: the new product card appears in a live run state ------------
  // Scope every interaction to THIS product's card (the dashboard may list
  // other products). The card is the nearest rounded-lg ancestor of its name.
  const card = () =>
    page
      .getByRole("main")
      .getByText(productName, { exact: true })
      .locator("xpath=ancestor::div[contains(@class,'rounded-lg')][1]");
  await expect(card()).toBeVisible();
  await shot(page, "02-run-started.png");

  // --- Step 3: run reaches awaiting_input (Needs input) --------------------
  await expect(card().getByText("Needs input")).toBeVisible({ timeout: 90_000 });
  await shot(page, "03-awaiting-input.png");

  // --- Step 4: paste content for EACH parked property ----------------------
  await card().getByRole("button", { name: "Provide content" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Provide content" })).toBeVisible();
  const parkedCount = await dialog.getByLabel(/Content for/).count();
  expect(parkedCount).toBeGreaterThan(0);
  for (let i = 0; i < parkedCount; i++) {
    await dialog.getByLabel(/Content for/).first().fill(PASTE_TEXT);
    await dialog.getByRole("button", { name: "Paste content" }).first().click();
    await page.waitForTimeout(1500);
  }
  await shot(page, "04-pasted.png");
  await page.keyboard.press("Escape");

  // --- Step 5: run completes; card shows open flags ------------------------
  await expect(card().getByText(/\d+ open flags/)).toBeVisible({
    timeout: 90_000,
  });
  await shot(page, "05-completed.png");

  // --- Step 6: product detail lists flags in both groupings ----------------
  await card().getByRole("link", { name: productName }).click();
  await expect(page).toHaveURL(/\/products\//);
  // Per-row Dismiss buttons are exact "Dismiss" (the cluster bulk action is
  // "Dismiss all"); one per open flag.
  const rowDismiss = page.getByRole("button", { name: "Dismiss", exact: true });
  // By cluster (default) shows flags
  await expect(rowDismiss.first()).toBeVisible({ timeout: 90_000 });
  expect(await rowDismiss.count()).toBeGreaterThanOrEqual(2);
  await shot(page, "06-detail-by-cluster.png");
  // By property also shows flags
  await page.getByRole("button", { name: "By property" }).click();
  await expect(rowDismiss.first()).toBeVisible();
  expect(await rowDismiss.count()).toBeGreaterThanOrEqual(2);
  await shot(page, "07-detail-by-property.png");
  await page.getByRole("button", { name: "By cluster" }).click();

  // --- Step 7: dismiss one, confirm one with a team; score changes ---------
  const before = await verifiedScore(page);
  await rowDismiss.first().click();
  // confirm the remaining open flag and assign a team + note
  await page.getByRole("button", { name: "Confirm", exact: true }).first().click();
  await page.getByRole("button", { name: "Web", exact: true }).click();
  await page
    .getByPlaceholder("Note, travels with the assignment")
    .fill("Escalated to Web for a template fix");
  await page.getByRole("button", { name: "Assign" }).click();
  await expect(page.getByText("Assigned · Web").first()).toBeVisible();

  await expect
    .poll(async () => verifiedScore(page), { timeout: 30_000 })
    .not.toBe(before);
  const after = await verifiedScore(page);
  expect(after).not.toBe(before);
  await shot(page, "08-dispositioned.png");

  // --- Step 8: reload; both dispositions and the score persist -------------
  await page.reload();
  await expect(page.getByText("Assigned · Web").first()).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByText("Dismissed").first()).toBeVisible();
  const afterReload = await verifiedScore(page);
  expect(afterReload).toBe(after);
  expect(afterReload).not.toBe(before);
  await shot(page, "09-persisted.png");

  // --- Step 9: flag detail highlights an evidence substring ----------------
  await page.getByRole("link", { name: "Open ›" }).first().click();
  await expect(page).toHaveURL(/\/flags\//);
  const mark = page.locator("mark").first();
  await expect(mark).toBeVisible();
  const markText = (await mark.innerText()).trim();
  expect(markText.length).toBeGreaterThan(0);
  // the highlighted span is a substring of the evidence panel text
  const panelText = await page
    .getByText("Checker reasoning")
    .locator("xpath=ancestor::div[contains(@class,'rounded-lg')][1]")
    .innerText();
  expect(panelText).toContain(markText);
  await shot(page, "10-flag-detail.png");
});
