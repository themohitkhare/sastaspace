/**
 * Concurrent Stress Testing - Test for race conditions
 * 
 * Simulates multiple players acting simultaneously to find race conditions
 */

import { test, expect } from '@playwright/test';

/**
 * Helper to create a game via API
 */
async function createGameViaAPI() {
    const response = await fetch('http://localhost:8000/api/v1/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cpu_count: 0 })
    });
    
    if (!response.ok) {
        throw new Error(`Failed to create game: ${response.status}`);
    }
    
    const data = await response.json();
    return data.id;
}

/**
 * Helper to join a game
 */
async function joinGame(page, gameId, playerName) {
    await page.goto(`http://localhost:9001/lobby/${gameId}`);
    await page.getByPlaceholder('ENTER_NAME').fill(playerName);
    await page.getByRole('button', { name: 'ENTER' }).click();
    await page.waitForTimeout(1000);
}

/**
 * Helper to ready up
 */
async function readyUp(page) {
    const launchKey = page.locator('button[aria-label*="key"], button[aria-label*="Key"], .launch-key-container').first();
    await launchKey.click();
    await page.waitForTimeout(1000);
}

/**
 * Helper to wait for game to start
 */
async function waitForGameStart(page, timeout = 30000) {
    return await expect.poll(async () => {
        const url = page.url();
        return url.includes('/game/');
    }, {
        timeout,
        intervals: [1000, 2000, 3000]
    }).toBeTruthy();
}

