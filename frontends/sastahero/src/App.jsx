import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import GameFeed from './pages/GameFeed.jsx';
import CollectionBook from './pages/CollectionBook.jsx';
import StoryThread from './pages/StoryThread.jsx';
import KnowledgeBank from './pages/KnowledgeBank.jsx';
import ProfilePage from './pages/ProfilePage.jsx';
import BottomNav from './components/BottomNav.jsx';

const TAB_ORDER = ['/', '/collection', '/story', '/knowledge', '/profile'];

function AnimatedRoutes() {
  const location = useLocation();
  const prevIndex = useRef(0);
  const [slideClass, setSlideClass] = useState('');

  useEffect(() => {
    const currentIdx = TAB_ORDER.indexOf(location.pathname);
    if (currentIdx === -1) return;
    if (currentIdx > prevIndex.current) setSlideClass('page-slide-left-enter');
    else if (currentIdx < prevIndex.current) setSlideClass('page-slide-right-enter');
    prevIndex.current = currentIdx;
    const timer = setTimeout(() => setSlideClass(''), 300);
    return () => clearTimeout(timer);
  }, [location.pathname]);

  return (
    <div className={`flex-1 flex flex-col overflow-hidden ${slideClass}`} key={location.pathname}>
      <Routes location={location}>
        <Route path="/" element={<GameFeed />} />
        <Route path="/collection" element={<CollectionBook />} />
        <Route path="/story" element={<StoryThread />} />
        <Route path="/knowledge" element={<KnowledgeBank />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter basename="/sastahero">
      <div className="flex flex-col h-screen bg-black">
        <AnimatedRoutes />
        <BottomNav />
      </div>
    </BrowserRouter>
  );
}

export default App;
