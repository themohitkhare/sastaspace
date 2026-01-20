# Prompt: Redesign VictoryScreen with Brutalist Aesthetic

## Context
The VictoryScreen component (`frontends/sastadice/src/components/game/VictoryScreen.jsx`) currently uses a cyberpunk/neon aesthetic that doesn't match the Brutalist design system used throughout the rest of the application (GamePage, LobbyView, and other components).

## Design System Reference

### Brutalist Aesthetic Principles
1. **Sharp, Geometric Forms**: No rounded corners. Use hard edges and rectangular shapes.
2. **High Contrast**: Black and white with accent color (`sasta-accent`).
3. **Bold Typography**: 
   - `font-zero` for headings (bold, uppercase, tight tracking)
   - `font-data` for body text (monospace-like)
   - Uppercase text with tight tracking (`tracking-tighter`)
4. **Hard Shadows**: Use `shadow-brutal-sm` and `shadow-brutal-lg` classes, or hard drop shadows like `shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]`
5. **Thick Borders**: Use `border-brutal-sm`, `border-brutal-lg`, or `border-2 border-black`
6. **No Gradients**: Avoid gradient backgrounds/text. Use solid colors.
7. **No Blur/Glow**: Remove backdrop-blur, drop-shadow glows, and soft shadows.
8. **Grid-Based Layout**: Use grid or flex with clear geometric divisions.

### Color Palette (from tailwind.config.js)
- Background: `bg-sasta-white` (#FFFFFF) or `bg-white`
- Primary: `bg-sasta-black` (#000000) or `bg-black`
- Accent: `bg-sasta-accent` (#00ff00 - bright green)
- Text on black: `text-sasta-accent` (#00ff00) or `text-white`
- Text on white: `text-sasta-black` (#000000) or `text-black`
- Borders: `border-black` or `border-sasta-black`

### Shadow Classes (from tailwind.config.js)
- `shadow-brutal-sm`: `2px 2px 0px 0px #000`
- `shadow-brutal`: `4px 4px 0px 0px #000`
- `shadow-brutal-lg`: `6px 6px 0px 0px #000`

### Typography Classes (from tailwind.config.js)
- Font families:
  - `font-zero`: Courier New, Fira Code, monospace (for headings)
  - `font-data`: JetBrains Mono, Roboto Mono, monospace (for body)
- Headings: `font-zero font-bold text-xl` (or larger)
- Body: `font-data text-xs` or `font-data text-sm`
- Uppercase: Always use `uppercase` class
- Tracking: `tracking-tighter` or `tracking-widest` for emphasis

### Button Styles
```jsx
className="bg-sasta-black text-sasta-accent px-4 py-2 font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all"
```

### Card/Container Styles
```jsx
className="bg-sasta-white border-brutal-lg shadow-brutal-lg p-6"
// or
className="bg-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-4"
```

## Current Issues to Fix

1. **Remove Cyberpunk Elements:**
   - Remove green neon colors (`#22c55e`, `#166534`, `text-green-500`)
   - Remove gradient text (`bg-clip-text bg-gradient-to-b`)
   - Remove glow effects (`drop-shadow-[0_0_10px_rgba(...)]`)
   - Remove scanline effects
   - Remove grid overlay effects
   - Remove radial gradient overlays

2. **Replace with Brutalist Elements:**
   - Use `sasta-white` background instead of black
   - Use `sasta-black` for text/accents instead of green
   - Use `sasta-accent` for highlights
   - Replace soft shadows with `shadow-brutal-*` classes
   - Replace rounded borders with `border-brutal-*` or `border-2 border-black`
   - Remove backdrop-blur effects

3. **Typography Updates:**
   - Change all headings to use `font-zero` instead of mixed fonts
   - Use `font-data` for body text
   - Make text uppercase where appropriate
   - Use tight tracking (`tracking-tighter`)

4. **Layout Structure:**
   - Use grid-based layout similar to LobbyView
   - Create clear geometric sections
   - Use `divide-black` or `border-2 border-black` for separators
   - Remove gradient overlays

5. **Button Redesign:**
   - Primary action: `bg-sasta-accent text-sasta-black` with brutal borders
   - Secondary action: `bg-sasta-black text-sasta-accent` with brutal borders
   - Use brutalist hover effects: `hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none`

6. **Winner Card:**
   - Replace `bg-zinc-900/90 backdrop-blur-md` with `bg-sasta-white` or `bg-white`
   - Replace `border-4 border-green-500` with `border-brutal-lg` or `border-2 border-black`
   - Replace soft shadow with `shadow-brutal-lg`
   - Remove corner accent squares (or make them brutalist if kept)
   - Remove scanline overlay

7. **Stats Section:**
   - Replace `bg-black border border-zinc-800` with `bg-sasta-white border-2 border-black`
   - Use brutalist typography
   - Remove soft transitions, use hard edges

8. **Confetti:**
   - Keep confetti but change colors to match brutalist palette (black, white, sasta-accent)
   - Or remove if it conflicts with aesthetic

## Implementation Requirements

1. **Maintain Functionality**: All existing functionality must remain (showStats toggle, onPlayAgain, onBackToLobby callbacks)

2. **Responsive Design**: Maintain responsive behavior for mobile/desktop

3. **Accessibility**: Keep semantic HTML and proper contrast ratios

4. **File Location**: Edit `frontends/sastadice/src/components/game/VictoryScreen.jsx`

5. **Dependencies**: Keep existing imports (useState, useEffect, Confetti)

## Example Brutalist Victory Screen Structure

```jsx
<div className="fixed inset-0 bg-sasta-white z-50 overflow-hidden flex flex-col">
  {/* Optional: Confetti with brutalist colors */}
  <Confetti colors={['#000000', '#FFFF00', '#FFFFFF']} />
  
  {/* Header Section - Brutalist */}
  <div className="border-b-2 border-black p-6 bg-sasta-white">
    <h1 className="text-6xl font-zero font-black tracking-tighter uppercase text-sasta-black">
      VICTORY
    </h1>
  </div>
  
  {/* Winner Card - Brutalist */}
  <div className="flex-1 flex items-center justify-center p-6">
    <div className="bg-sasta-white border-brutal-lg shadow-brutal-lg p-8 max-w-2xl w-full">
      {/* Winner avatar and info with brutalist styling */}
    </div>
  </div>
  
  {/* Stats Section - Brutalist */}
  <div className="border-t-2 border-black bg-sasta-white p-6">
    {/* Brutalist stats display */}
  </div>
  
  {/* Action Buttons - Brutalist */}
  <div className="border-t-2 border-black p-6 bg-sasta-white flex gap-4">
    <button className="flex-1 bg-sasta-accent text-sasta-black border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none font-zero font-bold uppercase py-4">
      PLAY AGAIN
    </button>
    <button className="flex-1 bg-sasta-black text-sasta-accent border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none font-zero font-bold uppercase py-4">
      RETURN TO LOBBY
    </button>
  </div>
</div>
```

## Reference Components
- Look at `LobbyView.jsx` for grid layout and brutalist card styling
- Look at `CenterActionButton.jsx` for brutalist button styling
- Look at `GamePage.jsx` for overall brutalist aesthetic patterns

## Deliverable
Redesign the VictoryScreen component to match the Brutalist aesthetic while maintaining all existing functionality. The screen should feel cohesive with the rest of the application's design language.
