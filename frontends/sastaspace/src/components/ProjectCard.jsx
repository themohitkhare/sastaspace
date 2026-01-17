import React from 'react'

const ProjectCard = ({ name, description, subdomain, accentColor = "#00ff00" }) => {
  const handleLaunch = () => {
    window.open(`https://${subdomain}.sastaspace.com`, '_blank')
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
