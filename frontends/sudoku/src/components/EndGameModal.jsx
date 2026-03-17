/**
 * EndGameModal — shown when the match ends (player win or AI win).
 *
 * Props:
 *   status: 'player_won' | 'ai_won'
 *   onPlayAgain: () => void
 */
export default function EndGameModal({ status, onPlayAgain }) {
  const isWin = status === 'player_won';

  return (
    <div className="modal-backdrop" data-testid="end-game-modal">
      <div className="modal">
        <h2 className={isWin ? 'win' : 'lose'}>
          {isWin ? '🎉 You Win!' : '🤖 AI Wins!'}
        </h2>
        <p>
          {isWin
            ? 'Congratulations! You solved the puzzle before the genetic algorithm.'
            : 'The AI evolved a perfect solution. Better luck next time!'}
        </p>
        <button className="btn-primary" onClick={onPlayAgain}>
          Play Again
        </button>
      </div>
    </div>
  );
}
