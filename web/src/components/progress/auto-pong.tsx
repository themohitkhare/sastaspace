"use client";

import { useEffect, useRef } from "react";

interface AutoPongProps {
  width?: number;
  height?: number;
  className?: string;
}

export function AutoPong({ width = 320, height = 180, className }: AutoPongProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Colors matching site theme
    const AMBER = "#c8993a";
    const DIM = "rgba(200, 153, 58, 0.15)";
    const TEXT = "rgba(200, 153, 58, 0.4)";

    const PADDLE_W = 4;
    const PADDLE_H = 32;
    const BALL_R = 3;
    const PADDLE_SPEED = 2.5;

    let ballX = width / 2;
    let ballY = height / 2;
    let ballVX = 1.8 * (Math.random() > 0.5 ? 1 : -1);
    let ballVY = 1.2 * (Math.random() > 0.5 ? 1 : -1);

    let leftY = height / 2 - PADDLE_H / 2;
    let rightY = height / 2 - PADDLE_H / 2;
    let scoreL = 0;
    let scoreR = 0;

    function resetBall() {
      ballX = width / 2;
      ballY = height / 2;
      ballVX = 1.8 * (Math.random() > 0.5 ? 1 : -1);
      ballVY = 1.2 * (Math.random() * 2 - 1);
    }

    function movePaddle(paddleY: number, targetY: number): number {
      const center = paddleY + PADDLE_H / 2;
      const diff = targetY - center;
      // Add slight imperfection so it's not robotic
      const jitter = (Math.random() - 0.5) * 0.8;
      if (Math.abs(diff) > 2) {
        return paddleY + Math.sign(diff) * Math.min(PADDLE_SPEED, Math.abs(diff)) + jitter;
      }
      return paddleY;
    }

    let animId: number;

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);

      // Center line
      ctx.setLineDash([4, 6]);
      ctx.strokeStyle = DIM;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(width / 2, 0);
      ctx.lineTo(width / 2, height);
      ctx.stroke();
      ctx.setLineDash([]);

      // Score
      ctx.fillStyle = TEXT;
      ctx.font = "16px ui-monospace, monospace";
      ctx.textAlign = "center";
      ctx.fillText(String(scoreL), width / 2 - 24, 22);
      ctx.fillText(String(scoreR), width / 2 + 24, 22);

      // Paddles
      ctx.fillStyle = AMBER;
      ctx.fillRect(8, leftY, PADDLE_W, PADDLE_H);
      ctx.fillRect(width - 8 - PADDLE_W, rightY, PADDLE_W, PADDLE_H);

      // Ball
      ctx.beginPath();
      ctx.arc(ballX, ballY, BALL_R, 0, Math.PI * 2);
      ctx.fill();

      // AI paddle movement — track ball with slight delay
      leftY = movePaddle(leftY, ballX < width / 2 ? ballY : height / 2);
      rightY = movePaddle(rightY, ballX > width / 2 ? ballY : height / 2);

      // Clamp paddles
      leftY = Math.max(0, Math.min(height - PADDLE_H, leftY));
      rightY = Math.max(0, Math.min(height - PADDLE_H, rightY));

      // Ball movement
      ballX += ballVX;
      ballY += ballVY;

      // Top/bottom bounce
      if (ballY - BALL_R <= 0 || ballY + BALL_R >= height) {
        ballVY *= -1;
        ballY = Math.max(BALL_R, Math.min(height - BALL_R, ballY));
      }

      // Left paddle hit
      if (
        ballX - BALL_R <= 8 + PADDLE_W &&
        ballY >= leftY &&
        ballY <= leftY + PADDLE_H &&
        ballVX < 0
      ) {
        ballVX = Math.abs(ballVX) * 1.02;
        const offset = (ballY - (leftY + PADDLE_H / 2)) / (PADDLE_H / 2);
        ballVY = offset * 2;
      }

      // Right paddle hit
      if (
        ballX + BALL_R >= width - 8 - PADDLE_W &&
        ballY >= rightY &&
        ballY <= rightY + PADDLE_H &&
        ballVX > 0
      ) {
        ballVX = -Math.abs(ballVX) * 1.02;
        const offset = (ballY - (rightY + PADDLE_H / 2)) / (PADDLE_H / 2);
        ballVY = offset * 2;
      }

      // Scoring
      if (ballX < 0) {
        scoreR++;
        resetBall();
      }
      if (ballX > width) {
        scoreL++;
        resetBall();
      }

      // Cap ball speed
      const speed = Math.sqrt(ballVX * ballVX + ballVY * ballVY);
      if (speed > 4) {
        ballVX = (ballVX / speed) * 4;
        ballVY = (ballVY / speed) * 4;
      }

      animId = requestAnimationFrame(draw);
    }

    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }, [width, height]);

  return (
    <div className={className}>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label="Decorative Pong game animation"
        style={{ width, height }}
        className="rounded-lg border border-border/50"
      />
      <p className="text-[10px] text-muted-foreground/50 text-center mt-1">
        AI vs AI
      </p>
    </div>
  );
}
