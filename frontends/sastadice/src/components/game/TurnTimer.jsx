import { useState, useEffect, useRef } from 'react'

export default function TurnTimer({ turnStartTime, timeoutSeconds = 30, onTimeout }) {
  const [timeRemaining, setTimeRemaining] = useState(timeoutSeconds)
  const timeoutFiredRef = useRef(false)

  useEffect(() => {
    timeoutFiredRef.current = false
    if (!turnStartTime || turnStartTime === 0) {
      setTimeRemaining(timeoutSeconds)
      return
    }

    const updateTimer = () => {
      const elapsed = (Date.now() / 1000) - turnStartTime
      const remaining = Math.max(0, timeoutSeconds - elapsed)
      setTimeRemaining(remaining)

      if (remaining <= 0 && onTimeout && !timeoutFiredRef.current) {
        timeoutFiredRef.current = true
        onTimeout()
      }
    }

    updateTimer()
    const interval = setInterval(updateTimer, 100)

    return () => clearInterval(interval)
  }, [turnStartTime, timeoutSeconds, onTimeout])

  const progress = (timeRemaining / timeoutSeconds) * 100
  const isWarning = timeRemaining < 10

  return (
    <div className="w-full bg-sasta-white border-brutal-sm p-2">
      <div className="flex items-center justify-between mb-1">
        <span className="font-data text-xs font-bold text-sasta-black">
          TURN TIMER
        </span>
        <span
          className={`font-data text-xs font-bold ${
            isWarning ? 'text-red-600' : 'text-sasta-black'
          }`}
        >
          {Math.ceil(timeRemaining)}s
        </span>
      </div>
      <div className="w-full h-3 bg-sasta-black border border-sasta-black">
        <div
          className={`h-full transition-all ${
            isWarning ? 'bg-red-600' : 'bg-sasta-accent'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}
