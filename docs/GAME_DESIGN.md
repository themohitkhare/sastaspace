# SastaDice Game Design Bible

## Core Identity
- **Genre**: "Viral Discord Game" — Fast, meme-able, global audience (Among Us meets Monopoly)
- **Aesthetic**: Brutalist, Hacker, Vaporwave
- **Tone**: Cynical & Funny ("Subscription You Forgot To Cancel" instead of "Luxury Tax")
- **Target**: Discord groups, voice chat parties, 18-35 demographic
- **Session Length**: 20-30 minutes ("Lunch Break" standard)
- **Player Count**: 2-6 (Best at 4)

## Win Conditions (Hybrid)
1. **Bankruptcy**: Last player standing wins
2. **Sudden Death**: Turn 30 → Game ends immediately → Richest player wins

## Luck vs Strategy
- **Balance**: 40% Strategy / 60% Chaos
- **Design Goal**: "Blue Shell" moments where losing players can wreck the leader
- **Upsets Encouraged**: A player with $1 should feel they *might* still win

---

## 💰 ECONOMY SYSTEM

### Starting Cash
- **Formula**: `Tiles × $75`
- **Example (4 Players / 24 Tiles)**: $1,800 each

### GO Bonus ("Salary")
- **Base**: $200
- **Inflation**: +$20 per round completed
- **Example Round 10**: $400 for passing GO

### Property Tiers
| Tier | Colors | Price Range | Purpose |
|------|--------|-------------|---------|
| 1 | Brown, Light Blue | $60 - $120 | Cheap, high ROI |
| 2 | Pink, Orange, Red | $140 - $240 | Mid-range |
| 3 | Yellow, Green, Dark Blue | $260 - $400 | Premium, game-enders |

### Rent Mechanics
- **Base Rent**: Low (encourage ownership)
- **Set Bonus**: Own all properties of a color → Rent doubles
- **Upgrades ("Hacks")**: Only available when owning full color set

### Upgrade System
| Level | Name | Cost | Rent Increase |
|-------|------|------|---------------|
| 1 | Script Kiddie | 50% of property price | +50% rent |
| 2 | 1337 Haxxor | 100% of property price | +200% rent |

### Property Acquisition
1. **Land-to-Buy**: First chance to owner
2. **Decline**: Instant "Snipe Auction" begins

### Snipe Auction
- 10-second timer starts immediately
- Any player can bid
- Bids increase by fixed $10 increments
- Highest bidder when timer ends wins

### Bankruptcy ("Loot Drop")
- Bankrupt player's **cash** goes to creditor
- Bankrupt player's **properties** reset to UNOWNED
- Triggers immediate State Auction for each property

### Fire Sale (No Mortgage)
- If you can't pay rent: Game auto-sells your cheapest property for 50% price
- Repeats until debt is paid or you're bankrupt

---

## 🗺️ BOARD STRUCTURE

### Size Formula
- `(Player Count × 5) + 4 Corners`
- **Example (4 Players)**: 24 tiles (6 per side)

### Corner Tiles (Fixed)
| Position | Name | Effect |
|----------|------|--------|
| 0% (Start) | **GO** | Collect Salary when passing |
| 25% | **The Glitch** | Random teleport to unowned property |
| 50% | **Server Downtime** | Jail equivalent |
| 75% | **The Black Market** | Buy 1 active buff |

### Tile Distribution
- **Properties**: ~60% of tiles
- **Sasta Events**: ~25% of tiles (1 in 4)
- **Tax/Special**: ~15% of tiles

### Color Sets
- Every color has exactly **2 or 3 properties**
- Colors assigned dynamically at game start

### User-Generated Tiles
- Players submit tile NAMES (the meme content)
- Engine assigns: type, price, color, position

---

## 🏢 SPECIAL TILES

### Server Downtime (Jail)
**Entry**:
- Land on "404 Error" corner tile
- Roll doubles 3 times in a row

**Exit**:
- Pay $50 "Bribe" (immediate release)
- Roll doubles (free release)
- Wait 1 turn (MAX)

### The Glitch (Teleport)
- Teleport to random UNOWNED property
- If all owned: Teleport to random Sasta Event tile

### The Black Market
| Buff | Name | Cost | Effect |
|------|------|------|--------|
| VPN | Immunity | $200 | Block next rent payment |
| DDoS | Blockade | $150 | Choose a tile, no rent for 1 round |
| Insider Info | Peek | $100 | See top 3 event cards |

---

## 🃏 SASTA EVENTS

### Design Philosophy
- **"Take-That" Mechanics**: Aggressive player interaction
- **Instant Use**: No hoarding cards
- **Chaos Factor**: Events should create memorable moments

### Event Categories
- **Cash Gain** (5-8 cards)
- **Cash Loss** (5-8 cards)
- **Movement** (4-6 cards)
- **Property Effects** (4-6 cards)
- **Player Targeting** (4-6 cards)
- **Global Effects** (3-5 cards)

---

## ⏱️ TURN STRUCTURE

### Turn Timer
- **30 seconds hard limit**
- Timer expires: CPU auto-rolls, auto-passes

### Turn Phases
1. **Pre-Roll**: Trade, Upgrade, Use items
2. **Roll & Move**: Animation lock
3. **Resolution**: Buy/Auction/Pay/Event
4. **End**: Auto-ends (unless doubles)

### Doubles
- Roll doubles: Get another turn
- Roll doubles 3x: Go to Jail

---

## 🤝 PLAYER INTERACTION

### Trading
- Only on YOUR turn
- Prevents "Kingmaking"

### Catch-Up ("Stimulus Check")
- If < $100 at turn start
- Roll 3 dice, keep best 2

### Disconnection ("AFK Ghost")
- Assets frozen, auto-pays rent
- Does NOT collect rent
- 3 turns → Bankruptcy

---

## 🤖 CPU PLAYERS

- Minimum 2 entities required
- Named: "Chad Bot", "Karen.exe", "STONKS", "ROBOCOP"
- Buy if cash > price + $200 buffer
- Bid up to 80% of property value

---

## 📋 RULES UI

### "Learn As You Play"
- NO separate rulebook
- UI explains in context
- First-time tooltips

### Rules Menu Structure
1. How to Win
2. Your Turn
3. Properties & Rent
4. Upgrades
5. Special Tiles
6. Events
7. Bankruptcy

---

## 🎮 SUCCESS CRITERIA

1. 4-player game completes in under 30 minutes
2. Player with $100 can still potentially win
3. Every turn has meaningful decision
4. New players understand without explanation
5. Generates "clip-worthy" moments
