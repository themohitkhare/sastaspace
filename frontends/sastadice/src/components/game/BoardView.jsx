import TileComponent from './TileComponent'
import PlayerToken from './PlayerToken'

const TILE_SIZE = 72

export default function BoardView({ tiles = [], boardSize, players = [], children }) {
  if (!boardSize || boardSize < 2) {
    return <div className="text-center p-8 font-zero">LOADING BOARD...</div>
  }

  const isOnPerimeter = (x, y) => x === 0 || x === boardSize - 1 || y === 0 || y === boardSize - 1

  return (
    <div className="board-wrapper flex justify-center items-center py-6">
      <div
        className="board-container relative border-brutal"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${boardSize}, ${TILE_SIZE}px)`,
          gridTemplateRows: `repeat(${boardSize}, ${TILE_SIZE}px)`,
          gap: '0px',
          backgroundColor: '#000',
        }}
      >
        {tiles.map((tile) => {
          if (!isOnPerimeter(tile.x, tile.y)) return null
          return (
            <div key={tile.id} style={{ gridColumn: tile.x + 1, gridRow: tile.y + 1 }}>
              <TileComponent tile={tile} players={players} />
            </div>
          )
        })}

        {players.map((player) => {
          const tile = tiles.find((t) => t.position === player.position)
          if (!tile || !isOnPerimeter(tile.x, tile.y)) return null

          const playersOnSameTile = players.filter(p => p.position === player.position)
          const playerIndex = playersOnSameTile.findIndex(p => p.id === player.id)

          return (
            <PlayerToken
              key={player.id}
              player={player}
              tile={tile}
              boardSize={boardSize}
              offsetX={(playerIndex % 2) * 18 - 9}
              offsetY={Math.floor(playerIndex / 2) * 18 - 9}
            />
          )
        })}

        {boardSize > 2 && (
          <div
            className="board-center bg-sasta-white border-brutal flex flex-col items-center justify-center"
            style={{ gridColumn: `2 / ${boardSize}`, gridRow: `2 / ${boardSize}` }}
          >
            {children}
          </div>
        )}
      </div>
    </div>
  )
}

export { TILE_SIZE }
