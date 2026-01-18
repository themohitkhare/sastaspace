import { test, expect } from '@playwright/test';

test.describe('Comprehensive Game Scenarios', () => {

    const scenarios = [
        {
            name: 'Quick Game (15 Rounds)',
            setup: async (page) => {
                await page.getByText('GAME SETTINGS').click();
                await page.getByRole('button', { name: 'Quick (15)' }).click();
                await expect(page.getByText('Richest after 15 rounds wins')).toBeVisible();
            },
            verify: async (page) => {
                // Verify UI shows round limit if implemented, or just that game starts
                await expect(page).toHaveURL(/.*\/game\/.*/);
            }
        },
        {
            name: 'Last Standing Mode',
            setup: async (page) => {
                await page.getByText('GAME SETTINGS').click();
                await page.getByRole('button', { name: 'Last Standing' }).click();
                await expect(page.getByText('Play until one player remains')).toBeVisible();
            },
            verify: async (page) => {
                await expect(page).toHaveURL(/.*\/game\/.*/);
            }
        },
        {
            name: 'Chaos Mode',
            setup: async (page) => {
                await page.getByText('GAME SETTINGS').click();
                await page.getByRole('button', { name: 'Chaos', exact: true }).click();
                // Verify visual feedback for Chaos mode if any
            },
            verify: async (page) => {
                await expect(page).toHaveURL(/.*\/game\/.*/);
            }
        }
    ];

    for (const scenario of scenarios) {
        test(`Scenario: ${scenario.name}`, async ({ browser }) => {
            const context = await browser.newContext();
            const page = await context.newPage();

            // 1. Create Game
            await page.goto('http://localhost:9001');
            await page.getByRole('button', { name: /> CREATE GAME/i }).click();

            // 2. Join as Host
            await page.getByPlaceholder('ENTER_NAME').fill('Host');
            await page.getByRole('button', { name: 'ENTER' }).click();

            // 3. Configure
            await scenario.setup(page);

            // 4. Ready & Launch (Single player + CPU flow if supported, or just verify launch capability)
            // Note: We need at least 1 player effectively. SastaDice allows single player launch usually (CPU added automatically?).
            // Let's check if we need to add CPU. The simulator script adds CPU players.
            // In UI, we assume "CPU JOINS ON LAUNCH" (text from LobbyView) applies if alone.

            const readyBtn = page.locator('.cursor-pointer').first();
            await readyBtn.click();

            // 5. Verify Launch
            await expect(page.getByText('ALL ARMED - LAUNCHING...')).toBeVisible();

            await expect(page).toHaveURL(/.*\/game\/.*/, { timeout: 15000 });

            // 6. Scenario Verification
            await scenario.verify(page);

            await context.close();
        });
    }

    test('Feature Toggles reflected in UI', async ({ page }) => {
        await page.goto('http://localhost:9001');
        await page.getByRole('button', { name: /> CREATE GAME/i }).click();
        await page.getByPlaceholder('ENTER_NAME').fill('Host');
        await page.getByRole('button', { name: 'ENTER' }).click();

        await page.getByText('GAME SETTINGS').click();

        // Toggle Stimulus Check
        const stimulusBtn = page.getByRole('button', { name: 'Stimulus Check' });
        // Initial state should be checked (✓)
        await expect(stimulusBtn).toContainText('✓');

        await stimulusBtn.click();
        await expect(stimulusBtn).toContainText('✗');

        // Toggle back
        await stimulusBtn.click();
        await expect(stimulusBtn).toContainText('✓');
    });

});
