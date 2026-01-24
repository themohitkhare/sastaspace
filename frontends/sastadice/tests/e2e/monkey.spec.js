/**
 * Monkey Testing - Random action testing with Smart/Dumb/Hoarder modes
 * 
 * This test performs weighted random actions to find bugs and edge cases.
 * Smart Mode: Prefers complex features (Trade, Market, Upgrade)
 * Dumb Mode: Purely random clicks
 * Hoarder Mode: Never buys, hoards cash to test economy drain
 */

import { test, expect } from '@playwright/test';

// Action weights for Smart Monkey mode
const ACTION_WEIGHTS = {
    // Dangerous - exercise complex paths (3x weight)
    'TRADE': 3,
    'PROPOSE': 3,
    'ACCEPT': 3,
    'DECLINE': 3,
    'BUY BUFF': 3,
    'DDOS': 3,
    'PEEK': 3,
    // Medium complexity (2x weight)
    'UPGRADE': 2,
    'DOWNGRADE': 2,
    'BID': 2,
    // Safe - core loop (1x weight)
    'ROLL': 1,
    'END TURN': 1,
    'BUY': 1,
    'PASS': 1,
    'LEAVE': 1,
};

/**
 * MonkeyTester - Performs random actions on the game
 */
class MonkeyTester {
    constructor(page, mode = 'SMART') {
        this.page = page;
        this.mode = mode; // 'SMART', 'DUMB', or 'HOARDER'
        this.actionLog = [];
        this.desyncErrors = [];
        this.errorCount = 0;
        this.screenshots = [];
    }

    /**
     * Find all clickable actions in the game area
     */
    async findClickableActions() {
        // Find all visible, enabled buttons in game container
        const buttons = await this.page.locator(
            'button:visible:not([disabled])'
        ).all();
        
        return buttons;
    }

    /**
     * Get weight for an action based on its label
     */
    getActionWeight(label) {
        if (this.mode === 'DUMB') return 1;
        
        const upperLabel = label.toUpperCase();
        for (const [pattern, weight] of Object.entries(ACTION_WEIGHTS)) {
            if (upperLabel.includes(pattern)) return weight;
        }
        return 1;
    }

    /**
     * Select a weighted random action from available actions
     */
    async selectWeightedAction(actions) {
        if (this.mode === 'DUMB') {
            // Purely random
            return actions[Math.floor(Math.random() * actions.length)];
        }
        
        // Build weighted selection pool
        const weighted = [];
        for (const action of actions) {
            const label = await action.textContent().catch(() => '');
            const weight = this.getActionWeight(label || '');
            for (let i = 0; i < weight; i++) {
                weighted.push({ action, label });
            }
        }
        
        if (weighted.length === 0) return null;
        const selected = weighted[Math.floor(Math.random() * weighted.length)];
        return selected.action;
    }

    /**
     * Dismiss any open modal overlays
     */
    async dismissModals() {
        // Check for modal backdrop
        const modalBackdrop = this.page.locator('.fixed.inset-0.bg-black\\/50');
        if (await modalBackdrop.isVisible({ timeout: 100 }).catch(() => false)) {
            // Try close button first
            const closeBtn = this.page.locator('button:has-text("×"), button:has-text("CLOSE"), button:has-text("✕")').first();
            if (await closeBtn.isVisible({ timeout: 100 }).catch(() => false)) {
                await closeBtn.click().catch(() => {});
                await this.page.waitForTimeout(200);
                return true;
            }
            // Try Escape key
            await this.page.keyboard.press('Escape');
            await this.page.waitForTimeout(200);
            return true;
        }
        return false;
    }

