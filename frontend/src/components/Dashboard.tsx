import React from 'react';

// Define the props interface for Dashboard
interface DashboardProps {
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>; // Accepts fetchWithAuth
}

// Update the Dashboard component to receive props
const Dashboard: React.FC<DashboardProps> = ({ fetchWithAuth }) => {
  return (
    <div className="h-full bg-gray-800 rounded-lg shadow-lg p-6">
      <h1 className="text-2xl font-bold text-white mb-4">Analytics Dashboard</h1>
      <p className="text-gray-400">
        This is where you'll see insights into document usage, user activity, and system performance.
      </p>
      {/* Future charts and data visualizations will go here */}
      <div className="mt-8 p-4 bg-gray-700 rounded-md text-gray-300">
        <h3 className="text-lg font-semibold mb-2">Key Metrics (Coming Soon):</h3>
        <ul className="list-disc list-inside space-y-1">
          <li>Total Documents Uploaded</li>
          <li>Average Chat Session Duration</li>
          <li>Most Queried Documents</li>
        </ul>
      </div>
      {/* You can now use fetchWithAuth here if you need to fetch data for the dashboard */}
      {/* Example:
      <button onClick={() => fetchWithAuth('YOUR_ANALYTICS_API_ENDPOINT')}>
        Load Dashboard Data
      </button>
      */}
    </div>
  );
};

export default Dashboard;
