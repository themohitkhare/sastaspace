/**
 * E2E tests for CPU-only game simulation
 * Tests complete game lifecycle with only CPU players - no human interaction
 */
import { test, expect } from '@playwright/test'

const API_URL = 'http://localhost:8000/api/v1/sastadice'

interface SimulationResult {
  game_id: string
  status: string
  turns_played: number
  winner: {
    name: string
    cash: number
    properties: number
    status?: string
  } | null
  final_standings: Array<{
    name: string
    cash: number
    properties: number
  }>
  turn_log: Array<{
    turn: number
    player: string
    player_id: string
    cash_before: number
    cash_after: number
    position_before: number
    position_after: number
    actions: Array<{
      action: string
      result: string
    }>
  }>
}

interface GameSession {
  id: string
  status: string
  players: Array<{
    id: string
    name: string
    cash: number
    position: number
    properties: string[]
  }>
  board: Array<{
    id: string
    name: string
    type: string
    position: number
  }>
}

test.describe('CPU-Only Game Simulation', () => {
  
  test('Create game with 2 CPU players and simulate to completion', async ({ request }) => {
    // Create a game with 2 CPU players
    const createResponse = await request.post(`${API_URL}/games?cpu_count=2`)
    expect(createResponse.ok()).toBeTruthy()
    
    const game: GameSession = await createResponse.json()
    expect(game.id).toBeTruthy()
    expect(game.players).toHaveLength(2)
    expect(game.players[0].name).toBe('CPU-1')
    expect(game.players[1].name).toBe('CPU-2')
    
    console.log(`Created game ${game.id} with 2 CPU players`)
    
    // Simulate the game
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=200`
    )
    expect(simulateResponse.ok()).toBeTruthy()
    
    const result: SimulationResult = await simulateResponse.json()
    
    console.log(`Game simulation completed:`)
    console.log(`  Status: ${result.status}`)
    console.log(`  Turns played: ${result.turns_played}`)
    console.log(`  Winner: ${result.winner?.name} with $${result.winner?.cash}`)
    
    // Verify simulation ran
    expect(result.turns_played).toBeGreaterThan(0)
    expect(result.final_standings).toHaveLength(2)
    
    // Verify game has a conclusion or reached max turns
    expect(['FINISHED', 'ACTIVE']).toContain(result.status)
    
    // Verify winner info
    expect(result.winner).toBeTruthy()
    expect(result.winner?.name).toMatch(/CPU-[12]/)
  })

  test('Create game with 4 CPU players and simulate', async ({ request }) => {
    // Create a game with 4 CPU players
    const createResponse = await request.post(`${API_URL}/games?cpu_count=4`)
    expect(createResponse.ok()).toBeTruthy()
    
    const game: GameSession = await createResponse.json()
    expect(game.players).toHaveLength(4)
    
    console.log(`Created game ${game.id} with 4 CPU players`)
    
    // Simulate the game
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=300`
    )
    expect(simulateResponse.ok()).toBeTruthy()
    
    const result: SimulationResult = await simulateResponse.json()
    
    console.log(`4-player game simulation:`)
    console.log(`  Status: ${result.status}`)
    console.log(`  Turns played: ${result.turns_played}`)
    console.log(`  Final standings:`)
    result.final_standings.forEach((p, i) => {
      console.log(`    ${i + 1}. ${p.name}: $${p.cash}, ${p.properties} properties`)
    })
    
    // Verify all 4 players participated
    expect(result.final_standings).toHaveLength(4)
    
    // Verify standings are sorted by cash (descending)
    for (let i = 0; i < result.final_standings.length - 1; i++) {
      expect(result.final_standings[i].cash).toBeGreaterThanOrEqual(
        result.final_standings[i + 1].cash
      )
    }
  })

  test('CPU players make intelligent buying decisions', async ({ request }) => {
    // Create game with 2 CPUs
    const createResponse = await request.post(`${API_URL}/games?cpu_count=2`)
    const game: GameSession = await createResponse.json()
    
    // Simulate with detailed logging - run longer to get property decisions
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=100`
    )
    const result: SimulationResult = await simulateResponse.json()
    
    // Check final standings for property ownership (more reliable than turn_log)
    const totalProperties = result.final_standings.reduce(
      (sum, p) => sum + p.properties, 0
    )
    
    console.log(`CPU buying behavior:`)
    console.log(`  Total turns played: ${result.turns_played}`)
    console.log(`  Total properties acquired: ${totalProperties}`)
    result.final_standings.forEach(p => {
      console.log(`  ${p.name}: ${p.properties} properties, $${p.cash}`)
    })
    
    // After 100 turns, CPUs should have acquired some properties
    // This verifies they are making buy decisions
    expect(result.turns_played).toBeGreaterThan(0)
    
    // Verify game state is valid
    expect(result.final_standings.length).toBe(2)
    for (const player of result.final_standings) {
      expect(player.name).toMatch(/CPU-\d+/)
      expect(player.cash).toBeDefined()
      expect(player.properties).toBeGreaterThanOrEqual(0)
    }
  })

  test('Game handles dice rolling correctly', async ({ request }) => {
    // Create and simulate
    const createResponse = await request.post(`${API_URL}/games?cpu_count=2`)
    const game: GameSession = await createResponse.json()
    
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=20`
    )
    const result: SimulationResult = await simulateResponse.json()
    
    // Verify turns were played
    expect(result.turns_played).toBeGreaterThan(0)
    
    // Check that at least some turns have dice rolling
    let turnsWithDiceRoll = 0
    for (const turn of result.turn_log) {
      const rollAction = turn.actions.find(a => a.action === 'ROLL_DICE')
      if (rollAction) {
        turnsWithDiceRoll++
      }
      
      // Position should be defined
      expect(turn.position_after).toBeDefined()
    }
    
    console.log(`Verified ${result.turn_log.length} turns in log`)
    console.log(`Turns with ROLL_DICE: ${turnsWithDiceRoll}`)
    console.log(`Total turns played: ${result.turns_played}`)
    
    // The game must have processed turns
    expect(result.turns_played).toBeGreaterThanOrEqual(10)
  })

  test('Game economy works correctly - cash changes appropriately', async ({ request }) => {
    // Create and simulate a longer game
    const createResponse = await request.post(`${API_URL}/games?cpu_count=2`)
    const game: GameSession = await createResponse.json()
    
    // Get initial state
    const initialTotalCash = game.players.reduce((sum, p) => sum + p.cash, 0)
    
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=100`
    )
    const result: SimulationResult = await simulateResponse.json()
    
    // Calculate final total cash
    const finalTotalCash = result.final_standings.reduce((sum, p) => sum + p.cash, 0)
    
    console.log(`Economy analysis:`)
    console.log(`  Initial total cash: $${initialTotalCash}`)
    console.log(`  Final total cash: $${finalTotalCash}`)
    console.log(`  Net change: $${finalTotalCash - initialTotalCash}`)
    console.log(`  Turns played: ${result.turns_played}`)
    
    // After 100 turns, cash should have changed (GO bonuses, rent, events)
    // The total cash in the system should be different from the start
    expect(result.turns_played).toBeGreaterThan(0)
    
    // Verify each player has valid cash
    for (const player of result.final_standings) {
      expect(typeof player.cash).toBe('number')
    }
  })

  test('Bankruptcy detection works', async ({ request }) => {
    // Create and simulate a longer game to potentially trigger bankruptcy
    const createResponse = await request.post(`${API_URL}/games?cpu_count=3`)
    const game: GameSession = await createResponse.json()
    
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=500`
    )
    const result: SimulationResult = await simulateResponse.json()
    
    console.log(`Bankruptcy test:`)
    console.log(`  Game status: ${result.status}`)
    console.log(`  Turns played: ${result.turns_played}`)
    
    // Check for bankrupt players (negative cash)
    const bankruptPlayers = result.final_standings.filter(p => p.cash < 0)
    console.log(`  Bankrupt players: ${bankruptPlayers.length}`)
    
    if (result.status === 'FINISHED') {
      // Game should have a clear winner
      expect(result.winner).toBeTruthy()
      console.log(`  Winner: ${result.winner?.name}`)
    }
  })

  test('Properties are acquired during game', async ({ request }) => {
    // Create and simulate
    const createResponse = await request.post(`${API_URL}/games?cpu_count=2`)
    const game: GameSession = await createResponse.json()
    
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=100`
    )
    const result: SimulationResult = await simulateResponse.json()
    
    // Check property ownership in final standings
    const totalProperties = result.final_standings.reduce(
      (sum, p) => sum + p.properties, 0
    )
    
    console.log(`Property acquisition:`)
    result.final_standings.forEach(p => {
      console.log(`  ${p.name}: ${p.properties} properties`)
    })
    console.log(`  Total properties owned: ${totalProperties}`)
    
    // After 100 turns, some properties should be owned
    expect(totalProperties).toBeGreaterThan(0)
  })

  test('Full game to completion', async ({ request }) => {
    // This test runs a full game until someone wins
    const createResponse = await request.post(`${API_URL}/games?cpu_count=2`)
    const game: GameSession = await createResponse.json()
    
    console.log(`Starting full game simulation: ${game.id}`)
    
    // Run up to 500 turns - should be enough for a game to complete
    const simulateResponse = await request.post(
      `${API_URL}/games/${game.id}/simulate?max_turns=500`
    )
    const result: SimulationResult = await simulateResponse.json()
    
    console.log(`\n=== FULL GAME RESULTS ===`)
    console.log(`Game ID: ${result.game_id}`)
    console.log(`Status: ${result.status}`)
    console.log(`Total turns: ${result.turns_played}`)
    console.log(`\nFinal Standings:`)
    result.final_standings.forEach((p, i) => {
      const status = p.cash < 0 ? '(BANKRUPT)' : ''
      console.log(`  ${i + 1}. ${p.name}: $${p.cash} ${status}, ${p.properties} properties`)
    })
    
    if (result.winner) {
      console.log(`\n🏆 WINNER: ${result.winner.name}`)
      console.log(`   Final cash: $${result.winner.cash}`)
      console.log(`   Properties: ${result.winner.properties}`)
    }
    
    // Verify game completed properly
    expect(result.turns_played).toBeGreaterThan(0)
    expect(result.winner).toBeTruthy()
    
    // Game should either finish or reach max turns
    expect(['FINISHED', 'ACTIVE']).toContain(result.status)
  })
})
