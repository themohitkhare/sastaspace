/**
 * Stress Testing Helpers - Multi-player setup and coordination
 */

import { expect } from '@playwright/test';

/**
 * Setup a multi-player game with host and additional players
 */
export async function setupGame(hostPage, ...playerPages) {
    await hostPage.goto('http://localhost:9001');
    await hostPage.getByRole('button', { name: /CREATE GAME/i }).click();
    await hostPage.waitForTimeout(1000);
    
    const gameUrl = hostPage.url();
    
    await hostPage.getByPlaceholder('ENTER_NAME').fill('Host');
    await hostPage.getByRole('button', { name: 'ENTER' }).click();
    await hostPage.waitForTimeout(1000);
    
    for (let i = 0; i < playerPages.length; i++) {
        await playerPages[i].goto(gameUrl);
        await playerPages[i].getByPlaceholder('ENTER_NAME').fill(`Player${i + 2}`);
        await playerPages[i].getByRole('button', { name: 'ENTER' }).click();
        await playerPages[i].waitForTimeout(1000);
    }
    
    await readyUp(hostPage);
    for (const page of playerPages) {
        await readyUp(page);
    }
    
    await expect(hostPage).toHaveURL(/\/game\//, { timeout: 30000 });
    
    return gameUrl;
}

/**
 * Setup a game with CPU players
 */
export async function setupGameWithCPU(page) {
    await page.goto('http://localhost:9001');
    
    const cpuButton = page.getByRole('button', { name: /CPU GAME/i });
    if (await cpuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await cpuButton.click();
        await page.waitForTimeout(2000);
        return true;
    }
    
    return false;
}

/**
 * Ready up a player
 */
export async function readyUp(page) {
    const launchKey = page.locator(
        'button[aria-label*="key"], button[aria-label*="Key"], .launch-key-container'
    ).first();
    
    if (await launchKey.isVisible({ timeout: 5000 }).catch(() => false)) {
        await launchKey.click();
        await page.waitForTimeout(1000);
    }
}

/**
 * Play a single turn step (roll, decide, end)
 */
export async function playTurnStep(page) {
    const isMyTurn = await page.getByText('YOUR TURN!')
        .isVisible({ timeout: 2000 })
        .catch(() => false);
    
    if (!isMyTurn) {
        return false;
    }
    
    const rollBtn = page.getByRole('button', { name: /ROLL/i });
    if (await rollBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await rollBtn.click();
        await page.waitForTimeout(1000);
    }
    
    const buyBtn = page.getByRole('button', { name: /BUY/i });
    const passBtn = page.getByRole('button', { name: /PASS/i });
    const leaveBtn = page.getByRole('button', { name: /LEAVE/i });
    
    if (await buyBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await buyBtn.click();
        await page.waitForTimeout(500);
    } else if (await passBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await passBtn.click();
        await page.waitForTimeout(500);
    } else if (await leaveBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await leaveBtn.click();
        await page.waitForTimeout(500);
    }
    
    const endBtn = page.getByRole('button', { name: /END TURN/i });
    if (await endBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await endBtn.click();
        await page.waitForTimeout(1000);
    }
    
    return true;
}

/**
 * Trigger an auction by playing until property landing and passing
 */
export async function triggerAuction(page) {
    let attempts = 0;
    
    while (attempts < 20) {
        const passBtn = page.getByRole('button', { name: /PASS/i });
        if (await passBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
            await passBtn.click();
            
            const auctionVisible = await page.getByText(/AUCTION|BIDDING/i)
                .isVisible({ timeout: 5000 })
                .catch(() => false);
            
            if (auctionVisible) return true;
        }
        
        await playTurnStep(page);
        attempts++;
    }
    return false;
}

/**
 * Propose a trade to another player
 */
export async function proposeTrade(page, targetPlayerName) {
    const tradeBtn = page.getByRole('button', { name: /TRADE|PROPOSE/i });
    if (await tradeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await tradeBtn.click();
        await page.waitForTimeout(1000);
        return true;
    }
    
    return false;
}

/**
 * Fetch game state via API
 */
export async function fetchGameState(gameId) {
    const response = await fetch(`http://localhost:8000/api/v1/games/${gameId}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch game state: ${response.status}`);
    }
    return await response.json();
}

/**
 * Get auction winner from game state
 */
export async function getAuctionWinner(page) {
    const winnerText = await page.locator('text=/won the auction|WINNER/i')
        .textContent({ timeout: 5000 })
        .catch(() => null);
    
    return winnerText;
}
