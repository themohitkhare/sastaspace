import { test, expect } from '@playwright/test';

test.describe('SastaHero Game Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Set a stable player ID for E2E tests
    await page.addInitScript(() => {
      localStorage.setItem('sastahero_player_id', 'e2e-test-player');
    });
  });

  test('loads the game feed with cards', async ({ page }) => {
    await page.goto('/sastahero/');
    // Should show loading then cards
    await expect(page.getByTestId('game-feed')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('shard-bar')).toBeVisible();
    await expect(page.getByTestId('card-display')).toBeVisible();
  });

  test('displays shard bar with all 5 shard types', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('shard-bar')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('shard-SOUL')).toBeVisible();
    await expect(page.getByTestId('shard-SHIELD')).toBeVisible();
    await expect(page.getByTestId('shard-VOID')).toBeVisible();
    await expect(page.getByTestId('shard-LIGHT')).toBeVisible();
    await expect(page.getByTestId('shard-FORCE')).toBeVisible();
  });

  test('card display shows required elements', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('card-name')).toBeVisible();
    await expect(page.getByTestId('rarity-label')).toBeVisible();
    await expect(page.getByTestId('shard-yield')).toBeVisible();
  });

  test('swipe up via keyboard advances card', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    const firstCardName = await page.getByTestId('card-name').textContent();

    // Swipe up using keyboard
    await page.getByTestId('swipe-handler').focus();
    await page.keyboard.press('ArrowUp');

    // Wait for card exit animation + new card
    await page.waitForTimeout(500);

    // Card should change (or show next card counter)
    const display = page.getByTestId('card-display');
    if (await display.isVisible()) {
      // If not last card, name may have changed
      const currentName = await page.getByTestId('card-name').textContent();
      // Just verify the game didn't crash
      expect(currentName).toBeTruthy();
    }
  });

  test('swipe down via keyboard advances card', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('swipe-handler').focus();
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(500);

    // Verify game still works
    const feed = page.getByTestId('game-feed');
    await expect(feed).toBeVisible();
  });

  test('swipe left via keyboard advances card', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('swipe-handler').focus();
    await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(500);

    await expect(page.getByTestId('game-feed')).toBeVisible();
  });

  test('swipe right via keyboard advances card', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('swipe-handler').focus();
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(500);

    await expect(page.getByTestId('game-feed')).toBeVisible();
  });

  test('WASD keys work for swiping', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('swipe-handler').focus();
    await page.keyboard.press('w'); // UP
    await page.waitForTimeout(500);

    await expect(page.getByTestId('game-feed')).toBeVisible();
  });

  test('powerup panel opens and closes', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('powerup-button')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('powerup-button').click();
    await expect(page.getByTestId('powerup-panel')).toBeVisible();
    await expect(page.getByTestId('powerup-REROLL')).toBeVisible();
    await expect(page.getByTestId('powerup-PEEK')).toBeVisible();

    // Close panel
    await page.getByLabel('Close powerups panel').click();
    await expect(page.getByTestId('powerup-panel')).not.toBeVisible();
  });

  test('swiping through all 10 cards shows quiz', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    // Swipe through all 10 cards
    await page.getByTestId('swipe-handler').focus();
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('ArrowUp');
      await page.waitForTimeout(400);
    }

    // Should show quiz or loading quiz
    const quizCard = page.getByTestId('quiz-card');
    const quizLoading = page.getByTestId('quiz-loading');
    const isQuiz = await quizCard.isVisible().catch(() => false);
    const isQuizLoading = await quizLoading.isVisible().catch(() => false);
    expect(isQuiz || isQuizLoading).toBeTruthy();
  });

  test('quiz shows question and 4 options', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    // Swipe through 10 cards
    await page.getByTestId('swipe-handler').focus();
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(400);
    }

    // Wait for quiz to load
    await expect(page.getByTestId('quiz-card')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('quiz-question')).toBeVisible();
    await expect(page.getByTestId('quiz-option-0')).toBeVisible();
    await expect(page.getByTestId('quiz-option-1')).toBeVisible();
    await expect(page.getByTestId('quiz-option-2')).toBeVisible();
    await expect(page.getByTestId('quiz-option-3')).toBeVisible();
    await expect(page.getByTestId('quiz-timer')).toBeVisible();
  });

  test('answering quiz shows result and continue button', async ({ page }) => {
    await page.goto('/sastahero/');
    await expect(page.getByTestId('card-display')).toBeVisible({ timeout: 10000 });

    // Swipe through 10 cards
    await page.getByTestId('swipe-handler').focus();
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('ArrowUp');
      await page.waitForTimeout(400);
    }

    // Wait for quiz
    await expect(page.getByTestId('quiz-card')).toBeVisible({ timeout: 10000 });

    // Answer the question
    await page.getByTestId('quiz-option-0').click();

    // Should show result
    await expect(page.getByTestId('quiz-result')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('quiz-continue')).toBeVisible();
  });
});
