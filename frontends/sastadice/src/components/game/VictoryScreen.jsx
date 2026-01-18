import { useNavigate } from 'react-router-dom'
import { useGameStore } from '../../store/useGameStore'
import { useEffect, useState } from 'react'

function Confetti() {
    const colors = ['#00ff00', '#ff0000', '#ffff00', '#00ffff', '#ff00ff', '#ffffff']
    const [particles, setParticles] = useState([])

    useEffect(() => {
        const newParticles = Array.from({ length: 50 }, (_, i) => ({
            id: i,
            left: Math.random() * 100,
            delay: Math.random() * 2,
            duration: 2 + Math.random() * 2,
            color: colors[Math.floor(Math.random() * colors.length)],
            size: 6 + Math.random() * 8,
        }))
        setParticles(newParticles)
    }, [])

    return (
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-40">
            {particles.map((p) => (
                <div
                    key={p.id}
                    className="absolute animate-confetti"
                    style={{
                        left: `${p.left}%`,
                        top: '-20px',
                        width: `${p.size}px`,
                        height: `${p.size}px`,
                        backgroundColor: p.color,
                        animationDelay: `${p.delay}s`,
                        animationDuration: `${p.duration}s`,
                    }}
                />
            ))}
        </div>
    )
}

export default function VictoryScreen({ game, winner }) {
    const navigate = useNavigate()
    const reset = useGameStore((s) => s.reset)
    const [showConfetti, setShowConfetti] = useState(true)

    const gameWinner = winner || (() => {
        const activePlayers = game.players.filter((p) => !p.is_bankrupt)
        if (activePlayers.length === 1) {
            return activePlayers[0]
        }
        return [...game.players].sort((a, b) => b.cash - a.cash)[0]
    })()

    const standings = [...game.players].sort((a, b) => b.cash - a.cash)
    const totalProperties = game.board?.filter(t => t.owner_id)?.length || 0
    const bankruptPlayers = game.players?.filter(p => p.is_bankrupt)?.length || 0
    const winnerProperties = game.board?.filter(t => t.owner_id === gameWinner.id)?.length || 0

    useEffect(() => {
        const timeout = setTimeout(() => setShowConfetti(false), 4000)
        return () => clearTimeout(timeout)
    }, [])

    const handlePlayAgain = () => {
        reset()
        navigate('/')
    }

    const handleGoHome = () => {
        reset()
        navigate('/')
    }

    return (
        <div className="min-h-screen bg-sasta-black flex items-center justify-center p-4 relative">
            {showConfetti && <Confetti />}

            <div className="max-w-lg w-full relative z-10">
                <div className="border-brutal-lg bg-sasta-accent shadow-brutal-lg p-8 text-center mb-6 animate-bounce-slow">
                    <div className="text-6xl mb-4 animate-pulse">🏆</div>
                    <h1 className="font-zero text-4xl font-bold text-sasta-black mb-2">
                        WINNER!
                    </h1>
                    <div className="font-zero text-2xl font-bold text-sasta-black mb-4">
                        {gameWinner.name?.toUpperCase()}
                    </div>
                    <div className="flex flex-wrap justify-center gap-3 font-zero text-sm">
                        <div className="border-brutal-sm bg-sasta-white px-3 py-2">
                            <span className="opacity-60">CASH:</span>
                            <span className="font-bold ml-2">${gameWinner.cash?.toLocaleString()}</span>
                        </div>
                        <div className="border-brutal-sm bg-sasta-white px-3 py-2">
                            <span className="opacity-60">PROPERTIES:</span>
                            <span className="font-bold ml-2">{winnerProperties}</span>
                </div>
              </div>
            </div>

                <div className="border-brutal-lg bg-sasta-black border-sasta-accent shadow-brutal-lg p-4 mb-6">
                    <h3 className="font-zero text-sm font-bold text-sasta-accent mb-3 text-center">
                        📊 GAME STATS
                    </h3>
                    <div className="grid grid-cols-3 gap-2 text-center font-zero text-xs">
                        <div className="bg-sasta-accent/20 p-2 border border-sasta-accent">
                            <div className="text-sasta-accent font-bold text-lg">{game.players?.length || 0}</div>
                            <div className="text-sasta-white/60">PLAYERS</div>
                        </div>
                        <div className="bg-sasta-accent/20 p-2 border border-sasta-accent">
                            <div className="text-sasta-accent font-bold text-lg">{totalProperties}</div>
                            <div className="text-sasta-white/60">OWNED</div>
                        </div>
                        <div className="bg-sasta-accent/20 p-2 border border-sasta-accent">
                            <div className="text-sasta-accent font-bold text-lg">{bankruptPlayers}</div>
                            <div className="text-sasta-white/60">BANKRUPT</div>
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
                        className="flex-1 min-h-[48px] py-4 px-6 bg-sasta-accent text-sasta-black font-zero font-bold text-lg border-brutal-lg shadow-brutal-lg hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
                    >
                        PLAY AGAIN
                    </button>
                    <button
                        onClick={handleGoHome}
                        className="flex-1 min-h-[48px] py-4 px-6 bg-sasta-white text-sasta-black font-zero font-bold text-lg border-brutal-lg shadow-brutal-lg hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
                    >
                        HOME
                    </button>
                </div>
            </div>
        </div>
    )
}

