import React, { useRef, useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const TABS = [
  { path: '/', label: 'PLAY', icon: '\u25B6' },
  { path: '/collection', label: 'CARDS', icon: '\u25C7' },
  { path: '/story', label: 'STORY', icon: '\u2261' },
  { path: '/knowledge', label: 'LEARN', icon: '\u2736' },
  { path: '/profile', label: 'ME', icon: '\u25CF' },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const tabRefs = useRef([]);
  const [indicatorStyle, setIndicatorStyle] = useState({});

  const activeIndex = TABS.findIndex(t => t.path === location.pathname);

  useEffect(() => {
    const el = tabRefs.current[activeIndex];
    if (el) {
      setIndicatorStyle({
        left: el.offsetLeft,
        width: el.offsetWidth,
      });
    }
  }, [activeIndex]);

  return (
    <nav
      data-testid="bottom-nav"
      role="tablist"
      aria-label="Main navigation"
      className="relative flex justify-around items-center bg-black text-white border-t-4 border-sasta-accent py-2 z-50"
    >
      <div
        className="absolute bottom-0 h-1 bg-sasta-accent transition-all duration-200 ease-out"
        style={indicatorStyle}
        aria-hidden="true"
      />
      {TABS.map(({ path, label, icon }, i) => {
        const active = location.pathname === path;
        return (
          <button
            key={path}
            ref={el => tabRefs.current[i] = el}
            role="tab"
            aria-selected={active}
            aria-label={label}
            data-testid={`nav-${label.toLowerCase()}`}
            className={`flex flex-col items-center text-xs font-bold font-zero uppercase tracking-wider ${
              active ? 'text-sasta-accent' : 'text-gray-500 hover:text-white'
            } transition-colors`}
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
