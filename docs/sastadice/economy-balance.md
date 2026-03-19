# SastaDice: Economy Balance Sheet

> **Design Target**: 20-30 minute games with meaningful decisions

---

## 💰 STARTING CONDITIONS

### Cash Formula
```
Starting Cash = Total Tiles × $75
```

| Players | Tiles | Starting Cash |
|---------|-------|---------------|
| 2 | 14 | $1,050 |
| 3 | 19 | $1,425 |
| 4 | 24 | $1,800 |
| 5 | 29 | $2,175 |
| 6 | 34 | $2,550 |

---

## 🏠 PROPERTY PRICING

### Tier System

| Tier | Colors | Price Range | Base Rent | % of Start |
|------|--------|-------------|-----------|------------|
| 1 | Brown, Light Blue | $60-$120 | $15-$30 | 3-7% |
| 2 | Pink, Orange, Red | $140-$240 | $35-$60 | 8-13% |
| 3 | Yellow, Green, Blue | $260-$400 | $65-$100 | 14-22% |

### Full Set Bonus
- **Rent × 2** when owning all properties of a color

### Upgrade Multipliers

| Level | Name | Cost | Rent Multiplier |
|-------|------|------|-----------------|
| 0 | None | - | 1.0× |
| 1 | Script Kiddie | 50% of price | 1.5× |
| 2 | 1337 Haxxor | 100% of price | 3.0× |

### Combined Rent Example

Property: "$200 Tier 2"
- Base rent: $50
- Full set: $100 (×2)
- Script Kiddie: $150 (×1.5)
- 1337 Haxxor: $300 (×3)
- Full set + 1337: $600 (×2 × ×3)

**Max possible rent from single property: $600** (30% of starting cash!)

---

## 🔄 CASH FLOW PER ROUND

### Income Sources

| Source | Amount | Frequency |
|--------|--------|-----------|
| Pass GO (base) | $200 | ~every 6 turns |
| GO Inflation | +$20/round | Cumulative |
| Rent collected | $15-$600 | Per landing |
| Events (positive) | $100-$300 | Random |
| Auction wins | Varies | Opportunistic |

### GO Bonus Progression

| Round | GO Bonus | Total Circulated (4P) |
|-------|----------|----------------------|
| 1 | $200 | $800 |
| 5 | $300 | $4,000 |
| 10 | $400 | $10,000 |
| 15 | $500 | $18,000 |
| 20 | $600 | $28,000 |
| 25 | $700 | $40,000 |
| 30 | $800 | $54,000 |

**Design Intent**: By round 20, so much cash circulates that players aggressively buy/upgrade, accelerating bankruptcies.

---

## 💸 EXPENSE SOURCES

| Expense | Amount | Impact |
|---------|--------|--------|
| Property purchase | $60-$400 | One-time |
| Rent payment | $15-$600 | Per landing |
| Upgrades | $30-$400 | Investment |
| Taxes | $50-$150 | Random tiles |
| Events (negative) | $50-$200 | Random |
| Jail bribe | $50 | Optional |
| Black Market | $100-$200 | Optional |

---

## 📊 BANKRUPTCY THRESHOLD ANALYSIS

### When Does Bankruptcy Happen?

Assume: 4 players, $1,800 starting cash

| Scenario | Required Bad Luck |
|----------|-------------------|
| Early (Turn 1-10) | 3+ consecutive high rents + no income |
| Mid (Turn 10-20) | Overinvested in upgrades + unlucky landings |
| Late (Turn 20-30) | Normal - expected 1-2 bankruptcies |

### Fire Sale Economics

- Sell price: 50% of purchase price
- Average property: $200 → Sells for $100
- Player with 3 properties has ~$300 "fire sale buffer"

### Bankruptcy Recovery Window

| Cash Needed | Properties to Sell | Survivable? |
|-------------|-------------------|-------------|
| $50 | 1 cheap | ✅ Yes |
| $150 | 1-2 | ✅ Yes |
| $300 | 2-3 | ⚠️ Barely |
| $500+ | 4+ | ❌ Likely bankrupt |

---

## 🎲 LUCK vs SKILL BUDGET

### Luck Components (60%)

| Mechanic | Chaos Level |
|----------|-------------|
| Dice movement | High |
| Event cards | High |
| Auction competition | Medium |
| Property distribution | Medium |

### Skill Components (40%)

| Mechanic | Strategy Level |
|----------|----------------|
| Buy/pass decisions | High |
| Auction bidding | High |
| Upgrade timing | Medium |
| Buff usage | Medium |
| Trade negotiation | High |

---

## ⚖️ CATCH-UP MECHANICS

### Stimulus Check

- Trigger: Cash < $100 at turn start
- Effect: Roll 3d6, keep best 2
- Average improvement: +1.5 movement (8.5 vs 7.0)
- Strategic impact: Better chance to land on unowned tiles

### Event Card Balance

| Type | Probability | Avg Impact |
|------|-------------|------------|
| Cash Gain | 22% | +$150 |
| Cash Loss | 22% | -$125 |
| Movement | 17% | Neutral |
| Property | 17% | Varies |
| Targeting | 17% | -$100 to target |
| Global | 11% | Chaotic |

**Net Expected Value**: Slightly positive (+$10) to keep losers hopeful

---

## 🏆 WIN CONDITION MATH

### Bankruptcy Path

Average turns to bankruptcy (when trailing):
- Aggressive economy: 8-12 turns
- Conservative economy: 15-20 turns

**Target**: First bankruptcy by turn 15-20

### Sudden Death (Turn 30)

If no bankruptcy by turn 30:
- Average cash per player: $3,000-$5,000
- Winner margin: Usually $500-$1,500 lead
- Decided by: Property portfolio value

---

## 🎮 SESSION LENGTH VALIDATION

### Model: 4 Players, 24 Tiles

| Phase | Turns | Real Time |
|-------|-------|-----------|
| Land Grab (0-10) | 10 | 5 min |
| Development (10-20) | 10 | 8 min |
| Conflict (20-30) | 10 | 10 min |
| **Total** | **30** | **~23 min** |

**✅ Within 20-30 minute target**

### Time Per Turn Breakdown

| Component | Time |
|-----------|------|
| Decision making | 10s |
| Dice animation | 2s |
| Movement animation | 3s |
| Resolution | 5s |
| Auction (if any) | 10s |
| **Average turn** | **20-30s** |

---

## 🔧 TUNING LEVERS

If games are too long:
- Increase GO inflation (+$30/round)
- Raise base rents (+50%)
- Lower auction timer (7s)

If games are too short:
- Decrease GO inflation (+$10/round)
- Lower base rents (-25%)
- Increase starting cash (+$200)

If rich get richer too fast:
- Add more aggressive targeting events
- Increase Fire Sale return (60%)
- Add "Robin Hood" event (steal from richest)

If comebacks are impossible:
- Buff Stimulus Check (roll 4d6, keep 2)
- Add "Bailout" event (+$500 to poorest)
- Reduce max upgrade rent (×2.5 instead of ×3)

---

*Balance sheet designed for SastaDice "20-minute chaos" target.*
