import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import GameSettingsPanel from '../../src/components/lobby/GameSettingsPanel'

describe('GameSettingsPanel', () => {
  const defaultSettings = {
    win_condition: 'SUDDEN_DEATH',
    round_limit: 30,
    chaos_level: 'NORMAL',
    doubles_give_extra_turn: true,
    enable_stimulus: true,
    enable_black_market: true,
    enable_auctions: true,
    target_cash: 5000,
    board_preset: 'CLASSIC',
    starting_cash_multiplier: 1.0,
    income_tax_rate: 0.1,
  }

  it('renders board preset selector for host', () => {
    const onUpdate = vi.fn()
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={onUpdate}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    expect(screen.getByText('CLASSIC')).toBeDefined()
    expect(screen.getByText('UGC 24')).toBeDefined()
  })

  it('updates board_preset when UGC 24 is clicked', () => {
    const onUpdate = vi.fn()
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={onUpdate}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    fireEvent.click(screen.getByText('UGC 24'))
    expect(onUpdate).toHaveBeenCalledWith('board_preset', 'UGC_24')
  })

  it('renders starting cash multiplier options', () => {
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={vi.fn()}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    expect(screen.getByText('0.5x')).toBeDefined()
    expect(screen.getByText('1x')).toBeDefined()
    expect(screen.getByText('2x')).toBeDefined()
  })

  it('renders income tax rate options', () => {
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={vi.fn()}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    expect(screen.getByText('5%')).toBeDefined()
    expect(screen.getByText('10%')).toBeDefined()
    expect(screen.getByText('15%')).toBeDefined()
  })
})
