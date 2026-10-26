import React, { useState, useEffect } from 'react';
import { HeartCrack, HeartHandshake } from 'lucide-react';

interface LivesModalProps {
  isOpen: boolean;
  onGetLife: () => void;
}

export const LivesModal: React.FC<LivesModalProps> = ({ isOpen, onGetLife }) => {
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    if (!isOpen) {
      setCountdown(5);
      return;
    }

    // Reset countdown initially
    setCountdown(5);

    // If window is unfocused or tab hidden, reset back to 5s
    const handleUnfocus = () => {
      setCountdown(5);
    };

    window.addEventListener('blur', handleUnfocus);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        handleUnfocus();
      }
    });

    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      clearInterval(interval);
      window.removeEventListener('blur', handleUnfocus);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const isReady = countdown === 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 p-4"
      style={{ borderRadius: '0px' }}
    >
      <div
        className="w-full max-w-md bg-white border border-slate-300 shadow-2xl p-6 text-center space-y-5 animate-in fade-in zoom-in-95 duration-200"
        style={{ borderRadius: '0px' }}
      >
        <div className="mx-auto w-14 h-14 bg-red-50 flex items-center justify-center text-red-600">
          <HeartCrack className="w-8 h-8" />
        </div>

        <div className="space-y-1.5">
          <h3 className="text-xl font-bold text-slate-900">
            Out of lives. Get a life to continue.
          </h3>
          <p className="text-sm text-slate-500">
            You made 3 mistakes in this puzzle. Pause for a moment to refocus.
          </p>
        </div>

        <div className="py-2">
          {!isReady ? (
            <div className="text-sm font-semibold text-slate-400 font-mono-numbers">
              Available in <span className="text-lg text-slate-800 font-bold">{countdown}</span> seconds
            </div>
          ) : (
            <div className="text-sm font-semibold text-green-600">
              Ready to resume!
            </div>
          )}
        </div>

        <button
          disabled={!isReady}
          onClick={onGetLife}
          className={`
            w-full py-3 px-4 font-bold text-sm tracking-wide transition-all uppercase flex items-center justify-center gap-2
            ${isReady
              ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer shadow-sm active:translate-y-0.5'
              : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
            }
          `}
          style={{ borderRadius: '0px' }}
        >
          <HeartHandshake className="w-4 h-4" />
          <span>Get a life {countdown > 0 && `(${countdown})`}</span>
        </button>
      </div>
    </div>
  );
};
