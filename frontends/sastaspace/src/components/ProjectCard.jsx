import React from 'react'

const ProjectCard = ({ name, description, subdomain, accentColor = "#00ff00", tags = [] }) => {
  const handleLaunch = () => {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      const port = window.location.port
      const isNonDefaultPort = port && port !== '80' && port !== '443'

      if (isNonDefaultPort) {
        window.location.assign(`${window.location.protocol}//${window.location.hostname}/${subdomain}/`)
      } else {
        window.location.assign(`/${subdomain}/`)
      }
    } else {
      window.location.assign(`https://${subdomain}.sastaspace.com`)
    }
  }

  return (
    <div className="border-brutal bg-sasta-white shadow-brutal p-6 hover:shadow-brutal-lg transition-shadow flex flex-col">
      <h3 className="text-2xl font-bold mb-3 font-zero">{name}</h3>
      <p className="text-sm mb-4 font-zero text-sasta-black/80 flex-1">{description}</p>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {tags.map((tag) => (
            <span
              key={tag}
              className="text-xs font-zero font-bold border-brutal-sm px-2 py-1 bg-sasta-black text-sasta-white"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
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
