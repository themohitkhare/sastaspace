import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HeroBuilder from './pages/HeroBuilder.jsx';

function App() {
  return (
    <BrowserRouter basename="/sastahero">
      <Routes>
        <Route path="/" element={<HeroBuilder />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
