import { useState, useEffect } from 'react'
import { useSeenTriggers } from '../../hooks/useSeenTriggers'

const TOOLTIP_MESSAGES = {
  first_property: 'This property is unowned! Click BUY to purchase or PASS to trigger an auction.',
  first_rent: "You landed on an owner's property. Rent was automatically paid.",
  first_doubles: 'DOUBLES! You get to roll again after this turn.',
  first_event: 'SASTA EVENT! These are random chaos cards. Expect anything!',
  first_jail: 'SERVER DOWNTIME! You\'re stuck. Pay $50 or wait 1 turn to escape.',
  low_cash: 'LOW CASH! You\'ll get the Stimulus Check — roll 3 dice, keep best 2!',
  first_auction: 'AUCTION! 10 seconds to bid. Click BID to raise by $10.',
  first_color_set: 'COLOR SET COMPLETE! Rent is now DOUBLED on these properties. You can also upgrade!',
}

export default function ContextualTooltip({ game, playerId, lastEventMessage }) {
  const { shouldShowTooltip, markSeen } = useSeenTriggers()
  const [tooltip, setTooltip] = useState(null)
  const [dismissed, setDismissed] = useState(false)

  const myPlayer = game?.players?.find((p) => p.id === playerId)
  const currentTile = myPlayer && game?.board
    ? game.board[myPlayer.position]
    : null
  const isMyTurn = game?.current_turn_player_id === playerId

  useEffect(() => {
    if (!game || !playerId || dismissed) return

    let trigger = null

    if (game.turn_phase === 'DECISION' && game.pending_decision?.type === 'BUY' && isMyTurn && shouldShowTooltip('first_property')) {
      trigger = 'first_property'
    } else if (lastEventMessage?.includes('Paid $') && lastEventMessage?.includes('rent') && shouldShowTooltip('first_rent')) {
      trigger = 'first_rent'
    } else if (game.last_dice_roll?.is_doubles && isMyTurn && shouldShowTooltip('first_doubles')) {
      trigger = 'first_doubles'
    } else if (lastEventMessage?.includes('SASTA') && currentTile?.type === 'CHANCE' && shouldShowTooltip('first_event')) {
      trigger = 'first_event'
    } else if (myPlayer?.in_jail && shouldShowTooltip('first_jail')) {
      trigger = 'first_jail'
    } else if (myPlayer?.cash < 100 && myPlayer?.cash >= 0 && isMyTurn && shouldShowTooltip('low_cash')) {
      trigger = 'low_cash'
    } else if (game.turn_phase === 'AUCTION' && game.auction_state && shouldShowTooltip('first_auction')) {
      trigger = 'first_auction'
    }

    if (trigger) {
      setTooltip({ trigger, message: TOOLTIP_MESSAGES[trigger] })
    } else {
      setTooltip(null)
    }
  }, [game?.turn_phase, game?.pending_decision, game?.last_dice_roll, game?.auction_state, lastEventMessage, currentTile?.type, myPlayer?.cash, myPlayer?.in_jail, isMyTurn, playerId, dismissed])

  const handleDismiss = () => {
    if (tooltip) {
      markSeen(tooltip.trigger)
      setTooltip(null)
      setDismissed(true)
    }
  }

  useEffect(() => {
    setDismissed(false)
  }, [game?.turn_phase])

  if (!tooltip) return null

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 max-w-sm">
      <div className="bg-sasta-black text-sasta-accent border-2 border-sasta-accent p-3 shadow-brutal-lg">
        <p className="text-xs font-data mb-2">{tooltip.message}</p>
        <button
          onClick={handleDismiss}
          className="w-full bg-sasta-accent text-sasta-black px-2 py-1 font-data font-bold text-xs border-brutal-sm hover:bg-sasta-white transition-colors"
        >
          GOT IT
        </button>
      </div>
    </div>
  )
}
