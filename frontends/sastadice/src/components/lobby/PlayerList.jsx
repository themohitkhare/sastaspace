/**
 * PlayerList - Displays list of players in the lobby
 */
import React from 'react'

export default function PlayerList({ players }) {
  if (!players || players.length === 0) {
    return (
      <div className="border-brutal-lg bg-sasta-white p-4 shadow-brutal-lg">
        <p className="font-zero">No players yet...</p>
      </div>
    )
  }

  return (
    <div className="border-brutal-lg bg-sasta-white p-4 shadow-brutal-lg">
      <h3 className="text-2xl font-bold font-zero mb-4">PLAYERS ({players.length})</h3>
      <ul className="space-y-2">
        {players.map((player) => (
          <li
            key={player.id}
            className="border-brutal-sm p-3 bg-sasta-white font-zero"
          >
            <span className="font-bold">{player.name}</span>
            <span className="ml-4 text-sm">Cash: ${player.cash}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
