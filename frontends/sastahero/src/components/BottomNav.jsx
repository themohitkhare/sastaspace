import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const TABS = [
  { path: '/', label: 'Play', icon: '▶' },
  { path: '/collection', label: 'Cards', icon: '◇' },
  { path: '/story', label: 'Story', icon: '📖' },
  { path: '/knowledge', label: 'Learn', icon: '💡' },
  { path: '/profile', label: 'Me', icon: '●' },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav data-testid="bottom-nav" className="flex justify-around items-center bg-black text-white border-t-2 border-white py-2">
      {TABS.map(({ path, label, icon }) => {
        const active = location.pathname === path;
        return (
          <button
            key={path}
            data-testid={`nav-${label.toLowerCase()}`}
            className={`flex flex-col items-center text-xs font-bold ${active ? 'text-white' : 'text-gray-500'}`}
            onClick={() => navigate(path)}
          >
            <span className="text-lg">{icon}</span>
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
