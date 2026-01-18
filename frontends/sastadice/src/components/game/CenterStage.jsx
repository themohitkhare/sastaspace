import DiceDisplay from './DiceDisplay'
import CenterActionButton from './CenterActionButton'
import TileCard from './TileCard'
import EventToast from './EventToast'

export default function CenterStage({
    lastDiceRoll,
    gameId,
    playerId,
    turnPhase,
    pendingDecision,
    isMyTurn,
    isCpuTurn,
    currentPlayer,
    currentTile,
    tileOwner,
    myPlayerCash,
    lastEventMessage,
    onActionComplete,
    myPlayer,
    onDdosActivate,
}) {
    return (
        <div className="w-full h-full flex flex-row">
            <div className="flex-[3] relative border-r-2 border-sasta-black p-2 flex flex-col items-center justify-center bg-sasta-white overflow-hidden">
                <div className="absolute top-2 left-2 right-2 flex flex-col gap-1 z-30 pointer-events-none">
                    <EventToast lastEventMessage={lastEventMessage} />
                </div>

                <div className="flex flex-col items-center justify-center gap-3 z-10">
                    <DiceDisplay lastDiceRoll={lastDiceRoll} size="large" />

                    {currentTile && (
                        <TileCard tile={currentTile} owner={tileOwner} isVisible />
                    )}
                </div>
            </div>

            <div className="flex-[2] flex flex-col justify-between p-3 bg-sasta-black text-sasta-accent min-w-[140px] max-w-[180px]">
                <div className="text-center border-b border-sasta-accent/30 pb-2">
                    <div className="text-[10px] font-data uppercase opacity-60 text-sasta-white">Current Turn</div>
                    {currentPlayer && (
                        <div className="flex items-center justify-center gap-2 mt-1">
                            <div
                                className="w-6 h-6 rounded-full border-2 border-white flex items-center justify-center font-data font-bold text-xs text-white"
                                style={{ backgroundColor: currentPlayer.color || '#000' }}
                            >
                                {currentPlayer.name?.charAt(0)?.toUpperCase()}
                            </div>
                            <span className="font-data font-bold text-sm text-sasta-white">
                                {currentPlayer.name?.toUpperCase()}
                            </span>
                        </div>
                    )}
                    {isMyTurn && (
                        <div className="text-[10px] font-data mt-1 bg-sasta-accent text-sasta-black px-2 py-0.5 inline-block">
                            YOUR TURN!
                        </div>
                    )}
                </div>

                <div className="text-center my-auto py-4">
                    <div className="text-[10px] font-data uppercase opacity-60 text-sasta-white mb-1">Your Stash</div>
                    <div className="text-3xl font-data font-bold text-white">
                        ${myPlayerCash?.toLocaleString() || '0'}
                    </div>
                </div>

                <div className="w-full">
                    <CenterActionButton
                        gameId={gameId}
                        playerId={playerId}
                        turnPhase={turnPhase}
                        pendingDecision={pendingDecision}
                        isMyTurn={isMyTurn}
                        isCpuTurn={isCpuTurn}
                        onActionComplete={onActionComplete}
                        myPlayer={myPlayer}
                        onDdosActivate={onDdosActivate}
                    />
                </div>

                <div className="text-center mt-2 pt-2 border-t border-sasta-accent/30">
                    <span className="text-[9px] font-data opacity-50 text-sasta-white">
                        {turnPhase?.replace('_', ' ') || 'WAITING'}
                    </span>
                </div>
            </div>
        </div>
    )
}
