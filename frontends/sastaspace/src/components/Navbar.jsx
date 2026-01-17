import React, { useState } from 'react'
import { SastaLogo } from './assets/SastaAssets'
import { UserAvatar } from './assets/SastaAssets'
import AuthModal from './AuthModal'
import useAuthStore from '../store/useAuthStore'

/**
 * Navbar - Sticky top navigation with logo and auth controls
 * Neo-Brutalist styling with thick borders and hard shadows
 */
const Navbar = () => {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  return (
    <>
      <nav className="sticky top-0 z-40 bg-sasta-white border-b-4 border-sasta-black shadow-brutal">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Left: Logo */}
          <div className="flex items-center gap-3">
            <SastaLogo accentColor="#00ff00" />
            <span className="text-xl font-bold font-zero">SASTASPACE</span>
          </div>

          {/* Right: Auth controls */}
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <UserAvatar size={32} />
                <span className="text-sm font-zero font-bold">{user?.email}</span>
                <button
                  onClick={logout}
                  className="border-brutal-sm bg-sasta-black text-sasta-white px-4 py-2 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors"
                >
                  LOGOUT
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="border-brutal-sm bg-sasta-black text-sasta-white px-6 py-2 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors"
              >
                LOGIN
              </button>
            )}
          </div>
        </div>
      </nav>

      <AuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />
    </>
  )
}

export default Navbar
