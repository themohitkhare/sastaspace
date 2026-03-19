import { useState } from 'react'

const SECTIONS = [
  {
    id: 'how-to-win',
    title: '🎯 HOW TO WIN',
    content: `Be the LAST PLAYER STANDING
   OR
Have the MOST CASH when Turn 30 hits

Bankrupt = You're out!
Sudden Death = Richest takes all!`
  },
  {
    id: 'your-turn',
    title: '🎲 YOUR TURN (30 seconds!)',
    content: `1️⃣ PRE-ROLL (Optional)
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
   • Roll doubles? Go again!`
  },
  {
    id: 'properties',
    title: '🏠 PROPERTIES',
    content: `BUYING
• Land on unowned = First dibs
• Pass? = 10-second AUCTION starts
• Everyone can bid (+$10 each)

RENT
• Land on owned = Pay rent to owner
• Base rent = 25% of property price

COLOR SETS
• Own ALL properties of one color
• DOUBLE rent on that color!
• Required for upgrades`
  },
  {
    id: 'upgrades',
    title: '🔧 UPGRADES ("Hacks")',
    content: `Requirement: Own full color set

LEVEL 1: SCRIPT KIDDIE
• Cost: 50% of property price
• Rent: +50%

LEVEL 2: 1337 HAXXOR
• Cost: 100% of property price  
• Rent: +200%

Max 2 levels per property!`
  },
  {
    id: 'special-tiles',
    title: '⬛ SPECIAL TILES',
    content: `GO (START) — Collect salary every time you pass.
Salary = Base ($200) + ($20 × Round Number)
Capped at 3× base to prevent runaway inflation.

THE GLITCH (25%) — Teleports you to a random unowned property or chance tile. Chaos is a feature.

SERVER DOWNTIME (50%) — This is jail.
• Land here = just visiting (safe)
• Sent here by 404 or event = locked up
• Escape: Pay $50 bribe OR roll doubles (max attempts from settings)

BLACK MARKET (75%) — Buy one-use power-ups:
• VPN ($200) — Blocks next rent payment against you
• DDoS ($150) — Disable any tile for 1 round
• Insider Info ($100) — Peek at next 3 event cards

SERVER NODES — Railroad equivalents.
Rent scales exponentially: $50 × 2^(nodes_owned - 1)
Own all 4 = $400 rent per landing.

404: ACCESS DENIED — Go directly to Server Downtime (jail). Do not pass GO. Do not collect salary.

TAX TILES — Pay the posted tax amount or half your GO bonus, whichever applies.

SASTA EVENTS (CHANCE) — Draw from the event deck. 35 possible events ranging from cash windfalls to hostile takeovers.`
  },
  {
    id: 'events',
    title: '🎲 SASTA EVENTS',
    content: `Land on event tile = Draw random card

EXAMPLES:
💰 "Startup Funding" = +$200
💸 "Rug Pull" = -$200
🚶 "Auto Strike" = Move back 3
🏠 "DDoS Attack" = Disable a property
🎯 "Identity Theft" = Swap cash with someone
🌍 "Market Crash" = All rent halved

36 cards total — expect chaos!`
  },
  {
    id: 'bankruptcy',
    title: '💀 GOING BROKE',
    content: `CAN'T PAY RENT?
1. FIRE SALE starts automatically
2. Your cheapest property sells at 50%
3. Repeat until debt paid

STILL CAN'T PAY?
• You're BANKRUPT!
• Your cash goes to creditor
• Properties reset to unowned
• State Auction begins!

⚠️ Creditor doesn't get your properties
   (Prevents snowballing!)`
  },
  {
    id: 'pro-tips',
    title: '💡 PRO TIPS',
    content: `🎯 CHEAP PROPERTIES = HIGH ROI
   Brown/Light Blue rent out fast

🎯 COLOR SETS = POWER
   2x rent is game-changing

🎯 SAVE CASH FOR AUCTIONS
   Snipe properties for cheap!

🎯 USE BUFFS WISELY
   VPN can save you from bankruptcy

🎯 WATCH THE ROUND COUNTER
   Sudden Death at Turn 30!`
  }
]

export default function RulesModal({ isOpen, onClose }) {
  const [activeSection, setActiveSection] = useState(SECTIONS[0].id)

  if (!isOpen) return null

  const currentSection = SECTIONS.find(s => s.id === activeSection) || SECTIONS[0]

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-sasta-white border-brutal-lg p-6 max-w-4xl w-full max-h-[90vh] flex flex-col shadow-brutal-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4 shrink-0">
          <h2 className="font-zero font-bold text-2xl text-sasta-black">
            📖 HOW TO PLAY
          </h2>
          <button
            onClick={onClose}
            className="font-zero font-bold text-3xl text-sasta-black hover:text-red-600 transition-colors"
          >
            ×
          </button>
        </div>

        <div className="flex gap-4 flex-1 min-h-0 overflow-hidden">
          <div className="w-48 shrink-0 border-r-2 border-sasta-black pr-4 overflow-y-auto">
            <nav className="space-y-1">
              {SECTIONS.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full text-left px-3 py-2 font-data text-sm font-bold transition-colors ${
                    activeSection === section.id
                      ? 'bg-sasta-accent text-sasta-black border-brutal-sm'
                      : 'bg-sasta-white text-sasta-black hover:bg-sasta-black/5 border border-transparent'
                  }`}
                >
                  {section.title}
                </button>
              ))}
            </nav>
          </div>

          <div className="flex-1 overflow-y-auto pr-2">
            <div className="bg-sasta-white p-4 border-brutal-sm">
              <h3 className="font-zero font-bold text-xl mb-4 text-sasta-black">
                {currentSection.title}
              </h3>
              <pre className="font-data text-sm text-sasta-black whitespace-pre-wrap leading-relaxed">
                {currentSection.content}
              </pre>
            </div>
          </div>
        </div>

        <div className="mt-4 shrink-0 pt-4 border-t-2 border-sasta-black">
          <button
            onClick={onClose}
            className="w-full py-3 px-4 bg-sasta-black text-sasta-accent font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  )
}
