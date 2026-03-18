import React from 'react'
import Navbar from './components/Navbar'
import ProjectCard from './components/ProjectCard'

function App() {
  const projects = [
    {
      name: 'SastaDice',
      description: 'Multiplayer board game with auctions, trading, and dynamic economy. Built with React, FastAPI, and MongoDB.',
      subdomain: 'sastadice',
      accentColor: '#00ff00',
      tags: ['React', 'FastAPI', 'MongoDB', 'Zustand'],
    },
    {
      name: 'SastaHero',
      description: 'Interactive RPG character builder. Pick a class, allocate stats, export your hero card as PNG.',
      subdomain: 'sastahero',
      accentColor: '#ff6600',
      tags: ['React', 'FastAPI', 'Canvas Export', 'Zustand'],
    },
    {
      name: 'Sudoku',
      description: 'Player vs Genetic Algorithm. Upload puzzles via OCR or play manually against an evolving AI solver.',
      subdomain: 'sudoku',
      accentColor: '#6366f1',
      tags: ['React', 'FastAPI', 'Genetic Algorithm', 'OCR'],
    },
  ]

  return (
    <div className="min-h-screen bg-sasta-white">
      <Navbar />

      <section className="max-w-7xl mx-auto px-6 py-20 text-center">
        <h1 className="text-7xl md:text-9xl font-bold font-zero mb-6 tracking-tight">
          SASTASPACE
        </h1>
        <p className="text-2xl md:text-3xl font-zero font-bold text-sasta-black/80 mb-4">
          High Performance. Low Budget. Pure Chaos.
        </p>
        <div className="mt-12 border-brutal-lg bg-sasta-black text-sasta-white p-8 shadow-brutal-lg inline-block">
          <p className="text-lg font-zero">
            &gt; Building tools that don&apos;t break the bank
          </p>
          <p className="text-lg font-zero mt-2">
            &gt; Shipping fast, shipping raw
          </p>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-4xl font-bold font-zero mb-12 text-center">PROJECTS</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {projects.map((project) => (
            <ProjectCard
              key={project.subdomain}
              name={project.name}
              description={project.description}
              subdomain={project.subdomain}
              accentColor={project.accentColor}
              tags={project.tags}
            />
          ))}
        </div>
      </section>

      <footer className="border-t-4 border-sasta-black bg-sasta-white py-8 mt-20">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-sm font-zero text-sasta-black/60 mb-3">
            &copy; 2026 SASTASPACE. ALL RIGHTS RESERVED. MAYBE.
          </p>
          <a
            href="https://github.com/mkhare/sastaspace"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-zero font-bold border-brutal-sm bg-sasta-black text-sasta-white px-4 py-2 shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors inline-block"
          >
            VIEW SOURCE →
          </a>
        </div>
      </footer>
    </div>
  )
}

export default App
