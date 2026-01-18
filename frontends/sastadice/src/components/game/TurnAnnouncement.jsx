import { useState, useEffect } from 'react'

export default function TurnAnnouncement({ playerName, isMyTurn, show }) {
    const [visible, setVisible] = useState(false)

    useEffect(() => {
        if (show) {
            setVisible(true)
            const timeout = setTimeout(() => setVisible(false), 1500)
            return () => clearTimeout(timeout)
        }
    }, [show])

    if (!visible) return null

    return (
        <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
            <div className="animate-turn-announce bg-sasta-black/90 px-8 py-6 border-brutal-lg shadow-brutal-lg">
                <div className="text-center">
                    <div className="font-zero text-sasta-accent text-sm mb-1">
                        {isMyTurn ? '🎲 YOUR TURN' : 'CURRENT TURN'}
                    </div>
                    <div className="font-zero text-3xl sm:text-5xl font-bold text-sasta-white">
                        {playerName?.toUpperCase() || 'UNKNOWN'}
                    </div>
                    {isMyTurn && (
                        <div className="font-zero text-sasta-accent text-sm mt-2 animate-pulse">
                            PRESS SPACE TO ROLL
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
