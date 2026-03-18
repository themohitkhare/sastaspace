import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const TABS = [
  { path: '/', label: 'Play', icon: '\u25B6' },
  { path: '/collection', label: 'Cards', icon: '\u25C7' },
  { path: '/story', label: 'Story', icon: '\u2261' },
  { path: '/knowledge', label: 'Learn', icon: '\u2736' },
  { path: '/profile', label: 'Me', icon: '\u25CF' },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav
      data-testid="bottom-nav"
      role="tablist"
      aria-label="Main navigation"
      className="flex justify-around items-center bg-black text-white border-t-2 border-white py-2"
    >
      {TABS.map(({ path, label, icon }) => {
        const active = location.pathname === path;
        return (
          <button
            key={path}
            role="tab"
            aria-selected={active}
            aria-label={label}
            data-testid={`nav-${label.toLowerCase()}`}
            className={`flex flex-col items-center text-xs font-bold ${active ? 'text-white' : 'text-gray-500'}`}
            onClick={() => navigate(path)}
          >
            <span className="text-lg" aria-hidden="true">{icon}</span>
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
