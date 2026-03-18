import React from 'react'

const ProjectCard = ({ name, description, subdomain, accentColor = "#00ff00" }) => {
  const handleLaunch = () => {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      // If you're on a direct container port (e.g. :9000), route via Traefik on :80.
      // If you're already on Traefik (:80), keep it as a relative navigation.
      const port = window.location.port
      const isNonDefaultPort = port && port !== '80' && port !== '443'

      if (isNonDefaultPort) {
        window.location.assign(`${window.location.protocol}//${window.location.hostname}/${subdomain}/`)
      } else {
        // Use same-tab navigation so browser Back works locally (and avoid popup blockers).
        window.location.assign(`/${subdomain}/`)
      }
    } else {
      window.location.assign(`https://${subdomain}.sastaspace.com`)
    }
  }

  return (
    <div className="border-brutal bg-sasta-white shadow-brutal p-6 hover:shadow-brutal-lg transition-shadow">
      <h3 className="text-2xl font-bold mb-3 font-zero">{name}</h3>
      <p className="text-sm mb-6 font-zero text-sasta-black/80">{description}</p>
      <button
        onClick={handleLaunch}
        className="border-brutal bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors"
        style={{ borderColor: accentColor }}
      >
        LAUNCH →
      </button>
    </div>
  )
}

export default ProjectCard