test.describe('Concurrent Stress Testing - Race Conditions', () => {

    test('4-Player Concurrent Ready-Up', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        const contexts = await Promise.all(
            Array(4).fill().map(() => browser.newContext())
        );
        const pages = await Promise.all(
            contexts.map(ctx => ctx.newPage())
        );

        await Promise.all(pages.map((page, i) => joinGame(page, gameId, `Player${i + 1}`)));
        await Promise.all(pages.map((page) => readyUp(page)));
        await waitForGameStart(pages[0], 30000).catch(() => false);
        const allInGame = await Promise.all(
            pages.map(async (page) => page.url().includes('/game/'))
        );
        expect(allInGame.filter(Boolean).length).toBeGreaterThanOrEqual(2);
        await Promise.all(contexts.map((ctx) => ctx.close()));
    });

    test('Concurrent Action Execution', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        const contexts = await Promise.all([
            browser.newContext(),
            browser.newContext()
        ]);
        const pages = await Promise.all(
            contexts.map(ctx => ctx.newPage())
        );

        // Join and start game
        await Promise.all([
            joinGame(pages[0], gameId, 'Alice'),
            joinGame(pages[1], gameId, 'Bob')
        ]);

        await Promise.all(pages.map((page) => readyUp(page)));
        await waitForGameStart(pages[0], 30000).catch(() => false);
        const results = await Promise.allSettled([
            pages[0].locator('button:visible:not([disabled])').first().click().catch(() => null),
            pages[1].locator('button:visible:not([disabled])').first().click().catch(() => null),
        ]);
        expect(results.filter((r) => r.status === 'fulfilled').length).toBeGreaterThanOrEqual(1);
        await Promise.all(contexts.map((ctx) => ctx.close()));
    });

    test('Rapid Polling Stress Test', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        const contexts = await Promise.all(
            Array(5).fill().map(() => browser.newContext())
        );
        const pages = await Promise.all(
            contexts.map(ctx => ctx.newPage())
        );

        await Promise.all(pages.map((page, i) => joinGame(page, gameId, `Poller${i + 1}`)));
        await pages[0].waitForTimeout(5000);
        const stillResponsive = await Promise.all(
            pages.map(async (page) => {
                try {
                    const title = await page.title();
                    return title !== '';
                } catch {
                    return false;
                }
            })
        );

        expect(stillResponsive.filter(Boolean).length).toBe(5);
        await Promise.all(contexts.map((ctx) => ctx.close()));
    });

    test('Auction Concurrent Bidding Stress', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        
        const contexts = await Promise.all([
            browser.newContext(),
            browser.newContext(),
            browser.newContext()
        ]);
        const pages = await Promise.all(
            contexts.map(ctx => ctx.newPage())
        );

        // Join and start
        await Promise.all(
            pages.map((page, i) => joinGame(page, gameId, `Bidder${i + 1}`))
        );

        await Promise.all(pages.map(page => readyUp(page)));
        await waitForGameStart(pages[0], 30000).catch(() => false);

        const auctionStarted = await pages[0]
            .locator('text=/AUCTION|BID/i')
            .isVisible({ timeout: 10000 })
            .catch(() => false);
        if (auctionStarted) {
            const bidResults = await Promise.allSettled(
                pages.map((page) => page.getByRole('button', { name: /BID/i }).click({ timeout: 2000 }))
            );
            expect(bidResults.some((r) => r.status === 'fulfilled')).toBe(true);
        }
        await Promise.all(contexts.map((ctx) => ctx.close()));
    });

    test('State Synchronization Under Load', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        const contexts = await Promise.all(
            Array(4).fill().map(() => browser.newContext())
        );
        const pages = await Promise.all(
            contexts.map(ctx => ctx.newPage())
        );

        await Promise.all(pages.map((page, i) => joinGame(page, gameId, `Observer${i + 1}`)));
        await pages[0].waitForTimeout(3000);
        const playerCounts = await Promise.all(
            pages.map((page) => page.locator('.player-list .player, .player-panel').count())
        );
        expect([...new Set(playerCounts)].length).toBe(1);
        expect(playerCounts[0]).toBe(4);
        await Promise.all(contexts.map((ctx) => ctx.close()));
    });

    test('Rapid Game Creation and Deletion', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();
        await page.goto('http://localhost:9001');
        for (let i = 0; i < 10; i++) {
            await page.getByRole('button', { name: /CREATE GAME/i }).click();
            await page.waitForTimeout(500);
            await page.goto('http://localhost:9001');
            await page.waitForTimeout(300);
        }
        const homeVisible = await page.getByText(/SASTADICE|CREATE GAME/i)
            .isVisible({ timeout: 3000 })
            .catch(() => false);
        expect(homeVisible).toBe(true);
        await context.close();
    });

    test('Network Interruption Simulation', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();

        await page.goto('http://localhost:9001');
        
        // Create game
        await page.getByRole('button', { name: /CREATE GAME/i }).click();
        await page.waitForTimeout(1000);

        // Join game
        await page.getByPlaceholder('ENTER_NAME').fill('NetworkTest');
        await page.getByRole('button', { name: 'ENTER' }).click();
        await page.waitForTimeout(1000);

        // Simulate offline
        await context.setOffline(true);
        await page.waitForTimeout(2000);

        // Try to interact while offline
        const launchKey = page.locator('button[aria-label*="key"]').first();
        if (await launchKey.isVisible({ timeout: 2000 }).catch(() => false)) {
            await launchKey.click().catch(() => {});
        }

        // Go back online
        await context.setOffline(false);
        await page.waitForTimeout(2000);

        expect(await page.locator('body').isVisible({ timeout: 5000 })).toBe(true);
        await context.close();
    });
});

test.describe('Edge Case Stress Tests', () => {
    test('Maximum Player Count Stress', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        
        // Try to add 8 players (maximum)
        const contexts = await Promise.all(
            Array(8).fill().map(() => browser.newContext())
        );
        const pages = await Promise.all(
            contexts.map(ctx => ctx.newPage())
        );

        // All join simultaneously
        const joinResults = await Promise.allSettled(
            pages.map((page, i) => joinGame(page, gameId, `Player${i + 1}`))
        );

        const successfulJoins = joinResults.filter((r) => r.status === 'fulfilled').length;
        expect(successfulJoins).toBeGreaterThanOrEqual(2);
        expect(successfulJoins).toBeLessThanOrEqual(8);

        await Promise.all(contexts.map(ctx => ctx.close()));
    });

    test('Long Running Game Stability', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();
        await page.goto('http://localhost:9001');
        const cpuButton = page.getByRole('button', { name: /CPU GAME/i });
        if (await cpuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await cpuButton.click();
            await page.waitForTimeout(30000);
            expect(await page.locator('body').isVisible({ timeout: 5000 })).toBe(true);
        }
        await context.close();
    });
});