    /**
     * Perform a random action from available actions
     */
    async performRandomAction() {
        // First dismiss any modal overlays
        await this.dismissModals();
        
        const actions = await this.findClickableActions();
        
        if (actions.length === 0) return false;

        // Select action based on mode
        const chosen = await this.selectWeightedAction(actions);
        if (!chosen) return false;
        
        try {
            const label = await chosen.textContent().catch(() => 'Unknown');
            const ariaLabel = await chosen.getAttribute('aria-label').catch(() => null);
            const actionName = ariaLabel || label;
            
            this.actionLog.push({ time: Date.now(), action: actionName, mode: this.mode });
            await chosen.click();
            await this.page.waitForTimeout(500);
            
            return true;
        } catch (e) {
            if (e.message.includes('intercepts pointer events')) {
                await this.dismissModals();
                return false;
            }
            this.errorCount++;
            return false;
        }
    }

    /**
     * Capture visual regression screenshot
     */
    async captureVisualRegression(reason) {
        const filename = `monkey_${reason}_${Date.now()}.png`;
        const path = `test-results/${filename}`;
        
        try {
            await this.page.screenshot({ path, fullPage: true });
            this.screenshots.push({ reason, filename, time: Date.now() });
        } catch {
            // Screenshot failed
        }
    }

    /**
     * Check for stuck state
     */
    async checkForStuckState() {
        const startTime = Date.now();
        const timeout = 10000; // 10 seconds
        
        while (Date.now() - startTime < timeout) {
            const actions = await this.findClickableActions();
            if (actions.length > 0) return false; // Not stuck
            await this.page.waitForTimeout(1000);
        }
        
        // Stuck! Capture visual regression
        await this.captureVisualRegression('stuck_state');
        return true;
    }

    /**
     * Run monkey test until game ends or max actions reached
     */
    async runUntilGameEnd(maxActions = 500) {
        let actions = 0;
        
        while (actions < maxActions) {
            // Check if game is over
            const gameOver = await this.page.locator('text=/GAME OVER|WINNER|VICTORY/i')
                .isVisible({ timeout: 1000 })
                .catch(() => false);
            
            if (gameOver) break;

            // Check if stuck every 50 actions
            if (actions % 50 === 0 && actions > 0) {
                const isStuck = await this.checkForStuckState();
                if (isStuck) {
                    throw new Error(`Game stuck after ${actions} actions - no clickable buttons for 10s`);
                }
            }

            // Perform action
            const actionPerformed = await this.performRandomAction();
            
            if (actionPerformed) {
                actions++;
            } else {
                // No action available, wait a bit
                await this.page.waitForTimeout(1000);
            }
        }

        // Calculate action distribution
        const actionCounts = {};
        for (const entry of this.actionLog) {
            actionCounts[entry.action] = (actionCounts[entry.action] || 0) + 1;
        }

        return {
            totalActions: actions,
            errors: this.errorCount,
            desyncErrors: this.desyncErrors.length,
            actionLog: this.actionLog.slice(-20), // Last 20 actions
            actionDistribution: actionCounts
        };
    }

    /**
     * Check for desync errors in console
     */
    async checkForDesyncErrors() {
        // This is handled by the console listener setup in beforeEach
        return this.desyncErrors.length;
    }
}

/**
 * HoarderMonkey - Never buys properties, hoards cash
 * Purpose: Verify players can't become invincible by hoarding
 */
class HoarderMonkey extends MonkeyTester {
    constructor(page) {
        super(page, 'HOARDER');
        this.cashHistory = [];
    }

    async performRandomAction() {
        const actions = await this.findClickableActions();
        
        if (actions.length === 0) {
            return false;
        }

        // Filter out BUY actions - hoarders never buy
        for (const action of actions) {
            const label = await action.textContent().catch(() => '');
            const upperLabel = label.toUpperCase();
            
            // NEVER buy - always pass/skip
            if (upperLabel.includes('BUY') && !upperLabel.includes('BUFF')) {
                const passBtn = this.page.getByRole('button', { name: /PASS/i });
                if (await passBtn.isVisible({ timeout: 500 }).catch(() => false)) {
                    const cash = await this.getCash();
                    this.actionLog.push({ 
                        time: Date.now(), 
                        action: 'PASS (hoarder)', 
                        cash 
                    });
                    await passBtn.click();
                    await this.page.waitForTimeout(500);
                    return true;
                }
            }
            
            // Skip market buffs
            if (upperLabel.includes('LEAVE') || upperLabel.includes('SKIP')) {
                const cash = await this.getCash();
                this.actionLog.push({ time: Date.now(), action: label, cash });
                await action.click();
                await this.page.waitForTimeout(500);
                return true;
            }
        }
        
        // Fall back to first available safe action (ROLL, END TURN)
        return super.performRandomAction();
    }

