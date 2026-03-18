import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sudoku from './pages/Sudoku.jsx';

export default function App() {
  return (
    <BrowserRouter basename="/sudoku">
      <div className="app-header">
        <a className="app-header__home" href="/">
          ← BACK
        </a>
        <div className="app-header__right">
          <h1>SUDOKU</h1>
          <span className="badge">GA SOLVER</span>
        </div>
      </div>
      <Routes>
        <Route path="/" element={<Sudoku />} />
        <Route path="/:matchId" element={<Sudoku />} />
      </Routes>
    </BrowserRouter>
  );
}
