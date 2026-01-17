import React, { useState } from 'react'
import { X } from 'lucide-react'
import useAuthStore from '../store/useAuthStore'

/**
 * AuthModal - Raw, brutalist modal pop-up for login
 * Thick black borders on all inputs, hard shadows
 */
const AuthModal = ({ isOpen, onClose }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useAuthStore((state) => state.login)

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    await login(email, password)
    onClose()
    setEmail('')
    setPassword('')
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-sasta-white border-brutal-lg shadow-brutal-lg p-8 max-w-md w-full relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 border-brutal-sm bg-sasta-black text-sasta-white p-2 hover:bg-sasta-accent hover:text-sasta-black transition-colors"
        >
          <X size={20} />
        </button>

        <h2 className="text-3xl font-bold mb-6 font-zero">LOGIN</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-bold mb-2 font-zero">
              EMAIL
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border-brutal p-3 bg-sasta-white font-zero focus:outline-none focus:bg-sasta-accent/10"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-bold mb-2 font-zero">
              PASSWORD
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border-brutal p-3 bg-sasta-white font-zero focus:outline-none focus:bg-sasta-accent/10"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full border-brutal bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal hover:bg-sasta-accent hover:text-sasta-black transition-colors mt-6"
          >
            SUBMIT
          </button>
        </form>
      </div>
    </div>
  )
}

export default AuthModal
