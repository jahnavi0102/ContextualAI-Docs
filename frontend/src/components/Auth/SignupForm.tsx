import React, { useState } from 'react';

interface SignupFormProps {
  onSignupSuccess: (access: string, refresh: string) => void; // Updated prop to accept both tokens
  onSwitchToLogin: () => void;
}

function SignupForm({ onSignupSuccess, onSwitchToLogin }: SignupFormProps) {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [password2, setPassword2] = useState<string>(''); // For password confirmation
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (password !== password2) {
      setError('Passwords do not match.');
      setLoading(false);
      return;
    }

    try {
      // API for signup
      const registerResponse = await fetch('http://127.0.0.1:8000/api/users/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, password2 }),
      });

      if (!registerResponse.ok) {
        const errorData = await registerResponse.json();
        if (errorData.email) setError(`email: ${errorData.email[0]}`);
        else if (errorData.password) setError(`Password: ${errorData.password[0]}`);
        else if (errorData.password2) setError(`Password confirmation: ${errorData.password2[0]}`);
        else throw new Error(errorData.detail || 'Registration failed.');
        return;
      }

      // If registration is successful, automatically log in the user
      const loginResponse = await fetch('http://127.0.0.1:8000/api/token/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!loginResponse.ok) {
        throw new Error('Signed up but failed to auto-login. Please try logging in manually.');
      }

      const data = await loginResponse.json();
      // Pass both access and refresh tokens to the parent's onSignupSuccess
      onSignupSuccess(data.access, data.refresh);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-md">
      <h2 className="text-3xl font-bold text-center text-white mb-6">Sign Up</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="signup-email">
            email
          </label>
          <input
            type="text"
            id="signup-email"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-900 leading-tight focus:outline-none focus:shadow-outline bg-gray-700 border-gray-600 focus:ring-2 focus:ring-blue-500"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="signup-password">
            Password
          </label>
          <input
            type="password"
            id="signup-password"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-900 leading-tight focus:outline-none focus:shadow-outline bg-gray-700 border-gray-600 focus:ring-2 focus:ring-blue-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="signup-password2">
            Confirm Password
          </label>
          <input
            type="password"
            id="signup-password2"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-900 leading-tight focus:outline-none focus:shadow-outline bg-gray-700 border-gray-600 focus:ring-2 focus:ring-blue-500"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            required
          />
        </div>
        {error && <p className="text-red-500 text-sm italic">{error}</p>}
        <button
          type="submit"
          className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-200 ease-in-out disabled:opacity-50"
          disabled={loading}
        >
          {loading ? 'Signing Up...' : 'Sign Up'}
        </button>
      </form>
      <p className="text-center text-gray-400 text-sm mt-4">
        Already have an account?{' '}
        <button onClick={onSwitchToLogin} className="text-blue-400 hover:text-blue-300 font-bold focus:outline-none">
          Login here
        </button>
      </p>
    </div>
  );
}

export default SignupForm;
