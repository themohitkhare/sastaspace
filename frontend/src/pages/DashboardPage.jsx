import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { portfolioAPI } from '../services/api';

const DashboardPage = () => {
  const [portfolio, setPortfolio] = useState(null);
  const [aiFeedback, setAiFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await portfolioAPI.getMyPortfolio();
        setPortfolio(response.data);
      } catch (error) {
        console.error('Error fetching portfolio:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolio();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
          
          {portfolio ? (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Your Portfolio</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name</label>
                  <p className="mt-1 text-sm text-gray-900">{portfolio.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Title</label>
                  <p className="mt-1 text-sm text-gray-900">{portfolio.title}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Bio</label>
                  <p className="mt-1 text-sm text-gray-900">{portfolio.bio}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Public URL</label>
                  <a 
                    href={`/p/${portfolio.slug}`} 
                    className="mt-1 text-sm text-blue-600 hover:text-blue-500"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View your portfolio
                  </a>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Welcome!</h2>
              <p className="text-gray-600 mb-4">
                You haven't created your portfolio yet. Start by uploading your resume and LinkedIn profile.
              </p>
              <a
                href="/onboarding"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Create Portfolio
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage; 