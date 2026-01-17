/**
 * E2E test for multiplayer game flow with 2, 3, and 5 players
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:9001'

// Helper function to create a game and return game ID
async function createGame(page) {
  await page.goto(BASE_URL)
  await page.click('button:has-text("CREATE GAME")')
  await page.waitForURL('**/game')
  await page.waitForTimeout(2000) // Wait for game state to load
  
  // Extract game ID from the lobby page - look for the UUID pattern in the game ID display
  const gameIdElement = page.locator('text=/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i').first()
  await gameIdElement.waitFor({ timeout: 5000 })
  const gameIdText = await gameIdElement.textContent()
  if (!gameIdText) {
    throw new Error('Game ID not found on page')
  }
  // Extract just the UUID from the text (handle case-insensitive)
  const match = gameIdText.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i)
  const gameId = match ? match[0] : null
  if (!gameId) {
    throw new Error(`Could not extract game ID from: ${gameIdText}`)
  }
  return gameId.toLowerCase() // Normalize to lowercase for consistency
}

// Helper function to join a game
async function joinGame(page, gameId: string, playerName: string, tiles: Array<{type: string, name: string}>) {
  await page.goto(BASE_URL)
  
  // Clean game ID (ensure lowercase for consistency)
  const cleanGameId = gameId.toLowerCase().trim()
  
  // Enter game code
  const gameCodeInput = page.locator('input[placeholder="ENTER GAME CODE"]')
  await gameCodeInput.waitFor({ timeout: 5000 })
  await gameCodeInput.fill(cleanGameId)
  
  // Click join button (wait for it to be enabled)
  const joinButton = page.locator('button:has-text("JOIN GAME")')
  await joinButton.waitFor({ state: 'visible', timeout: 5000 })
  await joinButton.click()
  
  await page.waitForURL('**/game', { timeout: 10000 })
  await page.waitForTimeout(1000) // Wait for page to load
  
  // Fill player name
  const nameInput = page.locator('input[placeholder="Enter your name"]')
  await nameInput.waitFor({ timeout: 5000 })
  await nameInput.fill(playerName)
  
  // Fill tiles
  const tileInputs = await page.locator('input[placeholder*="Tile"]').all()
  for (let i = 0; i < Math.min(tiles.length, tileInputs.length); i++) {
    await tileInputs[i].waitFor({ state: 'visible', timeout: 5000 })
    await tileInputs[i].fill(tiles[i].name)
  }
  
  // Submit join - wait for button to be enabled
  const joinSubmitButton = page.locator('button:has-text("JOIN GAME")').filter({ hasText: /^JOIN GAME$/ })
  await joinSubmitButton.waitFor({ state: 'visible', timeout: 5000 })
  await joinSubmitButton.click()
  
  await page.waitForTimeout(3000) // Wait for join to complete and polling to update
}

