import { useNavigate } from 'react-router-dom'
import { useGameStore } from '../../store/useGameStore'

export default function VictoryScreen({ game, winner }) {
    const navigate = useNavigate()
    const reset = useGameStore((s) => s.reset)

    const gameWinner = winner || (() => {
        const activePlayers = game.players.filter((p) => !p.is_bankrupt)
        if (activePlayers.length === 1) {
            return activePlayers[0]
        }
        return [...game.players].sort((a, b) => b.cash - a.cash)[0]
    })()

    const standings = [...game.players].sort((a, b) => b.cash - a.cash)

    const handlePlayAgain = () => {
        reset()
        navigate('/')
    }

    const handleGoHome = () => {
        reset()
        navigate('/')
    }

    return (
        <div className="min-h-screen bg-sasta-black flex items-center justify-center p-4">
            <div className="max-w-lg w-full">
                <div className="border-brutal-lg bg-sasta-accent shadow-brutal-lg p-8 text-center mb-6">
                    <div className="text-6xl mb-4">🏆</div>
                    <h1 className="font-zero text-4xl font-bold text-sasta-black mb-2">
                        WINNER!
                    </h1>
                    <div className="font-zero text-2xl font-bold text-sasta-black mb-4">
                        {gameWinner.name?.toUpperCase()}
                    </div>
                    <div className="flex justify-center gap-4 font-zero text-lg">
                        <div className="border-brutal-sm bg-sasta-white px-4 py-2">
                            <span className="opacity-60">CASH:</span>
                            <span className="font-bold ml-2">${gameWinner.cash?.toLocaleString()}</span>
                        </div>
                        <div className="border-brutal-sm bg-sasta-white px-4 py-2">
                            <span className="opacity-60">PROPERTIES:</span>
                            <span className="font-bold ml-2">{gameWinner.properties?.length || 0}</span>
                        </div>
                    </div>
                </div>

                <div className="border-brutal-lg bg-sasta-white shadow-brutal-lg p-6 mb-6">
                    <h2 className="font-zero text-xl font-bold mb-4 text-center border-b-2 border-sasta-black pb-2">
                        FINAL STANDINGS
                    </h2>
                    <div className="space-y-2">
                        {standings.map((player, index) => (
                            <div
                                key={player.id}
                                className={`flex items-center justify-between p-3 border-brutal-sm ${player.is_bankrupt ? 'bg-red-100 opacity-60' : 'bg-sasta-white'
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <span className="font-zero text-lg font-bold w-8">
                                        {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}
                                    </span>
                                    <div
                                        className="w-4 h-4 border-2 border-sasta-black"
                                        style={{ backgroundColor: player.color }}
                                    />
                                    <span className="font-zero font-bold">
                                        {player.name?.toUpperCase()}
                                    </span>
                                    {player.is_bankrupt && (
                                        <span className="text-xs font-zero text-red-500">(BANKRUPT)</span>
                                    )}
                                </div>
                                <div className="font-zero font-bold">
                                    ${player.cash?.toLocaleString()}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="flex gap-4">
                    <button
                        onClick={handlePlayAgain}
                        className="flex-1 py-4 px-6 bg-sasta-accent text-sasta-black font-zero font-bold text-lg border-brutal-lg shadow-brutal-lg hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
                    >
                        PLAY AGAIN
                    </button>
                    <button
                        onClick={handleGoHome}
                        className="flex-1 py-4 px-6 bg-sasta-white text-sasta-black font-zero font-bold text-lg border-brutal-lg shadow-brutal-lg hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
                    >
                        HOME
                    </button>
                </div>
            </div>
        </div>
    )
}
