import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { portfolioAPI } from '../services/api';

const PublicPortfolioPage = () => {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { slug } = useParams();

  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await portfolioAPI.getPublicPortfolio(slug);
        setPortfolio(response.data);
      } catch (error) {
        setError('Portfolio not found');
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolio();
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Portfolio Not Found</h1>
          <p className="text-gray-600">The portfolio you're looking for doesn't exist or has been removed.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {portfolio.slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </h1>
            <p className="text-lg text-gray-600">Professional Portfolio</p>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Professional Summary */}
        {portfolio.professional_summary && (
          <section className="bg-white shadow rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Professional Summary</h2>
            <p className="text-gray-700 leading-relaxed">{portfolio.professional_summary}</p>
          </section>
        )}

        {/* Skills */}
        {portfolio.skills && portfolio.skills.length > 0 && (
          <section className="bg-white shadow rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Skills</h2>
            <div className="flex flex-wrap gap-2">
              {portfolio.skills.map((skill, index) => (
                <span
                  key={index}
                  className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium"
                >
                  {skill}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Work Experience */}
        {portfolio.work_experience && portfolio.work_experience.length > 0 && (
          <section className="bg-white shadow rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Work Experience</h2>
            <div className="space-y-6">
              {portfolio.work_experience.map((job, index) => (
                <div key={index} className="border-l-4 border-blue-500 pl-6">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start mb-2">
                    <h3 className="text-lg font-medium text-gray-900">{job.title}</h3>
                    <span className="text-sm text-gray-500 mt-1 sm:mt-0">{job.dates}</span>
                  </div>
                  <p className="text-blue-600 font-medium mb-2">{job.company}</p>
                  <p className="text-gray-700 leading-relaxed">{job.description}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Education */}
        {portfolio.education && portfolio.education.length > 0 && (
          <section className="bg-white shadow rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Education</h2>
            <div className="space-y-6">
              {portfolio.education.map((edu, index) => (
                <div key={index} className="border-l-4 border-green-500 pl-6">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start mb-2">
                    <h3 className="text-lg font-medium text-gray-900">{edu.degree}</h3>
                    <span className="text-sm text-gray-500 mt-1 sm:mt-0">{edu.dates}</span>
                  </div>
                  <p className="text-green-600 font-medium">{edu.institution}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Footer */}
        <footer className="text-center py-8">
          <p className="text-gray-500 text-sm">
            Powered by{' '}
            <a href="/" className="text-blue-600 hover:text-blue-700 font-medium">
              SastaSpace
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
};

export default PublicPortfolioPage; 