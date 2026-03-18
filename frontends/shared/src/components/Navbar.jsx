import React from 'react'
import { SastaLogo } from '../assets/SastaAssets'

const Navbar = () => {
  return (
    <nav className="sticky top-0 z-40 bg-sasta-white border-b-4 border-sasta-black shadow-brutal">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SastaLogo accentColor="#00ff00" />
          <span className="text-xl font-bold font-zero">SASTASPACE</span>
        </div>

        <div className="flex items-center gap-4">
          <a
            href="https://github.com/mkhare/sastaspace"
            target="_blank"
            rel="noopener noreferrer"
            className="border-brutal-sm bg-sasta-black text-sasta-white px-6 py-2 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors"
          >
            GITHUB
          </a>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