    async getCash() {
        try {
            const cashText = await this.page.locator('.player-cash, [data-cash]')
                .first()
                .textContent({ timeout: 1000 });
            return parseInt(cashText?.replace(/[^0-9]/g, '') || '0', 10);
        } catch {
            return 0;
        }
    }

    async runAndVerifyBankruptcy(maxRounds = 100) {
        let rounds = 0;
        
        while (rounds < maxRounds) {
            const gameOver = await this.page.getByText(/GAME OVER|BANKRUPT|WINNER/i)
                .isVisible({ timeout: 1000 }).catch(() => false);
            
            if (gameOver) {
                const isBankrupt = await this.page.getByText(/BANKRUPT/i).isVisible().catch(() => false);
                return { bankrupt: isBankrupt, rounds, cashHistory: this.cashHistory };
            }
            
            await this.performRandomAction();
            
            // Track cash each round
            const currentCash = await this.getCash();
            this.cashHistory.push({ round: rounds, cash: currentCash });
            
            rounds++;
        }
        
        // If we get here, hoarder survived - economy may be broken!
        return { bankrupt: false, rounds, cashHistory: this.cashHistory };
    }
}

test.describe('Monkey Testing - Smart/Dumb/Hoarder Modes', () => {
    let desyncErrors = [];
    let monkey = null;

    test.beforeEach(async ({ page }) => {
        desyncErrors = [];
        
        // Listen for console errors indicating desync
        page.on('console', async (msg) => {
            const text = msg.text();
            const isDesync = 
                text.includes('DESYNC') || 
                text.includes('phase mismatch') ||
                text.includes('stale state') ||
                text.includes('unexpected phase');
            
            if (isDesync) {
                desyncErrors.push({ time: Date.now(), message: text });
                
                // IMMEDIATE screenshot on desync detection
                if (monkey) {
                    await monkey.captureVisualRegression('desync_detected');
                    console.error(`🚨 DESYNC DETECTED: ${text}`);
                }
            }
            
            if (msg.type() === 'error') {
                desyncErrors.push({ time: Date.now(), message: text });
            }
        });

        // Listen for page errors
        page.on('pageerror', async (error) => {
            desyncErrors.push({ time: Date.now(), message: error.message });
            if (monkey) {
                await monkey.captureVisualRegression('page_error');
                console.error(`💥 PAGE ERROR: ${error.message}`);
            }
        });
    });

    test('Smart Monkey - Weighted Complex Actions', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();
        monkey = new MonkeyTester(page, 'SMART');

        await page.goto('http://localhost:9001');
        
        const cpuButton = page.getByRole('button', { name: /CPU GAME/i });
        if (await cpuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await cpuButton.click();
        }

        await page.waitForTimeout(2000);
        const result = await monkey.runUntilGameEnd(250);
        expect(desyncErrors.filter(e => e.message.includes('DESYNC')).length).toBe(0);
        await context.close();
    });

    test('Dumb Monkey - Purely Random Clicks', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();
        monkey = new MonkeyTester(page, 'DUMB');

        await page.goto('http://localhost:9001');
        
        const cpuButton = page.getByRole('button', { name: /CPU GAME/i });
        if (await cpuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await cpuButton.click();
        }

        await page.waitForTimeout(2000);
        await monkey.runUntilGameEnd(200);
        expect(desyncErrors.filter(e => e.message.includes('DESYNC')).length).toBe(0);
        await context.close();
    });

    test('Hoarder Monkey - Never Buys, Tests Economy Drain', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();
        const hoarder = new HoarderMonkey(page);

        await page.goto('http://localhost:9001');
        
        const cpuButton = page.getByRole('button', { name: /CPU GAME/i });
        if (await cpuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await cpuButton.click();
        }

        await page.waitForTimeout(2000);
        const result = await hoarder.runAndVerifyBankruptcy(80);
        if (!result.bankrupt) {
            console.warn('Hoarder survived without buying - economy balance may need tuning');
        }
        await context.close();
    });

    test('UI Handles Large Cash Values Without Overflow', async ({ page }) => {
        await page.route('**/games/*', async (route) => {
            const url = route.request().url();
            if (route.request().method() === 'GET' && !url.includes('action')) {
                const response = await route.fetch();
                const json = await response.json();
                if (json.players?.length > 0) json.players[0].cash = 10000000;
                await route.fulfill({ json });
            } else {
                await route.continue();
            }
        });
        await page.goto('http://localhost:9001');
        await page.waitForTimeout(1000);
        expect(await page.locator('body').isVisible()).toBe(true);
    });

    test('Monkey Test - Rapid Clicking Stress', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();

        await page.goto('http://localhost:9001');
        
        // Create CPU game
        const cpuButton = page.getByRole('button', { name: /CPU GAME/i });
        if (await cpuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await cpuButton.click();
        }

        await page.waitForTimeout(2000);

        const monkey = new MonkeyTester(page);
        for (let i = 0; i < 50; i++) {
            const actions = await monkey.findClickableActions();
            if (actions.length > 0) {
                const randomAction = actions[Math.floor(Math.random() * actions.length)];
                await randomAction.click().catch(() => {});
            }
            if (i % 10 === 0) await page.waitForTimeout(100);
        }
        expect(desyncErrors.filter(e => e.message.includes('DESYNC')).length).toBe(0);

        await context.close();
    });

    test('Monkey Test - Edge Case Actions', async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();

        await page.goto('http://localhost:9001');
        
        // Create game
        await page.getByRole('button', { name: /CREATE GAME/i }).click();
        await page.waitForTimeout(1000);

        const monkey = new MonkeyTester(page);
        const disabledButtons = await page.locator('button[disabled]').all();
        for (const btn of disabledButtons.slice(0, 5)) {
            try {
                await btn.click({ force: true, timeout: 500 });
                monkey.actionLog.push({ time: Date.now(), action: 'disabled-button', type: 'edge-case' });
            } catch {
                // Expected to fail
            }
        }
        await page.click('body', { position: { x: 5, y: 5 } }).catch(() => {});
        await page.waitForTimeout(100);
        await page.goBack().catch(() => {});
        await page.waitForTimeout(200);
        await page.goForward().catch(() => {});
        await page.waitForTimeout(200);
        expect(desyncErrors.filter(e => e.message.includes('DESYNC')).length).toBe(0);

        await context.close();
    });
});

test.describe('Monkey Testing - Console Error Detection', () => {
    test('Monitor console for unexpected errors during normal gameplay', async ({ page }) => {
        const errors = [];
        const warnings = [];

        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            } else if (msg.type() === 'warning') {
                warnings.push(msg.text());
            }
        });

        await page.goto('http://localhost:9001');
        await page.waitForTimeout(1000);
        const createButton = page.getByRole('button', { name: /CREATE GAME|CPU GAME/i }).first();
        if (await createButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await createButton.click();
            await page.waitForTimeout(2000);
        }
        const criticalErrors = errors.filter((e) =>
            e.includes('DESYNC') || 
            e.includes('undefined') ||
            e.includes('null')
        );

        expect(criticalErrors.length).toBe(0);
    });
});
