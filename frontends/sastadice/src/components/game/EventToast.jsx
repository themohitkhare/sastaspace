import { useState, useEffect } from 'react'

const TOAST_TYPES = {
    RENT: { icon: '💸', bg: 'bg-red-500/80', text: 'text-white' },
    PURCHASE: { icon: '🏠', bg: 'bg-green-500/80', text: 'text-white' },
    GO_BONUS: { icon: '💰', bg: 'bg-sasta-accent/80', text: 'text-sasta-black' },
    TAX: { icon: '📋', bg: 'bg-orange-500/80', text: 'text-white' },
    EVENT: { icon: '⚡', bg: 'bg-purple-500/80', text: 'text-white' },
    BUFF: { icon: '✨', bg: 'bg-cyan-500/80', text: 'text-white' },
    MARKET_CRASH: { icon: '📉', bg: 'bg-red-600/90', text: 'text-white', animate: 'animate-pulse' },
    BULL_MARKET: { icon: '📈', bg: 'bg-green-600/90', text: 'text-white', animate: 'animate-pulse' },
    HYPERINFLATION: { icon: '💸', bg: 'bg-yellow-500/90', text: 'text-black', animate: 'animate-bounce' },
    SYSTEM_UPDATE: { icon: '🔄', bg: 'bg-purple-600/90', text: 'text-white' },
    RANSOMWARE: { icon: '🔒', bg: 'bg-red-800/90', text: 'text-red-200' },
    IDENTITY_THEFT: { icon: '🎭', bg: 'bg-pink-600/90', text: 'text-white' },
    WHISTLEBLOWER: { icon: '🔍', bg: 'bg-indigo-600/90', text: 'text-white' },
    FORK_REPO: { icon: '🍴', bg: 'bg-cyan-600/90', text: 'text-white' },
    HOSTILE_TAKEOVER: { icon: '⚔️', bg: 'bg-red-700/90', text: 'text-white', animate: 'animate-pulse' },
    OPEN_SOURCE: { icon: '🔓', bg: 'bg-green-600/90', text: 'text-white' },
    SYSTEM_RESTORE: { icon: '⏪', bg: 'bg-blue-600/90', text: 'text-white' },
    DEFAULT: { icon: '📢', bg: 'bg-sasta-black/80', text: 'text-sasta-accent' },
}

function parseEventType(message) {
    if (!message) return 'DEFAULT'
    const msg = message.toLowerCase()
    if (msg.includes('market crash') || msg.includes('rent halved')) return 'MARKET_CRASH'
    if (msg.includes('bull market') || msg.includes('rent +50%')) return 'BULL_MARKET'
    if (msg.includes('hyperinflation') || msg.includes('go bonus triples')) return 'HYPERINFLATION'
    if (msg.includes('system update') || msg.includes('all players skip')) return 'SYSTEM_UPDATE'
    if (msg.includes('ransomware') || msg.includes('steal')) return 'RANSOMWARE'
    if (msg.includes('identity theft') || msg.includes('swap cash')) return 'IDENTITY_THEFT'
    if (msg.includes('whistleblower') || msg.includes('reveal')) return 'WHISTLEBLOWER'
    if (msg.includes('fork') || msg.includes('clone upgrade')) return 'FORK_REPO'
    if (msg.includes('hostile takeover') || msg.includes('force buy')) return 'HOSTILE_TAKEOVER'
    if (msg.includes('open source') || msg.includes('free landing')) return 'OPEN_SOURCE'
    if (msg.includes('system restore') || msg.includes('previous position')) return 'SYSTEM_RESTORE'
    if (msg.includes('rent') || msg.includes('paid $')) return 'RENT'
    if (msg.includes('bought') || msg.includes('purchased')) return 'PURCHASE'
    if (msg.includes('go') && msg.includes('+$')) return 'GO_BONUS'
    if (msg.includes('tax')) return 'TAX'
    if (msg.includes('buff') || msg.includes('bonus')) return 'BUFF'
    if (msg.includes('event') || msg.includes('sasta') || msg.includes('gateway') || msg.includes('crypto') || msg.includes('viral')) return 'EVENT'
    return 'DEFAULT'
}

const CHAOS_EVENTS = new Set([
    'MARKET_CRASH', 'BULL_MARKET', 'HYPERINFLATION', 'SYSTEM_UPDATE',
    'RANSOMWARE', 'IDENTITY_THEFT', 'WHISTLEBLOWER', 'FORK_REPO',
    'HOSTILE_TAKEOVER', 'OPEN_SOURCE', 'SYSTEM_RESTORE',
])

const NEGATIVE_CHAOS = new Set([
    'MARKET_CRASH', 'RANSOMWARE', 'IDENTITY_THEFT', 'HOSTILE_TAKEOVER', 'SYSTEM_UPDATE',
])

function SingleToast({ message, type, onComplete }) {
    const [isVisible, setIsVisible] = useState(true)
    const [showFlash, setShowFlash] = useState(false)
    const config = TOAST_TYPES[type] || TOAST_TYPES.DEFAULT
    const isChaos = CHAOS_EVENTS.has(type)
    const isNegativeChaos = NEGATIVE_CHAOS.has(type)

    useEffect(() => {
        if (isChaos) {
            setShowFlash(true)
            const flashTimer = setTimeout(() => setShowFlash(false), 300)
            return () => clearTimeout(flashTimer)
        }
    }, [isChaos])

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsVisible(false)
            setTimeout(() => onComplete?.(), 200)
        }, isChaos ? 3500 : 2000)
        return () => clearTimeout(timer)
    }, [onComplete, isChaos])

    return (
        <>
            {showFlash && (
                <div className={`fixed inset-0 z-[100] pointer-events-none ${isNegativeChaos ? 'animate-flash-red' : 'animate-flash-green'}`} />
            )}
            <div
                className={`${config.bg} ${config.text} ${config.animate || ''} font-data flex items-center gap-1 rounded transition-all duration-200 ${
                    isChaos
                        ? `px-3 py-2 text-sm border-brutal-lg ${isNegativeChaos ? 'border-red-400 animate-screen-shake' : 'border-sasta-accent'} shadow-brutal-sm`
                        : `px-2 py-1 text-xs border-2 ${type === 'MARKET_CRASH' ? 'border-red-400' : type === 'BULL_MARKET' ? 'border-green-400' : 'border-transparent'}`
                } ${isVisible ? 'animate-toast-in opacity-100' : 'animate-toast-out opacity-0'}`}
            >
                <span className={isChaos ? 'text-lg' : ''}>{config.icon}</span>
                <span className={`flex-1 ${isChaos ? 'font-bold' : 'truncate'}`}>{message}</span>
            </div>
        </>
    )
}

export default function EventToast({ lastEventMessage }) {
    const [toasts, setToasts] = useState([])
    const [lastProcessedMessage, setLastProcessedMessage] = useState(null)

    useEffect(() => {
        if (lastEventMessage && lastEventMessage !== lastProcessedMessage) {
            setLastProcessedMessage(lastEventMessage)
            const newToast = {
                id: Date.now(),
                message: lastEventMessage,
                type: parseEventType(lastEventMessage),
            }
            setToasts([newToast])
        }
    }, [lastEventMessage, lastProcessedMessage])

    const removeToast = (id) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }

    if (toasts.length === 0) return null

    return (
        <div className="event-toast-container w-full space-y-1">
            {toasts.map(toast => (
                <SingleToast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    onComplete={() => removeToast(toast.id)}
                />
            ))}
        </div>
    )
}

