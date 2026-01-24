/**
 * Chaos Testing Helpers
 * 
 * Shared utilities for monkey testing and stress testing
 */

/**
 * Create a game via API
 */
export async function createGameViaAPI(cpuCount = 0) {
    const response = await fetch('http://localhost:8000/api/v1/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cpu_count: cpuCount })
    });
    
    if (!response.ok) {
        throw new Error(`Failed to create game: ${response.status}`);
    }
    
    const data = await response.json();
    return data.id;
}

/**
 * Join a game
 */
export async function joinGame(page, gameId, playerName) {
    await page.goto(`http://localhost:9001/lobby/${gameId}`);
    await page.getByPlaceholder('ENTER_NAME').fill(playerName);
    await page.getByRole('button', { name: 'ENTER' }).click();
    await page.waitForTimeout(1000);
}

/**
 * Ready up player
 */
export async function readyUp(page) {
    const launchKey = page.locator('button[aria-label*="key"], button[aria-label*="Key"], .launch-key-container').first();
    await launchKey.click();
    await page.waitForTimeout(1000);
}

/**
 * Wait for game to start
 */
export async function waitForGameStart(page, timeout = 30000) {
    return await page.waitForURL(/\/game\//, { timeout });
}

/**
 * Get all clickable game actions
 */
export async function getClickableActions(page) {
    return await page.locator(
        'button:visible:not([disabled]):not([aria-hidden="true"])'
    ).all();
}

/**
 * Perform random action
 */
export async function performRandomAction(page) {
    const actions = await getClickableActions(page);
    
    if (actions.length === 0) {
        return null;
    }

    const chosen = actions[Math.floor(Math.random() * actions.length)];
    const label = await chosen.textContent().catch(() => 'Unknown');
    
    try {
        await chosen.click();
        return label;
    } catch (e) {
        return null;
    }
}

/**
 * Check if game is over
 */
export async function isGameOver(page) {
    return await page.locator('text=/GAME OVER|WINNER|VICTORY/i')
        .isVisible({ timeout: 1000 })
        .catch(() => false);
}

/**
 * Monitor console for errors
 */
export function setupConsoleMonitoring(page) {
    const errors = [];
    const warnings = [];
    const desyncErrors = [];

    page.on('console', msg => {
        const text = msg.text();
        
        if (msg.type() === 'error') {
            errors.push({ time: Date.now(), message: text });
        } else if (msg.type() === 'warning') {
            warnings.push({ time: Date.now(), message: text });
        }

        if (text.includes('DESYNC') || text.includes('phase mismatch')) {
            desyncErrors.push({ time: Date.now(), message: text });
        }
    });

    page.on('pageerror', error => {
        errors.push({ time: Date.now(), message: error.message });
    });

    return {
        getErrors: () => errors,
        getWarnings: () => warnings,
        getDesyncErrors: () => desyncErrors,
        hasDesyncErrors: () => desyncErrors.length > 0
    };
}

/**
 * Retry an action with exponential backoff
 */
export async function retryWithBackoff(fn, maxRetries = 3, initialDelay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (e) {
            if (i === maxRetries - 1) {
                throw e;
            }
            const delay = initialDelay * Math.pow(2, i);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

/**
 * Generate random game settings
 */
export function generateRandomSettings() {
    const winConditions = ['SUDDEN_DEATH', 'LAST_STANDING', 'FIRST_TO_CASH'];
    const chaosLevels = ['CHILL', 'NORMAL', 'CHAOS'];
    
    return {
        win_condition: winConditions[Math.floor(Math.random() * winConditions.length)],
        round_limit: Math.floor(Math.random() * 50) + 15,
        chaos_level: chaosLevels[Math.floor(Math.random() * chaosLevels.length)],
        starting_cash_multiplier: 0.5 + Math.random() * 2.5,
        go_bonus_base: 150 + Math.floor(Math.random() * 200)
    };
}

/**
 * Wait for element with timeout
 */
export async function waitForElement(page, selector, timeout = 5000) {
    return await page.locator(selector).waitFor({ timeout, state: 'visible' });
}

/**
 * Safe click - clicks only if element is visible and enabled
 */
export async function safeClick(page, selector, timeout = 3000) {
    try {
        const element = page.locator(selector);
        await element.waitFor({ timeout, state: 'visible' });
        
        const isEnabled = await element.isEnabled();
        if (isEnabled) {
            await element.click();
            return true;
        }
    } catch (e) {
        return false;
    }
    return false;
}

/**
 * Take screenshot on failure
 */
export async function screenshotOnFailure(page, testName) {
    const timestamp = Date.now();
    const filename = `./test-results/failure-${testName}-${timestamp}.png`;
    
    try {
        await page.screenshot({ path: filename, fullPage: true });
        console.log(`Screenshot saved: ${filename}`);
    } catch (e) {
        console.log(`Failed to take screenshot: ${e.message}`);
    }
}

/**
 * Get game state via API
 */
export async function getGameState(gameId) {
    const response = await fetch(`http://localhost:8000/api/v1/games/${gameId}`);
    
    if (!response.ok) {
        throw new Error(`Failed to get game state: ${response.status}`);
    }
    
    return await response.json();
}

/**
 * Verify game state consistency
 */
export async function verifyGameStateConsistency(gameId) {
    const state = await getGameState(gameId);
    const issues = [];

    // Check player count
    if (state.players.length < 2 || state.players.length > 8) {
        issues.push(`Invalid player count: ${state.players.length}`);
    }

    // Check board size
    if (state.board.length < 10) {
        issues.push(`Invalid board size: ${state.board.length}`);
    }

    // Check current player
    if (state.status === 'ACTIVE' && !state.current_turn_player_id) {
        issues.push('Active game has no current player');
    }

    // Check player cash
    for (const player of state.players) {
        if (player.cash < 0 && !player.is_bankrupt) {
            issues.push(`Player ${player.name} has negative cash but not bankrupt`);
        }
    }

    return {
        valid: issues.length === 0,
        issues
    };
}
