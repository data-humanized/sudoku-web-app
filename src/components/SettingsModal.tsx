import React, { useState, useRef } from 'react';
import { X, Download, Upload, Trash2, Check } from 'lucide-react';
import { UserSettings } from '../logic/sudokuLogic';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: UserSettings;
  onUpdateSettings: (newSettings: UserSettings) => void;
  onExportData: () => void;
  onImportData: (fileContent: string) => void;
  onResetProgress: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  onExportData,
  onImportData,
  onResetProgress,
}) => {
  const [showConfirmReset, setShowConfirmReset] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const toggle = (key: keyof UserSettings) => {
    onUpdateSettings({
      ...settings,
      [key]: !settings[key],
    });
  };

  const setSize = (size: 'small' | 'medium' | 'large') => {
    onUpdateSettings({
      ...settings,
      numberSize: size,
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const content = ev.target?.result as string;
        onImportData(content);
        setImportStatus('Backup loaded successfully');
        setTimeout(() => setImportStatus(null), 3000);
      } catch (err) {
        setImportStatus('Failed to import backup');
        setTimeout(() => setImportStatus(null), 3000);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 p-4 select-none"
      style={{ borderRadius: '0px' }}
    >
      <div
        className="w-full max-w-lg bg-white border border-slate-300 shadow-2xl flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200"
        style={{ borderRadius: '0px' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-200">
          <h3 className="text-lg font-bold text-slate-900">Settings</h3>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Settings Body */}
        <div className="p-5 overflow-y-auto space-y-6 text-sm">
          {/* Number & Note Size */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Number & Note Size
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['small', 'medium', 'large'] as const).map(sz => (
                <button
                  key={sz}
                  onClick={() => setSize(sz)}
                  className={`py-2 text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer border ${
                    settings.numberSize === sz
                      ? 'bg-blue-600 text-white border-blue-600 font-bold'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                  style={{ borderRadius: '0px' }}
                >
                  {sz}
                </button>
              ))}
            </div>
          </div>

          {/* Gameplay Toggles */}
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Gameplay Options
            </label>
            <div className="space-y-2 border border-slate-200 divide-y divide-slate-100 bg-white">
              {/* Show Timer */}
              <div className="flex items-center justify-between p-3">
                <div>
                  <div className="font-semibold text-slate-800">Show Timer</div>
                  <div className="text-xs text-slate-400">Display elapsed time in stats row</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.showTimer}
                  onChange={() => toggle('showTimer')}
                  className="w-4 h-4 text-blue-600 accent-blue-600 cursor-pointer"
                />
              </div>

              {/* Highlight Same Numbers */}
              <div className="flex items-center justify-between p-3">
                <div>
                  <div className="font-semibold text-slate-800">Highlight Same Numbers</div>
                  <div className="text-xs text-slate-400">Highlight all matching digits and notes on board</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.highlightSameNumbers}
                  onChange={() => toggle('highlightSameNumbers')}
                  className="w-4 h-4 text-blue-600 accent-blue-600 cursor-pointer"
                />
              </div>

              {/* Color Feedback (Default ON) */}
              <div className="flex items-center justify-between p-3">
                <div>
                  <div className="font-semibold text-slate-800">Color Feedback</div>
                  <div className="text-xs text-slate-400">Green for correct entries, red for mistakes</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.colorFeedback}
                  onChange={() => toggle('colorFeedback')}
                  className="w-4 h-4 text-blue-600 accent-blue-600 cursor-pointer"
                />
              </div>

              {/* Auto-Remove Notes */}
              <div className="flex items-center justify-between p-3">
                <div>
                  <div className="font-semibold text-slate-800">Auto-Remove Notes</div>
                  <div className="text-xs text-slate-400">Clear peer candidates when placing correct digit</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.autoRemoveNotes}
                  onChange={() => toggle('autoRemoveNotes')}
                  className="w-4 h-4 text-blue-600 accent-blue-600 cursor-pointer"
                />
              </div>

              {/* Sound Effects */}
              <div className="flex items-center justify-between p-3">
                <div>
                  <div className="font-semibold text-slate-800">Sound Effects</div>
                  <div className="text-xs text-slate-400">Minimal procedural clicks and tones</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.soundEffects}
                  onChange={() => toggle('soundEffects')}
                  className="w-4 h-4 text-blue-600 accent-blue-600 cursor-pointer"
                />
              </div>

              {/* Haptic Feedback */}
              <div className="flex items-center justify-between p-3">
                <div>
                  <div className="font-semibold text-slate-800">Haptic Feedback</div>
                  <div className="text-xs text-slate-400">Device vibration on mistake (supported devices)</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.hapticFeedback}
                  onChange={() => toggle('hapticFeedback')}
                  className="w-4 h-4 text-blue-600 accent-blue-600 cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Data Management */}
          <div className="space-y-3 pt-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Data Management (zensudoku_data.json)
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={onExportData}
                className="py-2.5 px-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-center gap-2 cursor-pointer transition-colors"
                style={{ borderRadius: '0px' }}
              >
                <Download className="w-4 h-4 text-slate-500" />
                <span>Export JSON</span>
              </button>

              <button
                onClick={() => fileInputRef.current?.click()}
                className="py-2.5 px-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-center gap-2 cursor-pointer transition-colors"
                style={{ borderRadius: '0px' }}
              >
                <Upload className="w-4 h-4 text-slate-500" />
                <span>Import JSON</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={handleFileUpload}
              />
            </div>

            {importStatus && (
              <div className="p-2 bg-slate-100 text-slate-700 text-xs text-center font-medium">
                {importStatus}
              </div>
            )}

            {/* Reset Progress Section */}
            <div className="pt-2">
              {!showConfirmReset ? (
                <button
                  onClick={() => setShowConfirmReset(true)}
                  className="w-full py-2.5 text-xs text-red-600 hover:bg-red-50 border border-red-200 font-semibold transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  style={{ borderRadius: '0px' }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Reset All Progress & Streaks</span>
                </button>
              ) : (
                <div className="p-3 bg-red-50 border border-red-200 space-y-2 text-center">
                  <p className="text-xs text-red-700 font-medium">
                    Are you sure? This will permanently delete all completed game history and streaks.
                  </p>
                  <div className="flex gap-2 justify-center">
                    <button
                      onClick={() => setShowConfirmReset(false)}
                      className="px-3 py-1.5 bg-white border border-slate-300 text-slate-700 text-xs font-semibold cursor-pointer"
                      style={{ borderRadius: '0px' }}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        onResetProgress();
                        setShowConfirmReset(false);
                      }}
                      className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold cursor-pointer"
                      style={{ borderRadius: '0px' }}
                    >
                      Confirm Reset
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
