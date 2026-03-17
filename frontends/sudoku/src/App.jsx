import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sudoku from './pages/Sudoku.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-header">
        <h1>SastaSpace Sudoku</h1>
        <span className="badge">GA Solver</span>
      </div>
      <Routes>
        <Route path="/" element={<Sudoku />} />
      </Routes>
    </BrowserRouter>
  );
}
