import { useState, useEffect } from 'react'
import Confetti from 'react-confetti'
import { useNavigate } from 'react-router-dom'

export default function VictoryScreen({ winner, players, onPlayAgain, game }) {
    const { width, height } = useWindowSize()
    const [showStats, setShowStats] = useState(false)
    const [showGameStats, setShowGameStats] = useState(false)
    const navigate = useNavigate()

    const sortedPlayers = [...players].sort((a, b) => b.cash - a.cash)

    let winnerDetails = sortedPlayers.find((p) => p.id === winner)

    if (!winnerDetails && sortedPlayers.length > 0) {
        winnerDetails = sortedPlayers[0]
    }

    if (!winnerDetails) {
        winnerDetails = { name: 'UNKNOWN', cash: 0, color: '#00FF00', properties: [] }
    }

    const losers = sortedPlayers.filter((p) => p.id !== winnerDetails.id)

    // Compute game stats from board + players
    const board = game?.board || []
    const totalTurns = game?.current_round || 0
    const playerStats = sortedPlayers.map((p) => {
        const ownedProperties = board.filter((t) => t.owner_id === p.id)
        const propertyValue = ownedProperties.reduce((sum, t) => sum + (t.price || 0), 0)
        return {
            ...p,
            propertyCount: ownedProperties.length,
            netWorth: (p.cash || 0) + propertyValue,
        }
    })
    const winnerStats = playerStats.find((p) => p.id === winnerDetails.id) || { propertyCount: 0, netWorth: winnerDetails.cash || 0 }

    return (
        <div className="h-screen w-screen bg-sasta-white overflow-hidden flex flex-col font-data text-sasta-black selection:bg-sasta-accent selection:text-sasta-black relative">
            <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
                <Confetti
                    width={width}
                    height={height}
                    recycle={true}
                    numberOfPieces={100}
                    colors={['#000000', '#00ff00', '#ffffff']}
                />
            </div>

            <div className="border-b-2 border-sasta-black p-4 bg-sasta-white z-20 shrink-0">
                <div className="flex flex-col items-center">
                    <div className="text-[10px] font-data font-bold tracking-widest text-sasta-black/60 mb-1 uppercase">
                        GAME COMPLETE
                    </div>
                    <h1 className="text-4xl md:text-6xl font-zero font-black tracking-tighter uppercase text-sasta-black text-center leading-none">
                        VICTORY
                    </h1>
                </div>
            </div>

            <div className="flex-1 flex flex-col items-center justify-center p-4 z-20 min-h-0 overflow-hidden">
                <div className="w-full max-w-xl bg-sasta-white border-brutal-lg shadow-brutal-lg p-6 relative mb-6 shrink-0">
                    <div className="flex flex-row items-center gap-6">
                        <div
                            className="w-24 h-24 md:w-32 md:h-32 border-brutal-lg bg-sasta-black flex items-center justify-center font-zero font-bold text-5xl text-sasta-accent shadow-brutal-sm shrink-0"
                            style={{ backgroundColor: winnerDetails.color }}
                        >
                            <span className="relative z-10 filter grayscale mix-blend-multiply">{winnerDetails.name[0]?.toUpperCase()}</span>
                        </div>

                        <div className="flex-1 w-full overflow-hidden">
                            <div className="flex items-center gap-2 text-sasta-black mb-1">
                                <span className="text-[10px] font-bold tracking-widest uppercase border border-sasta-black px-1">[ WINNER ]</span>
                            </div>
                            <h2 className="text-3xl md:text-5xl font-zero font-bold text-sasta-black mb-2 truncate uppercase tracking-tight">
                                {winnerDetails.name}
                            </h2>
                            <div className="inline-block bg-sasta-white border-2 border-sasta-black px-3 py-1 mt-1 shadow-brutal-sm">
                                <div className="text-[8px] text-sasta-black/60 uppercase tracking-wider mb-0.5">FINAL BALANCE</div>
                                <div className="text-2xl md:text-3xl font-data font-bold text-sasta-black">
                                    ${winnerDetails.cash?.toLocaleString()}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="w-full max-w-xl flex flex-col min-h-0 shrink-0 overflow-y-auto max-h-[50vh]">
                    <button
                        onClick={() => setShowGameStats(!showGameStats)}
                        className={`w-full flex items-center justify-between bg-sasta-white border-2 border-sasta-black p-3 hover:bg-sasta-accent hover:text-sasta-black transition-colors font-zero font-bold group shadow-brutal-sm ${showGameStats ? 'mb-0 border-b-0 pb-2' : 'mb-2'}`}
                    >
                        <div className="flex items-center gap-3">
                            <span className="uppercase tracking-widest text-sm">GAME STATS</span>
                        </div>
                        <span className="text-xs">{showGameStats ? '▲' : '▼'}</span>
                    </button>

                    {showGameStats && (
                        <div className="bg-sasta-white border-2 border-t-0 border-sasta-black p-4 shadow-brutal-sm mb-2">
                            <div className="grid grid-cols-2 gap-2 font-data text-xs mb-3">
                                <div className="border-brutal-sm p-2 text-center">
                                    <div className="text-[9px] text-sasta-black/60 uppercase tracking-wider">TURNS PLAYED</div>
                                    <div className="text-xl font-bold text-sasta-black">{totalTurns}</div>
                                </div>
                                <div className="border-brutal-sm p-2 text-center">
                                    <div className="text-[9px] text-sasta-black/60 uppercase tracking-wider">WINNER NET WORTH</div>
                                    <div className="text-xl font-bold text-sasta-black">${winnerStats.netWorth?.toLocaleString()}</div>
                                </div>
                            </div>
                            <div className="flex flex-col gap-1 font-data text-xs">
                                {playerStats.map((player) => (
                                    <div key={player.id} className="flex justify-between items-center border-b border-dashed border-sasta-black/20 pb-1 last:border-0 px-2">
                                        <span className="font-bold text-sasta-black uppercase">{player.name}</span>
                                        <div className="flex items-center gap-3">
                                            <span className="text-sasta-black/60">{player.propertyCount} PROPS</span>
                                            <span className="font-bold text-sasta-black">${player.cash?.toLocaleString()}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <button
                        onClick={() => setShowStats(!showStats)}
                        className={`w-full flex items-center justify-between bg-sasta-white border-2 border-sasta-black p-3 hover:bg-sasta-accent hover:text-sasta-black transition-colors font-zero font-bold group shadow-brutal-sm ${showStats ? 'mb-0 border-b-0 pb-2' : 'mb-0'}`}
                    >
                        <div className="flex items-center gap-3">
                            <span className="uppercase tracking-widest text-sm">BANKRUPT PLAYERS [{losers.length}]</span>
                        </div>
                        <span className="text-xs">{showStats ? '▲' : '▼'}</span>
                    </button>

                    {showStats && (
                        <div className="bg-sasta-white border-2 border-t-0 border-sasta-black p-4 shadow-brutal-sm overflow-y-auto max-h-[30vh]">
                            <div className="flex flex-col gap-2 font-data text-xs">
                                {losers.length === 0 ? (
                                    <div className="text-sasta-black/60 italic text-center py-2 uppercase">NO BANKRUPTCIES</div>
                                ) : (
                                    losers.map((player, index) => (
                                        <div key={player.id} className="flex justify-between items-center border-b border-dashed border-sasta-black/20 pb-1 mb-1 last:border-0 hover:bg-sasta-accent/10 px-2 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <span className="text-sasta-black/60 font-bold w-4">#{index + 2}</span>
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-sasta-black uppercase">{player.name}</span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {(player.is_bankrupt || player.bankrupt) && <span className="text-[9px] text-sasta-white font-bold bg-sasta-black px-1">ELIMINATED</span>}
                                                <span className="font-bold text-sasta-black">${player.cash?.toLocaleString()}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="border-t-2 border-sasta-black p-4 bg-sasta-white z-50 shrink-0">
                <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-4">
                    <button
                        onClick={onPlayAgain}
                        className="flex-1 bg-sasta-accent text-sasta-black py-4 font-bold font-zero text-lg border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all uppercase tracking-widest flex items-center justify-center gap-2"
                    >
                        <span>↻</span>
                        PLAY AGAIN
                    </button>
                    <button
                        onClick={() => {
                            onPlayAgain?.()
                            navigate('/')
                        }}
                        className="flex-1 bg-sasta-black text-sasta-accent py-4 font-bold font-zero text-lg border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all uppercase tracking-widest flex items-center justify-center gap-2"
                    >
                        <span>⌂</span>
                        RETURN TO HOME
                    </button>
                </div>
            </div>
        </div>
    )
}

function useWindowSize() {
    const [size, setSize] = useState({ width: window.innerWidth, height: window.innerHeight })
    useEffect(() => {
        const handleResize = () => setSize({ width: window.innerWidth, height: window.innerHeight })
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])
    return size
}
