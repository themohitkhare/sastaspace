
import { test, expect } from '@playwright/test';

test('Host privileges preserved when created with CPUs', async ({ page, request }) => {
    // 1. Create Game via API with cpu_count=3
    // Note: Assuming API is at localhost:8000/api/v1/sastadice
    const response = await request.post('http://localhost:8000/api/v1/sastadice/games?cpu_count=3');
    expect(response.ok()).toBeTruthy();

    const game = await response.json();
    const gameId = game.id;
    const accessCode = gameId.substring(0, 8).toUpperCase();
    console.log(`Created Game: ${gameId} with 3 CPUs`);

    // 2. Go to Home Page
    await page.goto('http://localhost:9001');

    // 3. Join Game via Access Code
    await page.getByPlaceholder('ACCESS_CODE').fill(accessCode);
    await page.getByRole('button', { name: /> JOIN OPERATION/i }).click();

    // 4. Authenticate in Lobby
    await page.getByPlaceholder('ENTER_NAME').fill('HostCheck');
    await page.getByRole('button', { name: 'ENTER' }).click();

    // 5. Verify Settings Panel is Visible
    // "GAME SETTINGS" is the header of the editable panel.
    // Read-only view uses "GAME MODE".
    await expect(page.getByText('GAME SETTINGS')).toBeVisible();

    // 6. Verify Host Status (Crown)
    await expect(page.getByText('HOSTCHECK 👑')).toBeVisible();
});
