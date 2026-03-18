import React from 'react'

const TOAST_STYLES = {
  error: 'bg-red-600 text-white',
  success: 'bg-sasta-accent text-sasta-black',
  info: 'bg-sasta-black text-sasta-white',
}

export default function ToastContainer({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`border-brutal-sm shadow-brutal flex items-start gap-3 p-3 pointer-events-auto animate-slide-in ${TOAST_STYLES[toast.type] || TOAST_STYLES.error}`}
          role="alert"
        >
          <span className="font-zero font-bold text-sm flex-1">{toast.message}</span>
          <button
            onClick={() => onDismiss(toast.id)}
            className="font-zero font-bold text-sm opacity-70 hover:opacity-100 shrink-0 ml-2"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
