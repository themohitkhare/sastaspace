import React, { useState, useEffect, useCallback } from 'react';
import useGameStore from '../store/useGameStore';

export default function QuizCard() {
  const { quizQuestion, submitQuizAnswer, fetchStage, fetchQuiz, showQuiz } = useGameStore();
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [result, setResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(15);
  const [startTime] = useState(Date.now());

  useEffect(() => {
    if (showQuiz && !quizQuestion) {
      fetchQuiz();
    }
  }, [showQuiz, quizQuestion, fetchQuiz]);

  useEffect(() => {
    if (result || !quizQuestion) return;
    if (timeLeft <= 0) {
      handleAnswer(-1);
      return;
    }
    const timer = setTimeout(() => setTimeLeft(t => t - 1), 1000);
    return () => clearTimeout(timer);
  }, [timeLeft, result, quizQuestion]);

  const handleAnswer = useCallback(async (index) => {
    if (result) return;
    const timeTaken = Date.now() - startTime;
    setSelectedIndex(index);
    const res = await submitQuizAnswer(
      quizQuestion.question_id,
      Math.max(0, index),
      timeTaken,
    );
    setResult(res);
  }, [result, startTime, quizQuestion, submitQuizAnswer]);

  const handleContinue = () => {
    setSelectedIndex(null);
    setResult(null);
    setTimeLeft(15);
    fetchStage();
  };

  if (!quizQuestion) {
    return (
      <div data-testid="quiz-loading" role="status" className="w-full h-full flex items-center justify-center bg-black text-white">
        <p className="text-xl font-bold">Loading quiz...</p>
      </div>
    );
  }

  return (
    <div data-testid="quiz-card" role="region" aria-label="Quiz question" className="w-full h-full flex flex-col items-center justify-center bg-black text-white p-6">
      {/* Timer */}
      <div data-testid="quiz-timer" aria-label={`${timeLeft} seconds remaining`} aria-live="polite">
        <div className={`text-4xl font-bold ${timeLeft <= 5 ? 'text-red-500 animate-pulse' : 'text-white'}`}>
          {timeLeft}
        </div>
      </div>

      {/* Question */}
      <h2 className="text-xl font-bold text-center mb-8 max-w-md mt-6" data-testid="quiz-question">
        {quizQuestion.question}
      </h2>

      {/* Options */}
      <div className="w-full max-w-md space-y-3" role="group" aria-label="Answer options">
        {quizQuestion.options.map((option, i) => {
          let btnClass = 'w-full p-4 text-left border-2 border-white font-bold transition-colors';
          if (result) {
            if (i === result.correct_index) btnClass += ' bg-green-600 border-green-400';
            else if (i === selectedIndex && !result.correct) btnClass += ' bg-red-600 border-red-400';
            else btnClass += ' opacity-40';
          } else {
            btnClass += ' hover:bg-white hover:text-black';
          }

          return (
            <button
              key={i}
              data-testid={`quiz-option-${i}`}
              className={btnClass}
              onClick={() => handleAnswer(i)}
              disabled={!!result}
              aria-label={`Option ${i + 1}: ${option}`}
            >
              {option}
            </button>
          );
        })}
      </div>

      {/* Result */}
      {result && (
        <div className="mt-6 text-center" data-testid="quiz-result" role="alert">
          <p className={`text-lg font-bold ${result.correct ? 'text-green-400' : 'text-red-400'}`}>
            {result.correct ? 'Correct!' : 'Wrong!'}
          </p>
          <p className="text-sm mt-1">+{result.reward_shards} shards</p>
          {result.bonus_card && <p className="text-sm text-yellow-400">Bonus card next stage!</p>}
          <button
            data-testid="quiz-continue"
            className="mt-4 px-6 py-3 bg-white text-black font-bold border-2 border-white hover:bg-gray-200"
            onClick={handleContinue}
          >
            NEXT STAGE
          </button>
        </div>
      )}
    </div>
  );
}
