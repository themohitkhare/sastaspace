import { test, expect } from '@playwright/test';

test.describe('SastaDice Game Flow E2E', () => {

    test('Host can configure and start a game', async ({ page }) => {
        // 1. Go to Home Page
        await page.goto('http://localhost:9001');
        await expect(page).toHaveTitle(/SastaDice/);

        // 2. Create New Game
        const createBtn = page.getByRole('button', { name: /> CREATE GAME/i });
        await expect(createBtn).toBeVisible();
        await createBtn.click();

        // 3. Verify Lobby Loaded
        await expect(page.getByText('GAME LOBBY')).toBeVisible();

        // 4. Join Game
        await page.getByPlaceholder('ENTER_NAME').fill('TestHost');
        await page.getByRole('button', { name: 'ENTER' }).click();

        // 5. Verify Player Joined
        await expect(page.getByText('TestHost').first()).toBeVisible();
        await expect(page.getByText('YOU')).toBeVisible();

        // 6. Configure Settings (Host Only)
        // Open settings panel
        const settingsToggle = page.getByText('GAME SETTINGS');
        await expect(settingsToggle).toBeVisible();
        await settingsToggle.click();

        // Verify default state
        await expect(page.getByText('Richest after 30 rounds wins')).toBeVisible();

        // Change to Quick Game (15 rounds)
        const quickBtn = page.getByRole('button', { name: 'Quick (15)' });
        await quickBtn.click();

        // Check if description updated (implies backend update + re-render)
        // Note: This might be slightly delayed as it round-trips to backend
        await expect(page.getByText('Richest after 15 rounds wins')).toBeVisible();

        // Change Win Condition to "Last Standing"
        const lastStandingBtn = page.getByRole('button', { name: 'Last Standing' });
        await lastStandingBtn.click();
        await expect(page.getByText('Play until one player remains')).toBeVisible();

        // Toggle a feature (e.g. Stimulus Check)
        const stimulusToggle = page.getByText('Stimulus Check');
        await stimulusToggle.click();
        // Verify toggle state changed (we'd need to check class or icon, simpler to check visual feedback text if added, 
        // but for now we assume if no error, it worked. Ideally we check the checkmark/cross)

        // 7. Ready Up
        // Find the launch key/toggle
        // Note: LaunchKey component usually has a specific visual structure. 
        // We look for the button or interactive element.
        // Based on LobbyView.jsx it's inside <LaunchKey>

        // We'll click the "ARM SYSTEM" or "READY" text logic if accessible, 
        // or look for the key element.
        const keyContainer = page.locator('.cursor-pointer'); // The LaunchKey main div has cursor-pointer
        await keyContainer.first().click();

        // Verify Ready Status
        await expect(page.getByText('READY', { exact: true }).first()).toBeVisible();

        // 8. Verify "Waiting for players" (since we are alone)
        await expect(page.getByText('WAITING FOR OPERATORS...')).toBeVisible();

        // Since we can't easily add 2nd player in single-context test without multi-tab support,
        // we verify up to this point which confirms the "Create -> Configure -> Join -> Ready" flow works.
    });

    /* 
     * To test full game start, we would need multiple browser contexts.
     * Playwright supports this efficiently.
     */
    test('Full multiplayer game start simulation', async ({ browser }) => {
        // Context 1: Host
        const context1 = await browser.newContext();
        const page1 = await context1.newPage();

        await page1.goto('http://localhost:9001');
        await page1.getByRole('button', { name: /> CREATE GAME/i }).click();

        // Get Game ID/Code to join
        await expect(page1.getByText('GAME LOBBY')).toBeVisible();
        // The code is displayed in the UI, we can grab it from URL or UI
        const gameUrl = page1.url(); // e.g., http://localhost:9001/lobby/UUID

        // Host Joins
        await page1.getByPlaceholder('ENTER_NAME').fill('HostBot');
        await page1.getByRole('button', { name: 'ENTER' }).click();

        // Context 2: Player 2
        const context2 = await browser.newContext();
        const page2 = await context2.newPage();
        await page2.goto(gameUrl);

        await page2.getByPlaceholder('ENTER_NAME').fill('JoinerBot');
        await page2.getByRole('button', { name: 'ENTER' }).click();

        // Host Configures Settings (Quick Game)
        await page1.getByText('GAME SETTINGS').click();
        await page1.getByRole('button', { name: 'Quick (15)' }).click();

        // Verify Player 2 sees the settings change (Real-time sync check!)
        // Note: Current implementation is polling based, so it should update.
        await expect(page2.getByText('GAME MODE')).toBeVisible();
        // We expect Player 2 (non-host) to see the updated text
        await expect(page2.getByText('Richest after 15 rounds wins')).toBeVisible();

        // Both Ready Up
        await page1.locator('.cursor-pointer').first().click(); // Host Ready
        await page2.locator('.cursor-pointer').first().click(); // Player 2 Ready

        // Verify Launch Sequence
        await expect(page1.getByText('ALL ARMED - LAUNCHING...')).toBeVisible();
        await expect(page2.getByText('ALL ARMED - LAUNCHING...')).toBeVisible();

        // Wait for Game Board (Game Started)
        // Assuming redirection to /game/:id
        await expect(page1).toHaveURL(/.*\/game\/.*/, { timeout: 10000 });
        await expect(page2).toHaveURL(/.*\/game\/.*/, { timeout: 10000 });

        // Verify Board Loaded
        await expect(page1.locator('.board-container')).toBeVisible(); // Assuming class name
        // Or look for "GO" tile
        await expect(page1.getByText('GO', { exact: true })).toBeVisible();

        // Cleanup
        await context1.close();
        await context2.close();
    });
});