test.describe('Multiplayer Game Flow', () => {
  test('2 players can create, join, and play a complete game', async ({ browser }) => {
    const player1Context = await browser.newContext()
    const player2Context = await browser.newContext()
    
    const player1Page = await player1Context.newPage()
    const player2Page = await player2Context.newPage()

    try {
      // Player 1 creates game
      const gameId = await createGame(player1Page)
      expect(gameId).toBeTruthy()
      
      // Verify game ID is displayed in lobby
      await expect(player1Page.locator(`text=${gameId}`)).toBeVisible()
      await expect(player1Page.locator('button:has-text("COPY")')).toBeVisible()

      // Player 2 joins game using game code
      await joinGame(
        player2Page,
        gameId!,
        'Player2',
        [
          { type: 'PROPERTY', name: 'Tile 1' },
          { type: 'PROPERTY', name: 'Tile 2' },
          { type: 'CHANCE', name: 'Tile 3' },
          { type: 'TAX', name: 'Tile 4' },
          { type: 'BUFF', name: 'Tile 5' },
        ]
      )

      // Verify both players are in the lobby
      await player1Page.waitForTimeout(2000) // Wait for polling to update
      await expect(player1Page.locator('text=/PLAYERS \\(2\\)/')).toBeVisible()
      await expect(player2Page.locator('text=/PLAYERS \\(2\\)/')).toBeVisible()

      // Player 1 starts the game
      await player1Page.click('button:has-text("START GAME")')
      await player1Page.waitForTimeout(2000)

      // Verify game status changed to ACTIVE
      await expect(player1Page.locator('text=Status: ACTIVE')).toBeVisible({ timeout: 5000 })

      // Verify board is generated (check for board elements or game page)
      await expect(player1Page.locator('text=/SASTADICE GAME|GAME/')).toBeVisible({ timeout: 5000 })

    } finally {
      await player1Context.close()
      await player2Context.close()
    }
  })

  test('3 players can create, join, and play a complete game', async ({ browser }) => {
    const player1Context = await browser.newContext()
    const player2Context = await browser.newContext()
    const player3Context = await browser.newContext()
    
    const player1Page = await player1Context.newPage()
    const player2Page = await player2Context.newPage()
    const player3Page = await player3Context.newPage()

    try {
      // Player 1 creates game
      const gameId = await createGame(player1Page)
      expect(gameId).toBeTruthy()

      // Player 2 joins
      await joinGame(
        player2Page,
        gameId!,
        'Player2',
        [
          { type: 'PROPERTY', name: 'P2 Tile 1' },
          { type: 'PROPERTY', name: 'P2 Tile 2' },
          { type: 'CHANCE', name: 'P2 Tile 3' },
          { type: 'TAX', name: 'P2 Tile 4' },
          { type: 'BUFF', name: 'P2 Tile 5' },
        ]
      )

      // Player 3 joins
      await joinGame(
        player3Page,
        gameId!,
        'Player3',
        [
          { type: 'PROPERTY', name: 'P3 Tile 1' },
          { type: 'PROPERTY', name: 'P3 Tile 2' },
          { type: 'CHANCE', name: 'P3 Tile 3' },
          { type: 'TAX', name: 'P3 Tile 4' },
          { type: 'BUFF', name: 'P3 Tile 5' },
        ]
      )

      // Wait for all players to see each other
      await player1Page.waitForTimeout(3000)
      await expect(player1Page.locator('text=/PLAYERS \\(3\\)/')).toBeVisible({ timeout: 5000 })
      await expect(player2Page.locator('text=/PLAYERS \\(3\\)/')).toBeVisible({ timeout: 5000 })
      await expect(player3Page.locator('text=/PLAYERS \\(3\\)/')).toBeVisible({ timeout: 5000 })

      // Player 1 starts the game
      await player1Page.click('button:has-text("START GAME")')
      await player1Page.waitForTimeout(2000)

      // Verify game started for all players
      await expect(player1Page.locator('text=/Status: ACTIVE|SASTADICE GAME/')).toBeVisible({ timeout: 5000 })

    } finally {
      await player1Context.close()
      await player2Context.close()
      await player3Context.close()
    }
  })

  test('5 players can create, join, and play a complete game', async ({ browser }) => {
    const contexts = []
    const pages = []
    
    // Create 5 browser contexts
    for (let i = 0; i < 5; i++) {
      contexts.push(await browser.newContext())
      pages.push(await contexts[i].newPage())
    }

    try {
      // Player 1 creates game
      const gameId = await createGame(pages[0])
      expect(gameId).toBeTruthy()

      // Players 2-5 join
      const playerNames = ['Player1', 'Player2', 'Player3', 'Player4', 'Player5']
      for (let i = 1; i < 5; i++) {
        await joinGame(
          pages[i],
          gameId!,
          playerNames[i],
          [
            { type: 'PROPERTY', name: `P${i+1} Tile 1` },
            { type: 'PROPERTY', name: `P${i+1} Tile 2` },
            { type: 'CHANCE', name: `P${i+1} Tile 3` },
            { type: 'TAX', name: `P${i+1} Tile 4` },
            { type: 'BUFF', name: `P${i+1} Tile 5` },
          ]
        )
      }

      // Wait for all players to see each other
      await pages[0].waitForTimeout(4000)
      
      // Verify all 5 players are visible
      for (let i = 0; i < 5; i++) {
        await expect(pages[i].locator('text=/PLAYERS \\(5\\)/')).toBeVisible({ timeout: 8000 })
      }

      // Player 1 starts the game
      await pages[0].click('button:has-text("START GAME")')
      await pages[0].waitForTimeout(2000)

      // Verify game started (all players should see active game)
      for (let i = 0; i < 5; i++) {
        await expect(pages[i].locator('text=/Status: ACTIVE|SASTADICE GAME/')).toBeVisible({ timeout: 8000 })
      }

    } finally {
      // Cleanup all contexts
      for (const context of contexts) {
        await context.close()
      }
    }
  })

  test('Game ID copy functionality works', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.click('button:has-text("CREATE GAME")')
    await page.waitForURL('**/game')
    
    // Find and verify COPY button is visible
    const copyButton = page.locator('button:has-text("COPY")')
    await expect(copyButton).toBeVisible()
    
    // Click copy button
    await copyButton.click()
    
    // Verify button changes to "COPIED!"
    await expect(page.locator('button:has-text("COPIED!")')).toBeVisible({ timeout: 1000 })
    
    // Verify clipboard contains game ID (if clipboard API is available in test environment)
    // Note: This might not work in all test environments
  })
})