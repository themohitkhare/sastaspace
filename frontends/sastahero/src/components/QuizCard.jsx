import React, { useState, useEffect, useCallback } from 'react';
import useGameStore from '../store/useGameStore';

export default function QuizCard() {
  const { quizQuestion, submitQuizAnswer, fetchStage, fetchQuiz, showQuiz } = useGameStore();
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [result, setResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(15);
  const [startTime] = useState(Date.now());
  const [flashClass, setFlashClass] = useState('');
  const [shakeClass, setShakeClass] = useState('');

  useEffect(() => {
    if (showQuiz && !quizQuestion) fetchQuiz();
  }, [showQuiz, quizQuestion, fetchQuiz]);

  useEffect(() => {
    if (result || !quizQuestion) return;
    if (timeLeft <= 0) { handleAnswer(-1); return; }
    const timer = setTimeout(() => setTimeLeft(t => t - 1), 1000);
    return () => clearTimeout(timer);
  }, [timeLeft, result, quizQuestion]);

  const handleAnswer = useCallback(async (index) => {
    if (result) return;
    const timeTaken = Date.now() - startTime;
    setSelectedIndex(index);
    const res = await submitQuizAnswer(quizQuestion.question_id, index, timeTaken);
    setResult(res);
    if (res?.correct) { setFlashClass('flash-green'); setShakeClass('screen-shake'); }
    else { setFlashClass('flash-red'); setShakeClass('card-shudder'); }
    setTimeout(() => { setFlashClass(''); setShakeClass(''); }, 500);
  }, [result, startTime, quizQuestion, submitQuizAnswer]);

  const handleContinue = () => {
    setSelectedIndex(null); setResult(null); setTimeLeft(15);
    setFlashClass(''); setShakeClass(''); fetchStage();
  };

  if (!quizQuestion) {
    return (<div data-testid="quiz-loading" role="status" className="w-full h-full flex items-center justify-center bg-black text-white"><p className="text-xl font-bold font-zero">LOADING QUIZ...</p></div>);
  }

  return (
    <div data-testid="quiz-card" role="region" aria-label="Quiz question" className={`w-full h-full flex flex-col items-center justify-center bg-black text-white p-6 ${flashClass}`}>
      <div data-testid="quiz-timer" aria-label={`${timeLeft} seconds remaining`} aria-live="polite">
        <div className={`text-4xl font-bold font-zero border-brutal-sm px-4 py-2 ${timeLeft <= 5 ? 'timer-urgent border-red-500' : 'text-white border-white'}`}>{timeLeft}</div>
      </div>
      <h2 className={`text-xl font-bold font-zero text-center mb-8 max-w-md mt-6 uppercase tracking-wider ${shakeClass}`} data-testid="quiz-question">{quizQuestion.question}</h2>
      <div className="w-full max-w-md space-y-3" role="group" aria-label="Answer options">
        {quizQuestion.options.map((option, i) => {
          let btnClass = 'w-full p-4 text-left border-brutal font-bold font-zero transition-colors';
          if (result) {
            if (i === result.correct_index) btnClass += ' bg-green-600 border-green-400 text-white';
            else if (i === selectedIndex && !result.correct) btnClass += ' bg-red-600 border-red-400 text-white';
            else btnClass += ' opacity-40';
          } else { btnClass += ' bg-black text-white hover:bg-sasta-accent hover:text-black'; }
          return (<button key={i} data-testid={`quiz-option-${i}`} className={btnClass} onClick={() => handleAnswer(i)} disabled={!!result} aria-label={`Option ${i + 1}: ${option}`}>{option}</button>);
        })}
      </div>
      {result && (
        <div className="mt-6 text-center" data-testid="quiz-result" role="alert">
          <p className={`text-lg font-bold font-zero ${result.correct ? 'text-green-400' : 'text-red-400'}`}>{result.correct ? 'CORRECT!' : 'WRONG!'}</p>
          <p className="text-sm font-zero mt-1">+{result.reward_shards} SHARDS</p>
          {result.bonus_card && <p className="text-sm text-sasta-accent font-zero font-bold">BONUS CARD NEXT STAGE!</p>}
          <button data-testid="quiz-continue" className="mt-4 px-6 py-3 bg-sasta-accent text-black font-bold font-zero border-brutal hover:bg-white transition-colors" onClick={handleContinue}>NEXT STAGE</button>
        </div>
      )}
    </div>
  );
}
