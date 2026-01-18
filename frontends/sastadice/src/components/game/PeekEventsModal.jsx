export default function PeekEventsModal({ events, onClose }) {
  if (!events || events.length === 0) return null

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-sasta-white border-brutal-lg p-6 max-w-md w-full mx-4 shadow-brutal-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-zero font-bold text-xl text-sasta-black">
            🔎 INSIDER INFO
          </h2>
          <button
            onClick={onClose}
            className="font-zero font-bold text-2xl text-sasta-black hover:text-red-600 transition-colors"
          >
            ×
          </button>
        </div>

        <div className="mb-4">
          <p className="font-data text-sm text-sasta-black/70 mb-3">
            Next 3 Events:
          </p>
          <div className="space-y-2">
            {events.map((eventName, index) => (
              <div
                key={index}
                className="bg-sasta-accent border-brutal-sm p-3 font-zero font-bold text-sasta-black"
              >
                {index + 1}. {eventName}
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full py-3 px-4 bg-sasta-black text-sasta-accent font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
        >
          CLOSE
        </button>
      </div>
    </div>
  )
}
