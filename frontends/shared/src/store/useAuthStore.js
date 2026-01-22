import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      
      login: async (email, password) => {
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
      name: 'sastaspace-auth',
      storage: createJSONStorage(() => localStorage),
    }
  )
)

export default useAuthStore
