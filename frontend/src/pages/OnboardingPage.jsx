import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { profileAPI } from '../services/api';

const OnboardingPage = () => {
  const [step, setStep] = useState(1);
  const [resumeFile, setResumeFile] = useState(null);
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const navigate = useNavigate();

  const handleResumeUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!allowedTypes.includes(file.type)) {
        setError('Please upload a PDF or DOCX file');
        return;
      }
      setResumeFile(file);
      setError('');
    }
  };

  const handleNext = () => {
    if (!resumeFile) {
      setError('Please upload your resume');
      return;
    }
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!linkedinUrl) {
      setError('Please enter your LinkedIn URL');
      return;
    }

    setProcessing(true);
    setError('');

    try {
      const response = await profileAPI.onboard(resumeFile, linkedinUrl);
      setProcessing(false);
      navigate('/dashboard', { state: { portfolio: response.data.portfolio, aiFeedback: response.data.ai_feedback } });
    } catch (error) {
      setProcessing(false);
      setError(error.response?.data?.error || 'An error occurred. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md mx-auto">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-600'}`}>
              1
            </div>
            <div className={`flex-1 h-1 mx-4 ${step >= 2 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-600'}`}>
              2
            </div>
          </div>
          <div className="flex justify-between mt-2 text-sm text-gray-600">
            <span>Upload Resume</span>
            <span>LinkedIn URL</span>
          </div>
        </div>

        {processing ? (
          <div className="text-center">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
            <h2 className="mt-4 text-xl font-semibold text-gray-900">Creating your portfolio...</h2>
            <p className="mt-2 text-gray-600">This may take a few moments while we analyze your data.</p>
          </div>
        ) : (
          <>
            {step === 1 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Upload your resume</h2>
                <p className="text-gray-600 mb-6">
                  Upload your resume in PDF or DOCX format. We'll extract the text and analyze your experience.
                </p>
                
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    onChange={handleResumeUpload}
                    className="hidden"
                    id="resume-upload"
                  />
                  <label htmlFor="resume-upload" className="cursor-pointer">
                    <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                      <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <p className="mt-2 text-sm text-gray-600">
                      {resumeFile ? resumeFile.name : 'Click to upload resume (PDF or DOCX)'}
                    </p>
                  </label>
                </div>

                {error && (
                  <div className="mt-4 rounded-md bg-red-50 p-4">
                    <div className="text-sm text-red-700">{error}</div>
                  </div>
                )}

                <button
                  onClick={handleNext}
                  disabled={!resumeFile}
                  className="mt-6 w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2 px-4 rounded-md"
                >
                  Next
                </button>
              </div>
            )}

            {step === 2 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Add your LinkedIn profile</h2>
                <p className="text-gray-600 mb-6">
                  Provide your public LinkedIn profile URL. We'll extract your professional information.
                </p>
                
                <form onSubmit={handleSubmit}>
                  <div>
                    <label htmlFor="linkedin-url" className="block text-sm font-medium text-gray-700 mb-2">
                      LinkedIn Profile URL
                    </label>
                    <input
                      type="url"
                      id="linkedin-url"
                      value={linkedinUrl}
                      onChange={(e) => setLinkedinUrl(e.target.value)}
                      placeholder="https://www.linkedin.com/in/your-profile"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      required
                    />
                  </div>

                  {error && (
                    <div className="mt-4 rounded-md bg-red-50 p-4">
                      <div className="text-sm text-red-700">{error}</div>
                    </div>
                  )}

                  <div className="mt-6 flex space-x-3">
                    <button
                      type="button"
                      onClick={() => setStep(1)}
                      className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 font-medium py-2 px-4 rounded-md"
                    >
                      Back
                    </button>
                    <button
                      type="submit"
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md"
                    >
                      Create Portfolio
                    </button>
                  </div>
                </form>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default OnboardingPage; 