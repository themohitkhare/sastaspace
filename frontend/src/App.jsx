import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { authAPI } from './services/api';
import ErrorBoundary from './components/ErrorBoundary';
import { AuthContext } from './context/AuthContext';

// Pages
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import PublicPortfolioPage from './pages/PublicPortfolioPage';

// Main App component
function App() {
  // Hooks must be called at the top level of the component
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Effect hook for authentication check
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await authAPI.getCurrentUser();
        setUser(response.data);
      } catch (error) {
        console.log('Auth check failed:', error.message);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Event handlers - these are not hooks, just regular functions
  const login = async (email, password) => {
    try {
      await authAPI.login(email, password);
      const response = await authAPI.getCurrentUser();
      setUser(response.data);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data || 'Login failed' };
    }
  };

  const register = async (email, password1, password2) => {
    try {
      await authAPI.register(email, password1, password2);
      const response = await authAPI.getCurrentUser();
      setUser(response.data);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data || 'Registration failed' };
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  // Early return for loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Main render - all hooks must be called before this point
  return (
    <ErrorBoundary>
      <AuthContext.Provider value={{ user, login, register, logout }}>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route 
                path="/onboarding" 
                element={user ? <OnboardingPage /> : <Navigate to="/login" />} 
              />
              <Route 
                path="/dashboard" 
                element={user ? <DashboardPage /> : <Navigate to="/login" />} 
              />
              <Route path="/p/:slug" element={<PublicPortfolioPage />} />
            </Routes>
          </div>
        </Router>
      </AuthContext.Provider>
    </ErrorBoundary>
  );
}

export default App;
