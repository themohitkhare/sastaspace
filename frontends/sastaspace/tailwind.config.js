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
        'sasta-accent': '#00ff00', // Neon Green - can be swapped to #ff6600 (Warning Orange)
      },
      boxShadow: {
        'brutal': '4px 4px 0px 0px #000',
        'brutal-sm': '2px 2px 0px 0px #000',
        'brutal-lg': '6px 6px 0px 0px #000',
      },
    },
  },
  plugins: [],
}
