import React from 'react';
import Dashboard from './Dashboard';
import DocumentLibrary from './Documents/DocumentLibrary';
import Profile from './Profile';
import ChatInterface from '../components/Chat/ChatInterface';
import Settings from './Settings'; // Import the Settings component

interface MainContentProps {
  currentPage: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  onLogout: () => void; // MainContent now needs to pass onLogout to Settings
}

const MainContent: React.FC<MainContentProps> = ({ currentPage, fetchWithAuth, onLogout }) => {
  switch (currentPage) {
    case 'documents':
      return <DocumentLibrary fetchWithAuth={fetchWithAuth} />;
    case 'dashboard':
      return <Dashboard fetchWithAuth={fetchWithAuth} />;
    case 'profile':
      return <Profile fetchWithAuth={fetchWithAuth} />;
    case 'chat':
      return <ChatInterface fetchWithAuth={fetchWithAuth} onClose={() => {}} />;
    case 'settings': // Case for the settings page
      return <Settings onLogout={onLogout} fetchWithAuth={fetchWithAuth} />; // Pass onLogout and fetchWithAuth to Settings
    default:
      return <Dashboard fetchWithAuth={fetchWithAuth} />;
  }
};

export default MainContent;
