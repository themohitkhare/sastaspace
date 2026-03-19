/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'zero': ['Courier New', 'Fira Code', 'monospace'],
      },
      colors: {
        'sasta-black': '#000000',
        'sasta-white': '#FFFFFF',
        'sasta-accent': '#ff6600',
      },
      boxShadow: {
        'brutal': '4px 4px 0px 0px #000',
        'brutal-sm': '2px 2px 0px 0px #000',
        'brutal-lg': '6px 6px 0px 0px #000',
        'brutal-white': '4px 4px 0px 0px #fff',
        'brutal-white-sm': '2px 2px 0px 0px #fff',
      },
      animation: {
        'shard-bump': 'shard-bump 0.2s ease-out',
        'streak-fire': 'streak-fire 1.5s ease-in-out infinite',
        'card-breathe': 'card-breathe 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