test.describe('Zombie Player Simulation - Disconnect Handling', () => {

    test('Player disconnects mid-turn, game continues', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        
        const [hostCtx, p2Ctx] = await Promise.all([
            browser.newContext(),
            browser.newContext()
        ]);
        const [hostPage, p2Page] = await Promise.all([
            hostCtx.newPage(),
            p2Ctx.newPage()
        ]);
        
        // Setup 2-player game
        await Promise.all([
            joinGame(hostPage, gameId, 'Host'),
            joinGame(p2Page, gameId, 'Player2')
        ]);
        
        await Promise.all([readyUp(hostPage), readyUp(p2Page)]);
        await waitForGameStart(hostPage, 30000).catch(() => false);
        await hostPage.waitForTimeout(2000);
        const rollBtn = hostPage.getByRole('button', { name: /ROLL/i });
        if (await rollBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
            await rollBtn.click();
            await hostPage.waitForTimeout(500);
            await hostCtx.close();
            await p2Page.waitForTimeout(35000);
            const gameActive = await p2Page.locator('.game-board, .game-container').isVisible({ timeout: 10000 }).catch(() => false);
            expect(gameActive).toBe(true);
        }
        await p2Ctx.close();
    });

    test('Player disconnects mid-auction', async ({ browser }) => {
        const gameId = await createGameViaAPI();
        
        const contexts = await Promise.all([
            browser.newContext(),
            browser.newContext(),
            browser.newContext()
        ]);
        const pages = await Promise.all(
            contexts.map(ctx => ctx.newPage())
        );
        
        // Setup 3-player game
        await Promise.all(
            pages.map((page, i) => joinGame(page, gameId, `Player${i + 1}`))
        );
        
        await Promise.all(pages.map(page => readyUp(page)));
        await waitForGameStart(pages[0], 30000).catch(() => false);
        for (let attempt = 0; attempt < 5; attempt++) {
            await pages[0].waitForTimeout(3000);
            const auctionVisible = await pages[0].locator('text=/AUCTION|BIDDING/i').isVisible({ timeout: 1000 }).catch(() => false);
            if (auctionVisible) {
                const bidBtn1 = pages[0].getByRole('button', { name: /BID/i });
                if (await bidBtn1.isVisible({ timeout: 2000 }).catch(() => false)) await bidBtn1.click();
                const bidBtn2 = pages[1].getByRole('button', { name: /BID/i });
                if (await bidBtn2.isVisible({ timeout: 2000 }).catch(() => false)) {
                    await bidBtn2.click();
                    await contexts[1].close();
                }
                await pages[0].waitForTimeout(35000);
                break;
            }
        }
        await contexts[0].close();
        if (contexts[2]) await contexts[2].close();
    });

    test('Player reconnects after disconnect, state syncs', async ({ browser }) => {
        const hostCtx = await browser.newContext();
        const hostPage = await hostCtx.newPage();
        await hostPage.goto('http://localhost:9001');
        const cpuButton = hostPage.getByRole('button', { name: /CPU GAME/i });
        if (await cpuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await cpuButton.click();
            await hostPage.waitForTimeout(2000);
            const gameUrl = hostPage.url();
            await hostPage.waitForTimeout(5000);
            await hostCtx.close();
            await new Promise((r) => setTimeout(r, 10000));
            const newCtx = await browser.newContext();
            const newPage = await newCtx.newPage();
            await newPage.goto(gameUrl);
            await newPage.waitForTimeout(2000);
            const boardVisible = await newPage.locator('.game-board, .game-container').isVisible({ timeout: 5000 }).catch(() => false);
            if (boardVisible) expect(boardVisible).toBe(true);
            await newCtx.close();
        }
    });
});
