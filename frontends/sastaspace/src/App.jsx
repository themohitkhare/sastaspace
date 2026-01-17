import React from 'react'
import Navbar from './components/Navbar'
import ProjectCard from './components/ProjectCard'

/**
 * App - Main landing page with Hero section and Projects grid
 * Neo-Brutalist design with monospace typography and hard shadows
 */
function App() {
  const projects = [
    {
      name: 'SastaDice',
      description: 'Roll the dice, embrace the chaos. Random number generation with style.',
      subdomain: 'sastadice',
      accentColor: '#00ff00',
    },
    {
      name: 'SastaHero',
      description: 'Your hero journey starts here. Build, deploy, conquer.',
      subdomain: 'sastahero',
      accentColor: '#00ff00',
    },
  ]

  return (
    <div className="min-h-screen bg-sasta-white">
      <Navbar />

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 py-20 text-center">
        <h1 className="text-7xl md:text-9xl font-bold font-zero mb-6 tracking-tight">
          SASTASPACE
        </h1>
        <p className="text-2xl md:text-3xl font-zero font-bold text-sasta-black/80 mb-4">
          High Performance. Low Budget. Pure Chaos.
        </p>
        <div className="mt-12 border-brutal-lg bg-sasta-black text-sasta-white p-8 shadow-brutal-lg inline-block">
          <p className="text-lg font-zero">
            &gt; Building tools that don't break the bank
          </p>
          <p className="text-lg font-zero mt-2">
            &gt; Shipping fast, shipping raw
          </p>
        </div>
      </section>

      {/* Projects Grid */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-4xl font-bold font-zero mb-12 text-center">PROJECTS</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {projects.map((project) => (
            <ProjectCard
              key={project.name}
              name={project.name}
              description={project.description}
              subdomain={project.subdomain}
              accentColor={project.accentColor}
            />
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t-4 border-sasta-black bg-sasta-white py-8 mt-20">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-sm font-zero text-sasta-black/60">
            &copy; 2024 SASTASPACE. ALL RIGHTS RESERVED. MAYBE.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
