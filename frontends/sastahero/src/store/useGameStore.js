import { create } from 'zustand';

const API_BASE = '/api/v1/sastahero';

function getPlayerId() {
  let id = localStorage.getItem('sastahero_player_id');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('sastahero_player_id', id);
  }
  return id;
}

const useGameStore = create((set, get) => ({
  // Player
  playerId: getPlayerId(),

  // Stage
  cards: [],
  currentIndex: 0,
  stageNumber: 0,
  stagesCompleted: 0,
  isLoading: false,

  // Shards
  shards: { SOUL: 0, SHIELD: 0, VOID: 0, LIGHT: 0, FORCE: 0 },

  // Quiz
  showQuiz: false,
  quizQuestion: null,
  quizStreak: 0,

  // Collection
  collection: [],

  // Powerups
  activePowerups: [],

  // Swipe queue for optimistic UI
  pendingSwipes: [],

  // Milestone
  milestone: null,

  // Break suggestion
  showBreak: false,
  sessionStages: 0,

  // Last swipe result
  lastSwipeResult: null,

  initPlayer: () => {
    set({ playerId: getPlayerId() });
  },

  fetchStage: async () => {
    const { playerId } = get();
    set({ isLoading: true });
    try {
      const res = await fetch(`${API_BASE}/stage?player_id=${playerId}`);
      const data = await res.json();
      set({
        cards: data.cards,
        currentIndex: 0,
        stageNumber: data.stage_number,
        stagesCompleted: data.stages_completed,
        shards: data.shards,
        isLoading: false,
        showQuiz: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  processSwipe: async (direction) => {
    const { cards, currentIndex, playerId, shards, pendingSwipes } = get();
    const card = cards[currentIndex];
    if (!card) return;

    // Optimistic update
    const newShards = { ...shards };
    const shard_map = {
      CREATION: 'SOUL', PROTECTION: 'SHIELD', DESTRUCTION: 'VOID',
      ENERGY: 'LIGHT', POWER: 'FORCE',
    };

    if (direction === 'DOWN') {
      card.types.forEach(type => {
        const shard = shard_map[type];
        if (shard) newShards[shard] = (newShards[shard] || 0) + card.shard_yield;
      });
    }

    const nextIndex = currentIndex + 1;
    const isStageComplete = nextIndex >= cards.length;

    set({
      currentIndex: nextIndex,
      shards: newShards,
      lastSwipeResult: { direction, card },
      showQuiz: isStageComplete,
    });

    // Fire network request in background
    const swipeData = {
      player_id: playerId,
      card_id: card.card_id,
      action: direction,
    };

    try {
      const res = await fetch(`${API_BASE}/swipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(swipeData),
      });
      const data = await res.json();
      set({ shards: data.shards });
    } catch {
      // Queue for retry
      set({ pendingSwipes: [...get().pendingSwipes, swipeData] });
    }

    // Complete stage if done
    if (isStageComplete) {
      const { stageNumber, sessionStages } = get();
      try {
        const res = await fetch(
          `${API_BASE}/stage/${stageNumber}/complete?player_id=${playerId}`,
          { method: 'POST' }
        );
        const data = await res.json();
        const newSessionStages = sessionStages + 1;
        set({
          stagesCompleted: data.stages_completed,
          milestone: data.milestone,
          sessionStages: newSessionStages,
          showBreak: newSessionStages > 0 && newSessionStages % 3 === 0,
        });
      } catch {
        // silently continue
      }
    }
  },

  fetchQuiz: async () => {
    const { playerId } = get();
    try {
      const res = await fetch(`${API_BASE}/quiz?player_id=${playerId}`);
      const data = await res.json();
      set({ quizQuestion: data });
    } catch {
      set({ quizQuestion: null });
    }
  },

  submitQuizAnswer: async (questionId, selectedIndex, timeTakenMs) => {
    const { playerId } = get();
    try {
      const res = await fetch(`${API_BASE}/quiz/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player_id: playerId,
          question_id: questionId,
          selected_index: selectedIndex,
          time_taken_ms: timeTakenMs,
        }),
      });
      const data = await res.json();
      set({ quizStreak: data.streak_count });
      return data;
    } catch {
      return null;
    }
  },

  purchasePowerup: async (powerupType, shardType) => {
    const { playerId } = get();
    try {
      const res = await fetch(`${API_BASE}/powerup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player_id: playerId,
          powerup_type: powerupType,
          shard_type: shardType,
        }),
      });
      const data = await res.json();
      if (data.success) {
        set({ shards: data.shards, activePowerups: data.active_powerups });
      }
      return data;
    } catch {
      return { success: false };
    }
  },

  dismissMilestone: () => set({ milestone: null }),
  dismissBreak: () => set({ showBreak: false }),

  resetQuiz: () => set({ showQuiz: false, quizQuestion: null }),
}));

export default useGameStore;
