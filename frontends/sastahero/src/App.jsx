import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import GameFeed from './pages/GameFeed.jsx';
import CollectionBook from './pages/CollectionBook.jsx';
import StoryThread from './pages/StoryThread.jsx';
import KnowledgeBank from './pages/KnowledgeBank.jsx';
import ProfilePage from './pages/ProfilePage.jsx';
import BottomNav from './components/BottomNav.jsx';

function App() {
  return (
    <BrowserRouter basename="/sastahero">
      <div className="flex flex-col h-screen bg-black">
        <Routes>
          <Route path="/" element={<GameFeed />} />
          <Route path="/collection" element={<CollectionBook />} />
          <Route path="/story" element={<StoryThread />} />
          <Route path="/knowledge" element={<KnowledgeBank />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
        <BottomNav />
      </div>
    </BrowserRouter>
  );
}

export default App;
