import React from 'react';

interface SettingsProps {
  onLogout: () => void;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>; // Pass fetchWithAuth if settings needs API calls
}

const Settings: React.FC<SettingsProps> = ({ onLogout, fetchWithAuth }) => {
  return (
    <div className="h-full bg-gray-800 rounded-lg shadow-lg p-6 flex flex-col items-center justify-center">
      <h1 className="text-3xl font-bold text-white mb-8">Settings</h1>
      <p className="text-gray-300 text-lg mb-8 text-center">
        Manage your account preferences and security settings here.
      </p>

      {/* Logout Button */}
      <button
        onClick={onLogout}
        className="mt-4 w-full max-w-xs bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg transition duration-200 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
      >
        Logout
      </button>

      {/* Future settings options can go here */}
      <div className="mt-8 text-gray-400 text-sm">
        {/* Example: <p>Version: 1.0.0</p> */}
      </div>
    </div>
  );
};

export default Settings;
