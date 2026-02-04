const STORAGE_KEY = 'sastadice_seen_triggers'

export function useSeenTriggers() {
  const getSeen = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? new Set(JSON.parse(raw)) : new Set()
    } catch {
      return new Set()
    }
  }

  const markSeen = (trigger) => {
    try {
      const seen = getSeen()
      seen.add(trigger)
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...seen]))
      return true
    } catch {
      return false
    }
  }

  const isSeen = (trigger) => getSeen().has(trigger)

  const shouldShowTooltip = (trigger) => !isSeen(trigger)

  return { getSeen, markSeen, isSeen, shouldShowTooltip }
}
