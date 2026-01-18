# SastaDice: In-Game Rules Content

> **Design Philosophy**: "Learn As You Play" — No rulebook, UI explains in context

---

## 📋 RULES MODAL SECTIONS

### Section 1: How to Win
```
🎯 HOW TO WIN

Be the LAST PLAYER STANDING
   OR
Have the MOST CASH when Turn 30 hits

Bankrupt = You're out!
Sudden Death = Richest takes all!
```

---

### Section 2: Your Turn
```
🎲 YOUR TURN (30 seconds!)

1️⃣ PRE-ROLL (Optional)
   • Trade properties with others
   • Upgrade your properties
   • Use Black Market items

2️⃣ ROLL & MOVE
   • Roll 2 dice, move clockwise
   • Pass GO = Collect salary

3️⃣ RESOLVE
   • Unowned property? BUY or AUCTION
   • Owned by others? PAY RENT
   • Your property? Safe!
   • Event tile? Face the chaos

4️⃣ END TURN
   • Auto-ends after resolution
   • Roll doubles? Go again!
```

---

### Section 3: Properties & Rent
```
🏠 PROPERTIES

BUYING
• Land on unowned = First dibs
• Pass? = 10-second AUCTION starts
• Everyone can bid (+$10 each)

RENT
• Land on owned = Pay rent to owner
• Base rent = 25% of property price

COLOR SETS
• Own ALL properties of one color
• DOUBLE rent on that color!
• Required for upgrades
```

---

### Section 4: Upgrades
```
🔧 UPGRADES ("Hacks")

Requirement: Own full color set

LEVEL 1: SCRIPT KIDDIE
• Cost: 50% of property price
• Rent: +50%

LEVEL 2: 1337 HAXXOR
• Cost: 100% of property price  
• Rent: +200%

Max 2 levels per property!
```

---

### Section 5: Special Tiles
```
⬛ CORNER TILES

🟢 GO (Start)
   Pass = Collect salary
   Salary = $200 + $20 per round

⚡ THE GLITCH (25%)
   Teleport to random unowned tile!
   All owned? Go to event tile

🔴 SERVER DOWNTIME (50%)
   Jail! Stuck for 1 turn
   Pay $50 = Instant release
   Roll doubles = Free escape

🟣 BLACK MARKET (75%)
   Buy 1 buff (hold max 1):
   • VPN ($200): Block next rent
   • DDoS ($150): Shut down a tile
   • Peek ($100): See next 3 events
```

---

### Section 6: Events
```
🎲 SASTA EVENTS

Land on event tile = Draw random card

EXAMPLES:
💰 "Startup Funding" = +$200
💸 "Rug Pull" = -$200
🚶 "Auto Strike" = Move back 3
🏠 "DDoS Attack" = Disable a property
🎯 "Identity Theft" = Swap cash with someone
🌍 "Market Crash" = All rent halved

36 cards total — expect chaos!
```

---

### Section 7: Bankruptcy
```
💀 GOING BROKE

CAN'T PAY RENT?
1. FIRE SALE starts automatically
2. Your cheapest property sells at 50%
3. Repeat until debt paid

STILL CAN'T PAY?
• You're BANKRUPT!
• Your cash goes to creditor
• Properties reset to unowned
• State Auction begins!

⚠️ Creditor doesn't get your properties
   (Prevents snowballing!)
```

---

### Section 8: Pro Tips
```
💡 PRO TIPS

🎯 CHEAP PROPERTIES = HIGH ROI
   Brown/Light Blue rent out fast

🎯 COLOR SETS = POWER
   2x rent is game-changing

🎯 SAVE CASH FOR AUCTIONS
   Snipe properties for cheap!

🎯 USE BUFFS WISELY
   VPN can save you from bankruptcy

🎯 WATCH THE ROUND COUNTER
   Sudden Death at Turn 30!
```

---

## 🔔 CONTEXTUAL TOOLTIPS

### First-Time Triggers

| Trigger | Tooltip |
|---------|---------|
| First property landing | "This property is unowned! Click BUY to purchase or PASS to trigger an auction." |
| First rent payment | "You landed on {owner}'s property. Rent of ${amount} was automatically paid." |
| First doubles | "DOUBLES! You get to roll again after this turn." |
| First event | "SASTA EVENT! These are random chaos cards. Expect anything!" |
| First jail | "SERVER DOWNTIME! You're stuck. Pay $50 or wait 1 turn to escape." |
| Cash below $100 | "LOW CASH! You'll get the Stimulus Check — roll 3 dice, keep best 2!" |
| First auction | "AUCTION! 10 seconds to bid. Click BID to raise by $10." |
| First color set | "COLOR SET COMPLETE! Rent is now DOUBLED on these properties. You can also upgrade!" |

---

## 📱 TOAST MESSAGES

### Action Confirmations

| Action | Toast |
|--------|-------|
| Buy property | "🏠 Bought '{name}' for ${price}!" |
| Win auction | "🔨 Won auction for '{name}' at ${price}!" |
| Pay rent | "💸 Paid ${amount} to {owner}" |
| Collect rent | "💰 Received ${amount} from {payer}" |
| Pass GO | "🚀 Salary collected: ${amount}" |
| Upgrade L1 | "🔧 Upgraded to SCRIPT KIDDIE!" |
| Upgrade L2 | "🔧 Upgraded to 1337 HAXXOR!" |
| Fire sale | "🔥 FIRE SALE: Sold {name} for ${price}" |
| Bankruptcy | "💀 {player} went BANKRUPT!" |
| Jail entry | "🚨 {player} sent to SERVER DOWNTIME!" |
| Jail exit | "✅ {player} released from SERVER DOWNTIME" |
| Teleport | "⚡ GLITCH! Teleported to {tile}!" |
| Buff bought | "🛒 Bought {buff} from Black Market!" |
| Buff used | "✨ {buff} activated!" |

---

## 🎮 GAME STATE MESSAGES

### Phase Indicators

| Phase | Message |
|-------|---------|
| PRE_ROLL | "Your turn! Roll the dice or manage properties." |
| DECISION | "Choose: BUY for ${price} or PASS to auction" |
| AUCTION | "AUCTION! {time}s left — BID or wait" |
| POST_TURN | "Click END TURN to finish" |
| WAITING | "Waiting for {player}..." |
| CPU_TURN | "🤖 {cpu} is thinking..." |

### End Game

| Condition | Message |
|-----------|---------|
| Bankruptcy win | "🏆 {winner} WINS! Last player standing!" |
| Sudden death | "⏰ TURN 30! {winner} wins with ${cash}!" |
| Tie | "🏆 TIE! {player1} and {player2} share victory!" |

---

*Rules content designed for SastaDice "Learn As You Play" philosophy.*
