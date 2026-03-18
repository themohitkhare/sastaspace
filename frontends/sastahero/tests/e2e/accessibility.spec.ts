import { test, expect } from '@playwright/test';

test.describe('SastaHero Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('sastahero_player_id', 'e2e-a11y-player');
    });
  });

  test('card display has proper ARIA attributes', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    const card = page.getByTestId('card-display');
    await expect(card).toHaveAttribute('role', 'article');
    const ariaLabel = await card.getAttribute('aria-label');
    expect(ariaLabel).toContain('card');
    expect(ariaLabel).toContain('rarity');
  });

  test('swipe handler has keyboard instructions', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('swipe-handler')).toBeVisible({ timeout: 10000 });

    const handler = page.getByTestId('swipe-handler');
    await expect(handler).toHaveAttribute('role', 'application');
    const ariaLabel = await handler.getAttribute('aria-label');
    expect(ariaLabel).toContain('arrow keys');
    expect(ariaLabel).toContain('WASD');
  });

  test('swipe handler is focusable', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('swipe-handler')).toBeVisible({ timeout: 10000 });

    const handler = page.getByTestId('swipe-handler');
    await expect(handler).toHaveAttribute('tabIndex', '0');
  });

  test('shard bar has status role', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('shard-bar')).toBeVisible({ timeout: 10000 });

    const bar = page.getByTestId('shard-bar');
    await expect(bar).toHaveAttribute('role', 'status');

    // Each shard has aria-label
    const soul = page.getByTestId('shard-SOUL');
    const ariaLabel = await soul.getAttribute('aria-label');
    expect(ariaLabel).toContain('Soul shards');
  });

  test('bottom nav uses tablist role', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });

    const nav = page.getByTestId('bottom-nav');
    await expect(nav).toHaveAttribute('role', 'tablist');

    const playTab = page.getByTestId('nav-play');
    await expect(playTab).toHaveAttribute('role', 'tab');
  });

  test('powerup panel has dialog role', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('powerup-button')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('powerup-button').click();

    const panel = page.getByTestId('powerup-panel');
    await expect(panel).toHaveAttribute('role', 'dialog');

    // Close button has aria-label
    const closeBtn = page.getByLabel('Close powerups panel');
    await expect(closeBtn).toBeVisible();
  });

  test('powerup button has aria-label', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('powerup-button')).toBeVisible({ timeout: 10000 });

    const btn = page.getByTestId('powerup-button');
    await expect(btn).toHaveAttribute('aria-label', 'Open powerups panel');
  });
});
