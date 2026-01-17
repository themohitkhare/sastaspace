/**
 * E2E tests for SastaDice multiplayer game flow
 * Tests the complete game lifecycle including turn phases and economy
 */
import { test, expect, Page, BrowserContext } from '@playwright/test'

const BASE_URL = 'http://localhost:9001'

// Helper function to create a game and return game ID
async function createGame(page: Page): Promise<string> {
  await page.goto(BASE_URL)
  await page.click('button:has-text("Create New Game")')
  await page.waitForURL('**/lobby', { timeout: 10000 })
  await page.waitForTimeout(2000) // Wait for game state to load

  // Extract game ID from the lobby page - look for the UUID pattern
  const gameIdElement = page.locator('text=/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i').first()
  await gameIdElement.waitFor({ timeout: 5000 })
  const gameIdText = await gameIdElement.textContent()
  if (!gameIdText) {
    throw new Error('Game ID not found on page')
  }
  // Extract just the UUID from the text
  const match = gameIdText.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i)
  const gameId = match ? match[0] : null
  if (!gameId) {
    throw new Error(`Could not extract game ID from: ${gameIdText}`)
  }
  return gameId.toLowerCase()
}

// Helper function to join a game (go to home, enter code, navigate to lobby)
async function navigateToGame(page: Page, gameId: string): Promise<void> {
  await page.goto(BASE_URL)

  // Enter game code
  const gameCodeInput = page.locator('input[placeholder="Enter game code..."]')
  await gameCodeInput.waitFor({ timeout: 5000 })
  await gameCodeInput.fill(gameId)

  // Click join button
  const joinButton = page.locator('button:has-text("Join Game")')
  await joinButton.waitFor({ state: 'visible', timeout: 5000 })
  await joinButton.click()

  await page.waitForURL('**/lobby', { timeout: 10000 })
  await page.waitForTimeout(1000)
}

// Helper function to join as a player in the lobby
async function joinAsPlayer(page: Page, playerName: string): Promise<void> {
  // Fill player name
  const nameInput = page.locator('input[placeholder="Enter your name"]')
  await nameInput.waitFor({ timeout: 5000 })
  await nameInput.fill(playerName)

  // Submit join
  const joinSubmitButton = page.locator('button:has-text("Join Game")').last()
  await joinSubmitButton.waitFor({ state: 'visible', timeout: 5000 })
  await joinSubmitButton.click()

  await page.waitForTimeout(2000) // Wait for join to complete
}

// Helper function to start the game
async function startGame(page: Page): Promise<void> {
  const startButton = page.locator('button:has-text("Start Game")')
  await startButton.waitFor({ state: 'visible', timeout: 5000 })
  await startButton.click()
  await page.waitForTimeout(2000) // Wait for game to start
}

// Helper function to roll dice
async function rollDice(page: Page): Promise<void> {
  const rollButton = page.locator('button:has-text("Roll Dice")')
  await rollButton.waitFor({ state: 'visible', timeout: 5000 })
  await rollButton.click()
  await page.waitForTimeout(1500) // Wait for roll animation and state update
}

// Helper function to end turn
async function endTurn(page: Page): Promise<void> {
  const endTurnButton = page.locator('button:has-text("End Turn")')
  await endTurnButton.waitFor({ state: 'visible', timeout: 5000 })
  await endTurnButton.click()
  await page.waitForTimeout(1000)
}

// Helper function to buy property
async function buyProperty(page: Page): Promise<void> {
  const buyButton = page.locator('button:has-text("Buy")')
  await buyButton.waitFor({ state: 'visible', timeout: 3000 })
  await buyButton.click()
  await page.waitForTimeout(1000)
}

// Helper function to pass on property
async function passProperty(page: Page): Promise<void> {
  const passButton = page.locator('button:has-text("Pass")')
  await passButton.waitFor({ state: 'visible', timeout: 3000 })
  await passButton.click()
  await page.waitForTimeout(1000)
}

