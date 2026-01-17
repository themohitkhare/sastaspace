const DICE_PATTERNS = {
  1: ['   ', ' ● ', '   '],
  2: ['●  ', '   ', '  ●'],
  3: ['●  ', ' ● ', '  ●'],
  4: ['● ●', '   ', '● ●'],
  5: ['● ●', ' ● ', '● ●'],
  6: ['● ●', '● ●', '● ●'],
}

function Die({ value }) {
  const pattern = DICE_PATTERNS[value] || DICE_PATTERNS[1]

  return (
    <div className="die border-brutal-sm bg-sasta-white p-2 w-14 h-14 flex flex-col items-center justify-center font-mono text-[10px] leading-tight">
      {pattern.map((row, idx) => (
        <div key={idx} className="whitespace-pre">{row}</div>
      ))}
    </div>
  )
}

export default function DiceDisplay({ lastDiceRoll }) {
  if (!lastDiceRoll?.dice1) {
    return (
      <div className="text-center p-4">
        <div className="flex justify-center gap-2 opacity-40">
          <div className="border-brutal-sm border-dashed bg-sasta-white/50 w-14 h-14 flex items-center justify-center font-zero text-xs">
            ?
          </div>
          <div className="border-brutal-sm border-dashed bg-sasta-white/50 w-14 h-14 flex items-center justify-center font-zero text-xs">
            ?
          </div>
        </div>
        <p className="font-zero text-xs mt-2 opacity-60">NO ROLL YET</p>
      </div>
    )
  }

  const { dice1, dice2, total, is_doubles, passed_go } = lastDiceRoll

  return (
    <div className="text-center">
      <div className="flex justify-center gap-3 mb-2">
        <Die value={dice1} />
        <Die value={dice2} />
      </div>
      <div className={`font-zero font-bold text-lg ${is_doubles ? 'text-sasta-accent bg-sasta-black px-2' : ''}`}>
        TOTAL: {total} {is_doubles && '(DOUBLES!)'}
      </div>
      {passed_go && (
        <div className="font-zero text-xs mt-1 text-sasta-accent bg-sasta-black px-2 py-1 inline-block">
          PASSED GO! +${passed_go}
        </div>
      )}
    </div>
  )
}
