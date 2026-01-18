import { useState, useEffect } from 'react'

const TOAST_TYPES = {
    RENT: { icon: '💸', bg: 'bg-red-500/80', text: 'text-white' },
    PURCHASE: { icon: '🏠', bg: 'bg-green-500/80', text: 'text-white' },
    GO_BONUS: { icon: '💰', bg: 'bg-sasta-accent/80', text: 'text-sasta-black' },
    TAX: { icon: '📋', bg: 'bg-orange-500/80', text: 'text-white' },
    EVENT: { icon: '⚡', bg: 'bg-purple-500/80', text: 'text-white' },
    BUFF: { icon: '✨', bg: 'bg-cyan-500/80', text: 'text-white' },
    DEFAULT: { icon: '📢', bg: 'bg-sasta-black/80', text: 'text-sasta-accent' },
}

function parseEventType(message) {
    if (!message) return 'DEFAULT'
    const msg = message.toLowerCase()
    if (msg.includes('rent') || msg.includes('paid $')) return 'RENT'
    if (msg.includes('bought') || msg.includes('purchased')) return 'PURCHASE'
    if (msg.includes('go') && msg.includes('+$')) return 'GO_BONUS'
    if (msg.includes('tax')) return 'TAX'
    if (msg.includes('buff') || msg.includes('bonus')) return 'BUFF'
    if (msg.includes('event') || msg.includes('sasta') || msg.includes('monsoon') || msg.includes('flood')) return 'EVENT'
    return 'DEFAULT'
}

function SingleToast({ message, type, onComplete }) {
    const [isVisible, setIsVisible] = useState(true)
    const config = TOAST_TYPES[type] || TOAST_TYPES.DEFAULT

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsVisible(false)
            setTimeout(() => onComplete?.(), 200)
        }, 2000) // Fast dismiss
        return () => clearTimeout(timer)
    }, [onComplete])

    return (
        <div
            className={`${config.bg} ${config.text} px-2 py-1 font-data text-xs flex items-center gap-1 rounded transition-all duration-200 ${isVisible ? 'animate-toast-in opacity-100' : 'animate-toast-out opacity-0'
                }`}
        >
            <span>{config.icon}</span>
            <span className="flex-1 truncate">{message}</span>
        </div>
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

