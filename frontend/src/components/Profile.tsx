import React, { useState, useEffect } from 'react';

interface ProfileProps {
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>; // Accept fetchWithAuth prop
}

interface UserProfileData {
  email: string;
  memberSince: string; // Or Date, depending on how you want to parse/display
}

const Profile: React.FC<ProfileProps> = ({ fetchWithAuth }) => { // Destructure fetchWithAuth
  const [userProfile, setUserProfile] = useState<UserProfileData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserProfile = async () => {
      setLoading(true); // Set loading to true at the start of fetch
      setError(null);   // Clear any previous errors

      try {
        // Use fetchWithAuth instead of direct fetch
        const response = await fetchWithAuth('http://127.0.0.1:8000/api/users/me/', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch user profile.');
        }

        const data = await response.json();
        setUserProfile({
          email: data.email,
          memberSince: new Date(data.created_at).toLocaleDateString('en-US', { // Use data.created_at for memberSince
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          }),
        });
      } catch (err: any) {
        setError(err.message);
        console.error("Error fetching user profile:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchUserProfile();
  }, [fetchWithAuth]); // Dependency on fetchWithAuth ensures it re-runs if fetchWithAuth (or its dependencies) change

  if (loading) {
    return <div className="h-full flex items-center justify-center text-white">Loading profile...</div>;
  }

  if (error) {
    return <div className="h-full flex items-center justify-center text-red-500">Error: {error}</div>;
  }

  if (!userProfile) {
    return <div className="h-full flex items-center justify-center text-gray-400">No profile data available.</div>;
  }

  return (
    <div className="h-full bg-gray-800 rounded-lg shadow-lg p-6">
      <h1 className="text-2xl font-bold text-white mb-4">User Profile</h1>
      <div className="space-y-4 text-gray-300">
        <div>
          <label className="block text-gray-400 text-sm font-bold mb-1">Email:</label>
          <p className="text-lg">{userProfile.email}</p>
        </div>
        <div>
          <label className="block text-gray-400 text-sm font-bold mb-1">Member Since:</label>
          <p className="text-lg">{userProfile.memberSince}</p>
        </div>
      </div>
      {/* Future profile editing options will go here */}
      <button className="mt-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md transition-colors duration-200">
        Edit Profile
      </button>
    </div>
  );
};

export default Profile;
