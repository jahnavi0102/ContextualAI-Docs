import React from 'react';
import { FaFileAlt, FaChartBar, FaUser, FaCog, FaComments } from 'react-icons/fa';

interface NavbarProps {
  onPageChange: (page: string) => void;
  currentPage: string;
  onLogout: () => void; // onLogout prop is still accepted and passed to the Logout button
}

const Navbar: React.FC<NavbarProps> = ({ onPageChange, currentPage, onLogout }: NavbarProps) => {
  const navItems = [
    { name: 'Documents', icon: FaFileAlt, page: 'documents' },
    { name: 'Dashboard', icon: FaChartBar, page: 'dashboard' },
    { name: 'Profile', icon: FaUser, page: 'profile' },
    { name: 'DocAI Chat', icon: FaComments, page: 'chat' },
    { name: 'Settings', icon: FaCog, page: 'settings' }, 
  ];

  return (
    <nav className="flex flex-col h-full">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-blue-400">RAG System</h1>
      </div>
      <ul className="space-y-2 flex-grow">
        {navItems.map((item) => (
          <li key={item.page}>
            <button
              onClick={() => onPageChange(item.page)}
              className={`w-full text-left py-2 px-4 rounded-lg transition duration-150 ease-in-out
                ${currentPage === item.page ? 'bg-blue-700 text-white' : 'hover:bg-gray-700 text-gray-300'}`}
            >
              <item.icon className="inline-block mr-2" />
              {item.name}
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-auto pt-4 border-t border-gray-700">
      </div>
    </nav>
  );
};

export default Navbar;