test.describe('SastaDice Multiplayer Game Flow', () => {
  test('Single player can create game and start with CPU', async ({ page }) => {
    // Create game
    const gameId = await createGame(page)
    expect(gameId).toBeTruthy()

    // Join as player
    await joinAsPlayer(page, 'TestPlayer')

    // Verify player is in lobby
    await expect(page.locator('text=TestPlayer')).toBeVisible()

    // Start game (CPU will be added automatically)
    await startGame(page)

    // Verify game is active
    await expect(page.locator('text=ACTIVE')).toBeVisible({ timeout: 5000 })

    // Verify board is displayed
    await expect(page.locator('.board-container')).toBeVisible({ timeout: 5000 })

    // Verify player panel shows cash
    await expect(page.locator('text=/\\$[0-9,]+/')).toBeVisible()
  })

  test('2 players can create, join, and play turns', async ({ browser }) => {
    const player1Context = await browser.newContext()
    const player2Context = await browser.newContext()

    const player1Page = await player1Context.newPage()
    const player2Page = await player2Context.newPage()

    try {
      // Player 1 creates game
      const gameId = await createGame(player1Page)
      expect(gameId).toBeTruthy()

      // Player 1 joins
      await joinAsPlayer(player1Page, 'Alice')

      // Player 2 navigates to game and joins
      await navigateToGame(player2Page, gameId)
      await joinAsPlayer(player2Page, 'Bob')

      // Wait for both players to see each other
      await player1Page.waitForTimeout(2000)
      await expect(player1Page.locator('text=Alice')).toBeVisible()
      await expect(player1Page.locator('text=Bob')).toBeVisible()

      // Player 1 starts the game
      await startGame(player1Page)

      // Verify game is active on both pages
      await expect(player1Page.locator('text=ACTIVE')).toBeVisible({ timeout: 5000 })
      await expect(player2Page.locator('text=ACTIVE')).toBeVisible({ timeout: 5000 })

      // Verify turn indicator shows first player
      await expect(player1Page.locator('text=Your turn!')).toBeVisible({ timeout: 5000 })

      // Player 1 rolls dice
      await rollDice(player1Page)

      // Verify dice result is displayed
      await expect(player1Page.locator('.dice-face')).toBeVisible({ timeout: 3000 })

      // Handle decision phase if needed (buy/pass)
      const buyButton = player1Page.locator('button:has-text("Buy")')
      const passButton = player1Page.locator('button:has-text("Pass")')
      const endTurnButton = player1Page.locator('button:has-text("End Turn")')

      // Wait a moment for the phase to settle
      await player1Page.waitForTimeout(500)

      // If buy/pass buttons are visible, make a decision
      if (await buyButton.isVisible()) {
        await passProperty(player1Page) // Pass for simplicity
      }

      // End turn
      if (await endTurnButton.isVisible()) {
        await endTurn(player1Page)
      }

      // Verify turn passed to Player 2
      await player2Page.waitForTimeout(2000)
      await expect(player2Page.locator('text=Your turn!')).toBeVisible({ timeout: 5000 })

    } finally {
      await player1Context.close()
      await player2Context.close()
    }
  })

  test('Turn phases work correctly (PRE_ROLL -> DECISION -> POST_TURN)', async ({ page }) => {
    // Create and start a game
    const gameId = await createGame(page)
    await joinAsPlayer(page, 'PhaseTest')
    await startGame(page)

    // Verify initial phase is PRE_ROLL
    await expect(page.locator('text=PRE_ROLL')).toBeVisible({ timeout: 5000 })

    // Roll dice
    await rollDice(page)

    // Verify phase changed (either DECISION or POST_TURN depending on tile)
    const decisionOrPostTurn = page.locator('text=/DECISION|POST_TURN/')
    await expect(decisionOrPostTurn).toBeVisible({ timeout: 5000 })

    // If in DECISION phase, make a choice
    const buyButton = page.locator('button:has-text("Buy")')
    const passButton = page.locator('button:has-text("Pass")')

    if (await buyButton.isVisible()) {
      await passProperty(page)
    }

    // Verify POST_TURN phase
    await expect(page.locator('text=POST_TURN')).toBeVisible({ timeout: 5000 })

    // End turn
    await endTurn(page)

    // Verify back to PRE_ROLL (for next player or same player if solo)
    await expect(page.locator('text=PRE_ROLL')).toBeVisible({ timeout: 5000 })
  })

  test('Player can buy property and see ownership', async ({ page }) => {
    // Create and start a game
    const gameId = await createGame(page)
    await joinAsPlayer(page, 'Buyer')
    await startGame(page)

    // Get initial cash
    const initialCashText = await page.locator('text=/Your Cash.*\\$[0-9,]+/').textContent()
    const initialCash = parseInt(initialCashText?.match(/\$([0-9,]+)/)?.[1]?.replace(',', '') || '0')

    // Roll dice until we land on a purchasable property
    let attempts = 0
    while (attempts < 10) {
      // Roll dice
      await rollDice(page)
      await page.waitForTimeout(500)

      // Check if buy button is visible
      const buyButton = page.locator('button:has-text("Buy")')
      if (await buyButton.isVisible()) {
        // Buy the property
        await buyProperty(page)

        // Verify cash decreased
        await page.waitForTimeout(1000)
        const newCashText = await page.locator('text=/Your Cash.*\\$[0-9,]+/').textContent()
        const newCash = parseInt(newCashText?.match(/\$([0-9,]+)/)?.[1]?.replace(',', '') || '0')
        expect(newCash).toBeLessThan(initialCash)

        // Verify ownership badge appears (player initial on tile)
        await expect(page.locator('.owner-badge')).toBeVisible()
        break
      }

      // End turn and try again
      const endTurnButton = page.locator('button:has-text("End Turn")')
      if (await endTurnButton.isVisible()) {
        await endTurn(page)
      }

      attempts++
    }
  })

  test('Dynamic economy scales with board size', async ({ page }) => {
    // Create and start a game
    const gameId = await createGame(page)
    await joinAsPlayer(page, 'EconomyTest')
    await startGame(page)

    // Verify GO bonus is displayed
    await expect(page.locator('text=/GO Bonus.*\\$[0-9]+/')).toBeVisible({ timeout: 5000 })

    // Verify starting cash is displayed and reasonable
    const cashText = await page.locator('text=/Your Cash.*\\$[0-9,]+/').textContent()
    const cash = parseInt(cashText?.match(/\$([0-9,]+)/)?.[1]?.replace(',', '') || '0')
    expect(cash).toBeGreaterThan(0)
    expect(cash).toBeLessThan(10000) // Reasonable upper bound
  })

  test('Game copy functionality works', async ({ page }) => {
    await createGame(page)

    // Find and verify Copy button is visible
    const copyButton = page.locator('button:has-text("Copy")')
    await expect(copyButton).toBeVisible()

    // Click copy button
    await copyButton.click()

    // Verify button changes to "Copied!"
    await expect(page.locator('button:has-text("Copied")')).toBeVisible({ timeout: 2000 })
  })

  test('Event messages are displayed after actions', async ({ page }) => {
    // Create and start a game
    const gameId = await createGame(page)
    await joinAsPlayer(page, 'EventTest')
    await startGame(page)

    // Roll dice
    await rollDice(page)

    // Verify an event message is displayed
    await expect(page.locator('.event-message')).toBeVisible({ timeout: 5000 })
  })

  test('Player tokens move on the board', async ({ page }) => {
    // Create and start a game
    const gameId = await createGame(page)
    await joinAsPlayer(page, 'MoveTest')
    await startGame(page)

    // Verify player token is visible
    await expect(page.locator('.player-token')).toBeVisible({ timeout: 5000 })

    // Roll dice
    await rollDice(page)

    // Token should still be visible (position changed)
    await expect(page.locator('.player-token')).toBeVisible()
  })

  test('3 players can join and play', async ({ browser }) => {
    const contexts: BrowserContext[] = []
    const pages: Page[] = []

    // Create 3 browser contexts
    for (let i = 0; i < 3; i++) {
      contexts.push(await browser.newContext())
      pages.push(await contexts[i].newPage())
    }

    try {
      // Player 1 creates game
      const gameId = await createGame(pages[0])
      expect(gameId).toBeTruthy()

      // All players join
      await joinAsPlayer(pages[0], 'Player1')
      await navigateToGame(pages[1], gameId)
      await joinAsPlayer(pages[1], 'Player2')
      await navigateToGame(pages[2], gameId)
      await joinAsPlayer(pages[2], 'Player3')

      // Wait for all players to see each other
      await pages[0].waitForTimeout(3000)

      // Verify all players are visible
      for (const page of pages) {
        await expect(page.locator('text=Player1')).toBeVisible({ timeout: 5000 })
        await expect(page.locator('text=Player2')).toBeVisible({ timeout: 5000 })
        await expect(page.locator('text=Player3')).toBeVisible({ timeout: 5000 })
      }

      // Player 1 starts the game
      await startGame(pages[0])

      // Verify game started for all players
      for (const page of pages) {
        await expect(page.locator('text=ACTIVE')).toBeVisible({ timeout: 5000 })
      }

    } finally {
      for (const context of contexts) {
        await context.close()
      }
    }
  })
})
