/**
 * TileSubmissionForm - Form for submitting 5 custom tiles
 */
import React, { useState } from 'react'

const TILE_TYPES = ['PROPERTY', 'TAX', 'CHANCE', 'TRAP', 'BUFF']

export default function TileSubmissionForm({ tiles, setTiles }) {
  const updateTile = (index, field, value) => {
    const newTiles = [...tiles]
    if (!newTiles[index]) {
      newTiles[index] = { type: 'PROPERTY', name: '', effect_config: {} }
    }
    newTiles[index] = { ...newTiles[index], [field]: value }
    setTiles(newTiles)
  }

  const addTile = () => {
    if (tiles.length < 5) {
      setTiles([...tiles, { type: 'PROPERTY', name: '', effect_config: {} }])
    }
  }

  return (
    <div className="mt-4">
      <h4 className="text-xl font-bold font-zero mb-2">
        SUBMIT 5 TILES ({tiles.length}/5)
      </h4>

      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="mb-3 border-brutal-sm p-3">
          <div className="flex gap-3 mb-2">
            <select
              value={tiles[index]?.type || 'PROPERTY'}
              onChange={(e) => updateTile(index, 'type', e.target.value)}
              className="border-brutal-sm p-2 font-zero"
            >
              {TILE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={tiles[index]?.name || ''}
              onChange={(e) => updateTile(index, 'name', e.target.value)}
              placeholder={`Tile ${index + 1} name`}
              className="flex-1 border-brutal-sm p-2 font-zero"
            />
          </div>
        </div>
      ))}
    </div>
  )
}
