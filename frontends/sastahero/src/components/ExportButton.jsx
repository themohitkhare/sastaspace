import React, { useState } from 'react';
import { toPng } from 'html-to-image';

const ExportButton = ({ cardRef }) => {
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    if (!cardRef?.current) return;
    setExporting(true);
    try {
      const dataUrl = await toPng(cardRef.current, { cacheBust: true });
      const link = document.createElement('a');
      link.download = 'hero-card.png';
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Export failed', err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={exporting}
      className="border-brutal bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal hover:bg-sasta-accent hover:text-sasta-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full"
    >
      {exporting ? 'EXPORTING...' : 'EXPORT AS PNG →'}
    </button>
  );
};

export default ExportButton;
