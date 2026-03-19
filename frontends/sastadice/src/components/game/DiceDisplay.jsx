import { useState, useEffect, useRef } from 'react'

const DICE_PATTERNS = {
  1: ['   ', ' ● ', '   '],
  2: ['●  ', '   ', '  ●'],
  3: ['●  ', ' ● ', '  ●'],
  4: ['● ●', '   ', '● ●'],
  5: ['● ●', ' ● ', '● ●'],
  6: ['● ●', '● ●', '● ●'],
}

function Die({ value, isRolling, size = 'small' }) {
  const pattern = DICE_PATTERNS[value] || DICE_PATTERNS[1]
  const isLarge = size === 'large'

  return (
    <div
      className={`die border-brutal-sm bg-sasta-white flex flex-col items-center justify-center font-mono leading-tight transition-transform ${isRolling ? 'animate-dice-roll' : 'animate-dice-land'
        } ${isLarge ? 'w-20 h-20 p-3 text-base' : 'w-14 h-14 p-2 text-[10px]'}`}
    >
      {pattern.map((row, idx) => (
        <div key={idx} className="whitespace-pre">{row}</div>
      ))}
    </div>
  )
}

export default function DiceDisplay({ lastDiceRoll, size = 'small' }) {
  const [isRolling, setIsRolling] = useState(false)
  const [displayedRoll, setDisplayedRoll] = useState(null)
  const [rollingValues, setRollingValues] = useState({ dice1: 1, dice2: 1 })
  const prevRollRef = useRef(null)
  const rollIntervalRef = useRef(null)
  const isLarge = size === 'large'

  useEffect(() => {
    if (lastDiceRoll?.dice1 && lastDiceRoll?.dice2) {
      const rollKey = `${lastDiceRoll.dice1}-${lastDiceRoll.dice2}-${lastDiceRoll.total}`

      if (prevRollRef.current !== rollKey) {
        setIsRolling(true)
        prevRollRef.current = rollKey

        rollIntervalRef.current = setInterval(() => {
          setRollingValues({
            dice1: Math.floor(Math.random() * 6) + 1,
            dice2: Math.floor(Math.random() * 6) + 1,
          })
        }, 80)

        setTimeout(() => {
          clearInterval(rollIntervalRef.current)
          setIsRolling(false)
          setDisplayedRoll(lastDiceRoll)
        }, 600)
      } else if (!displayedRoll) {
        setDisplayedRoll(lastDiceRoll)
      }
    }

    return () => {
      if (rollIntervalRef.current) {
        clearInterval(rollIntervalRef.current)
      }
    }
  }, [lastDiceRoll])

  if (!lastDiceRoll?.dice1) {
    return (
      <div className="text-center p-2">
        <div className={`flex justify-center ${isLarge ? 'gap-4' : 'gap-2'} opacity-40`}>
          <div className={`border-brutal-sm border-dashed bg-sasta-white/50 flex items-center justify-center font-zero ${isLarge ? 'w-20 h-20 text-2xl' : 'w-14 h-14 text-xs'}`}>
            ?
          </div>
          <div className={`border-brutal-sm border-dashed bg-sasta-white/50 flex items-center justify-center font-zero ${isLarge ? 'w-20 h-20 text-2xl' : 'w-14 h-14 text-xs'}`}>
            ?
          </div>
        </div>
        <p className={`font-zero mt-2 opacity-60 ${isLarge ? 'text-sm' : 'text-xs'}`}>WAITING FOR ROLL</p>
      </div>
    )
  }

  const { dice1, dice2, total, is_doubles, passed_go } = isRolling
    ? { ...rollingValues, total: '??', is_doubles: false, passed_go: null }
    : (displayedRoll || lastDiceRoll)

  return (
    <div className="text-center">
      <div className={`flex justify-center ${isLarge ? 'gap-4 mb-3' : 'gap-3 mb-2'}`}>
        <Die value={dice1} isRolling={isRolling} size={size} />
        <Die value={dice2} isRolling={isRolling} size={size} />
      </div>
      <div className={`font-zero font-bold transition-all ${isLarge ? 'text-2xl' : 'text-lg'
        } ${isRolling
          ? 'animate-pulse text-sasta-black/50'
          : is_doubles
            ? 'text-sasta-accent bg-sasta-black px-2 inline-block animate-dice-result-pop'
            : 'animate-dice-result-pop'
        }`}>
        {isRolling ? 'ROLLING...' : `TOTAL: ${total}`} {!isRolling && is_doubles && '🎯 DOUBLES!'}
      </div>
      {!isRolling && passed_go && (
        <div className={`font-zero mt-1 text-sasta-accent bg-sasta-black px-2 py-1 inline-block animate-pulse ${isLarge ? 'text-sm' : 'text-xs'}`}>
          💰 PASSED GO! +${passed_go}
        </div>
      )}
    </div>
  )
}

