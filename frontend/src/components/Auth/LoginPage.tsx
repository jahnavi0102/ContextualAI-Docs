import React, { useState } from 'react';

interface LoginPageProps {
  onLoginSuccess: (access: string, refresh: string) => void; // Updated prop to accept both tokens
  onSwitchToSignup: () => void;
}

function LoginPage({ onLoginSuccess, onSwitchToSignup }: LoginPageProps) {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/token/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      // Pass both access and refresh tokens to the parent's onLoginSuccess
      onLoginSuccess(data.access, data.refresh);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-md">
      <h2 className="text-3xl font-bold text-center text-white mb-6">Login</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="email">
            email
          </label>
          <input
            type="text"
            id="email"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-900 leading-tight focus:outline-none focus:shadow-outline bg-gray-700 border-gray-600 focus:ring-2 focus:ring-blue-500"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password">
            Password
          </label>
          <input
            type="password"
            id="password"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-900 leading-tight focus:outline-none focus:shadow-outline bg-gray-700 border-gray-600 focus:ring-2 focus:ring-blue-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <p className="text-red-500 text-sm italic">{error}</p>}
        <button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-200 ease-in-out disabled:opacity-50"
          disabled={loading}
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
      <p className="text-center text-gray-400 text-sm mt-4">
        Don't have an account?{' '}
        <button onClick={onSwitchToSignup} className="text-blue-400 hover:text-blue-300 font-bold focus:outline-none">
          Sign Up here
        </button>
      </p>
    </div>
  );
}

export default LoginPage;
