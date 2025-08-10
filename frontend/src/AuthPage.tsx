import React, { useState } from 'react'
import LoginPage from './components/Auth/LoginPage'
import SignupForm from './components/Auth/SignupForm'
interface AuthPageProps {
  onLoginSuccess: (access: string, refresh: string) => void
}

function AuthPage({ onLoginSuccess }: AuthPageProps) {
  const [currentForm, setCurrentForm] = useState<'login' | 'signup'>('login');


  const handleSignupSuccess = (access: string, refresh: string) => {
    onLoginSuccess(access, refresh);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      {currentForm === 'login' ? (
        <LoginPage 
          onLoginSuccess={onLoginSuccess}
          onSwitchToSignup={() => setCurrentForm('signup')} 
        />
      ) : (
        <SignupForm 
          onSignupSuccess={handleSignupSuccess}
          onSwitchToLogin={() => setCurrentForm('login')} 
        />
      )}
    </div>
  );
}

export default AuthPage;
