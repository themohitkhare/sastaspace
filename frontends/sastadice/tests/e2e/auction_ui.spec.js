import { test, expect } from '@playwright/test';

test.describe('Auction UI', () => {
    test('Auction Modal appears and handles interaction', async ({ page }) => {
        // 1. Setup mocks
        await page.route('**/sastadice/games*', async route => {
            const method = route.request().method();
            const url = route.request().url();

            if (method === 'POST' && !url.includes('action')) {
                // Create Game mock (POST /games)
                await route.fulfill({ json: { id: 'test-game-id' } });
            } else if (method === 'GET' && url.includes('test-game-id')) {
                // Get Game state mock
                const json = {
                    id: 'test-game-id',
                    status: 'ACTIVE',
                    turn_phase: 'AUCTION',
                    players: [
                        { id: 'p1', name: 'Host', cash: 1000 },
                        { id: 'p2', name: 'Other', cash: 1000 }
                    ],
                    current_turn_player_id: 'p1',
                    host_id: 'p1',
                    auction_state: {
                        property_id: 'prop-1',
                        highest_bid: 100,
                        highest_bidder_id: 'p2',
                        end_time: Date.now() / 1000 + 30, // 30s remaining
                        participants: ['p1', 'p2'],
                        min_bid_increment: 10
                    },
                    board: [
                        { id: 'prop-1', name: 'MUMBAY', color: 'RED', price: 200, type: 'PROPERTY' }
                    ],
                    settings: { enable_auctions: true }
                };
                await route.fulfill({ json });
            } else {
                await route.continue();
            }
        });

        // 2. Start at Home
        await page.goto('http://localhost:9001');

        // 3. Click Create Game to populate store
        // Ensure we select Create Game button
        await page.getByRole('button', { name: /> CREATE GAME/i }).click();

        // 4. Verify we land on game page
        // Lobby should redirect to Game because status is ACTIVE
        await expect(page).toHaveURL(/.*\/game\/test-game-id/, { timeout: 10000 });

        // 5. Verify Modal functionality
        await expect(page.getByText('🔨 AUCTION TIME')).toBeVisible();
        await expect(page.getByText('MUMBAY')).toBeVisible();
        await expect(page.getByText('$100')).toBeVisible(); // Current bid

        // 6. Verify Controls
        // We assume we are 'Host' (first player usually implies host if we just created)
        // Wait, HomePage create logic sets playerId in store based on response? 
        // Actually HomePage sets response.id as gameId. The PlayerId is usually generating or returned?
        // HomePage.jsx: 
        // setGame(res.data, 0)
        // setGameId(res.data.id)
        // "0" implies index 0 -> Player ID?
        // check UseGameStore logic: setGame(game, playerIndex) -> uses game.players[playerIndex].id
        // Since our mock response has players[0].id = 'p1', we will be 'p1'.

        const bidBtn = page.getByRole('button', { name: 'BID $110' }); // Min bid 100+10
        await expect(bidBtn).toBeVisible();

        // 7. Simulate Bid Click & Verify Request
        let bidRequestSent = false;
        await page.route('**/action', async route => {
            const postData = route.request().postDataJSON();
            if (postData.type === 'BID' && postData.payload.amount === 110) {
                bidRequestSent = true;
                await route.fulfill({ json: { success: true } });
            } else {
                await route.continue();
            }
        });

        await bidBtn.click();

        await expect(async () => {
            expect(bidRequestSent).toBeTruthy();
        }).toPass();
    });
});
