import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      
      login: async (email, password) => {
        // Mock login - just console log for now
        console.log('Login attempt:', { email, password })
        
        // Simulate async login
        // In real implementation, this would call the API
        const mockUser = {
          id: 1,
          email: email,
          name: 'Sasta User',
        }
        
        set({
          user: mockUser,
          isAuthenticated: true,
        })
        
        return { success: true, user: mockUser }
      },
      
      logout: () => {
        set({
          user: null,
          isAuthenticated: false,
        })
      },
    }),
    {
      name: 'sastaspace-auth', // localStorage key
      storage: createJSONStorage(() => localStorage),
    }
  )
)

export default useAuthStore
