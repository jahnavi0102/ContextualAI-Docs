import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Shared/Navbar';
import MainContent from './components/MainContent';
import AuthPage from './AuthPage';
import './index.css';

// Helper to decode JWT token and get its payload
const decodeJwt = (token: string) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error("Error decoding JWT:", e);
    return null;
  }
};

function App() {

  const [currentPage, setCurrentPage] = useState<string>(
    localStorage.getItem('lastPage') || 'dashboard'
  );
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loadingAuth, setLoadingAuth] = useState<boolean>(true);

  useEffect(() => {
    localStorage.setItem('lastPage', currentPage);
  }, [currentPage]);

  // Function to refresh the access token
  const refreshAccessToken = useCallback(async (currentRefreshToken: string): Promise<string | null> => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/token/refresh/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: currentRefreshToken }),
      });

      if (!response.ok) {
        console.error("Failed to refresh token:", await response.json());
        throw new Error('Failed to refresh token');
      }

      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      setAuthToken(data.access);
      setRefreshToken(data.refresh);
      return data.access;
    } catch (error) {
      console.error("Error during token refresh:", error);
      handleLogout(); // Log out if refresh fails
      return null;
    }
  }, []);

  // Centralized fetch function with automatic token refresh
  const fetchWithAuth = useCallback(async (url: string, options?: RequestInit): Promise<Response> => {
    let currentAccessToken = authToken;
    let currentRefreshToken = refreshToken;

    if (currentAccessToken) {
      const decodedToken = decodeJwt(currentAccessToken);
      if (decodedToken && decodedToken.exp * 1000 < Date.now()) {
        console.log("Access token expired, attempting to refresh...");
        if (currentRefreshToken) {
          currentAccessToken = await refreshAccessToken(currentRefreshToken);
        } else {
          console.warn("No refresh token available, logging out.");
          handleLogout();
          throw new Error("Authentication required.");
        }
      }
    } else if (currentRefreshToken) {
      console.log("No access token, attempting to get new one with refresh token...");
      currentAccessToken = await refreshAccessToken(currentRefreshToken);
    } else {
      handleLogout();
      throw new Error("Authentication required.");
    }

    if (!currentAccessToken) {
      throw new Error("Authentication required.");
    }

    const headers = {
      ...options?.headers,
      'Authorization': `Bearer ${currentAccessToken}`,
    };

    return fetch(url, { ...options, headers });
  }, [authToken, refreshToken, refreshAccessToken]);

  // Check for existing tokens on component mount
  useEffect(() => {
    const storedAccessToken = localStorage.getItem('access_token');
    const storedRefreshToken = localStorage.getItem('refresh_token');

    if (storedAccessToken) {
      const decodedToken = decodeJwt(storedAccessToken);
      if (decodedToken && decodedToken.exp * 1000 > Date.now()) {
        setAuthToken(storedAccessToken);
        setRefreshToken(storedRefreshToken);
        setIsAuthenticated(true);
        setLoadingAuth(false);
      } else if (storedRefreshToken) {
        console.log("Access token expired on mount, attempting to refresh...");
        refreshAccessToken(storedRefreshToken).then(newAccessToken => {
          if (newAccessToken) {
            setIsAuthenticated(true);
          } else {
            setIsAuthenticated(false);
          }
          setLoadingAuth(false);
        });
      } else {
        setIsAuthenticated(false);
        setLoadingAuth(false);
      }
    } else if (storedRefreshToken) {
      console.log("No access token on mount, attempting to get new one with refresh token...");
      refreshAccessToken(storedRefreshToken).then(newAccessToken => {
        if (newAccessToken) {
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
        setLoadingAuth(false);
      });
    } else {
      setIsAuthenticated(false);
      setLoadingAuth(false);
    }
  }, [refreshAccessToken]);

  const handleLoginSuccess = (access: string, refresh: string) => {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    setAuthToken(access);
    setRefreshToken(refresh);
    setIsAuthenticated(true);
    setCurrentPage('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setAuthToken(null);
    setRefreshToken(null);
    setIsAuthenticated(false);
    setCurrentPage('dashboard');
  };

  if (loadingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white text-xl">
        Loading authentication...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Left Column: Navigation Panel */}
      <div className="w-64 flex-shrink-0 border-r border-gray-700 p-4">
        <Navbar 
          onPageChange={setCurrentPage} 
          currentPage={currentPage} 
          onLogout={handleLogout} 
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-8 overflow-y-auto">
        <MainContent 
          currentPage={currentPage} 
          fetchWithAuth={fetchWithAuth} 
          onLogout={handleLogout} 
        />
      </div>
    </div>
  );
}

export default App;
