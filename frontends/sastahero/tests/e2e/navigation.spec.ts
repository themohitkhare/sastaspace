import { test, expect } from '@playwright/test';

test.describe('SastaHero Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('sastahero_player_id', 'e2e-nav-player');
    });
  });

  test('bottom nav shows all 5 tabs', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('nav-play')).toBeVisible();
    await expect(page.getByTestId('nav-cards')).toBeVisible();
    await expect(page.getByTestId('nav-story')).toBeVisible();
    await expect(page.getByTestId('nav-learn')).toBeVisible();
    await expect(page.getByTestId('nav-me')).toBeVisible();
  });

  test('navigate to collection page', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('nav-cards').click();

    // Should show collection or loading/error
    const collection = page.getByTestId('collection-book');
    const loading = page.getByTestId('collection-loading');
    const error = page.getByTestId('collection-error');
    await expect(
      collection.or(loading).or(error)
    ).toBeVisible({ timeout: 10000 });
  });

  test('navigate to story page', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('nav-story').click();

    const story = page.getByTestId('story-thread');
    const loading = page.getByTestId('story-loading');
    const error = page.getByTestId('story-error');
    await expect(
      story.or(loading).or(error)
    ).toBeVisible({ timeout: 10000 });
  });

  test('navigate to knowledge page', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('nav-learn').click();

    const knowledge = page.getByTestId('knowledge-bank');
    const loading = page.getByTestId('knowledge-loading');
    const error = page.getByTestId('knowledge-error');
    await expect(
      knowledge.or(loading).or(error)
    ).toBeVisible({ timeout: 10000 });
  });

  test('navigate to profile page', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('nav-me').click();

    const profile = page.getByTestId('profile-page');
    const loading = page.getByTestId('profile-loading');
    const error = page.getByTestId('profile-error');
    await expect(
      profile.or(loading).or(error)
    ).toBeVisible({ timeout: 10000 });
  });

  test('navigate back to game feed', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });

    // Go to profile
    await page.getByTestId('nav-me').click();
    await page.waitForTimeout(500);

    // Go back to play
    await page.getByTestId('nav-play').click();
    await expect(page.getByTestId('game-feed')).toBeVisible({ timeout: 10000 });
  });

  test('active tab is highlighted', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('bottom-nav')).toBeVisible({ timeout: 10000 });

    // Play tab should be active (aria-selected=true)
    const playTab = page.getByTestId('nav-play');
    await expect(playTab).toHaveAttribute('aria-selected', 'true');

    // Navigate to cards
    await page.getByTestId('nav-cards').click();
    await page.waitForTimeout(500);

    const cardsTab = page.getByTestId('nav-cards');
    await expect(cardsTab).toHaveAttribute('aria-selected', 'true');
    await expect(playTab).toHaveAttribute('aria-selected', 'false');
  });
});
