import { useState, useCallback, useRef } from 'react'

let toastIdCounter = 0

export function useToast() {
  const [toasts, setToasts] = useState([])
  const timersRef = useRef({})

  const showToast = useCallback((message, type = 'error') => {
    const id = ++toastIdCounter
    setToasts((prev) => [...prev, { id, message, type }])

    timersRef.current[id] = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
      delete timersRef.current[id]
    }, 4000)
  }, [])

  const dismissToast = useCallback((id) => {
    clearTimeout(timersRef.current[id])
    delete timersRef.current[id]
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return { toasts, showToast, dismissToast }
}
