import React, { useState, useEffect, useCallback } from 'react';
import { FaUpload } from 'react-icons/fa'; // Import the upload icon

interface DocumentLibraryProps {
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
}

interface Document {
  id: number;
  filename: string;
  status: string;
  created_at: string;
  size: number;
  file: string; // The URL to the actual file
  // Add other fields you expect from your Document model/serializer
}

const DocumentLibrary: React.FC<DocumentLibraryProps> = ({ fetchWithAuth }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // States for the integrated file upload
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Make fetchDocuments a useCallback to avoid re-creating it unnecessarily
  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth('http://127.0.0.1:8000/api/documents/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch documents.');
      }

      const data: Document[] = await response.json();
      setDocuments(data);
    } catch (err: any) {
      setError(err.message);
      console.error("Error fetching documents:", err);
    } finally {
      setLoading(false);
    }
  }, [fetchWithAuth]); // Dependency on fetchWithAuth

  useEffect(() => {
    fetchDocuments(); // Initial fetch when component mounts
  }, [fetchDocuments]); // Re-run effect if fetchDocuments changes

  // Handles when a file is selected by the user
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
      setUploadError(null); // Clear any previous errors
    } else {
      setSelectedFile(null);
    }
  };

  // Handles the actual file upload when the button is clicked
  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file to upload.');
      return;
    }

    setUploading(true); // Set loading state for upload
    setUploadError(null); // Clear previous errors

    const formData = new FormData();
    formData.append('file', selectedFile); // The key 'file' must match your Django serializer's field name

    // No metadata input from frontend user, if metadata is needed, it will be added programmatically
    // For now, no metadata is appended by the frontend user.

    try {
      const response = await fetchWithAuth('http://127.0.0.1:8000/api/documents/upload/', {
        method: 'POST',
        body: formData, // When using FormData, the browser automatically sets 'Content-Type': 'multipart/form-data'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || errorData.file || 'File upload failed.');
      }

      const result = await response.json();
      console.log('Upload successful:', result);
      setSelectedFile(null); // Clear the selected file input
      (document.getElementById('file-upload') as HTMLInputElement).value = ''; // Reset input field
      fetchDocuments(); // Re-fetch the list of documents after successful upload

    } catch (error: any) {
      setUploadError(error.message);
      console.error('Upload error:', error);
    } finally {
      setUploading(false); // Reset loading state
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900 text-white text-xl">
        Loading documents...
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center text-red-500 text-xl">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-800 rounded-lg shadow-lg p-6 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-white">Your Document Library</h1>
        
        {/* Simplified Upload Button/Icon */}
        <label htmlFor="file-upload" 
          className={`cursor-pointer font-bold py-2 px-4 rounded-lg flex items-center transition-colors duration-200 
            ${uploading ? 'bg-gray-500 text-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white'}`}
        >
          <FaUpload className="mr-2" />
          {uploading ? 'Uploading...' : 'Upload Document'}
          <input
            id="file-upload"
            type="file"
            onChange={handleFileChange}
            className="hidden" // Hide the default file input
            disabled={uploading} // Disable the input while uploading
          />
        </label>
        {selectedFile && !uploading && !uploadError && (
          <button
            onClick={handleUpload}
            className="ml-4 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200 ease-in-out"
            disabled={uploading} // Explicitly disable this button while uploading
          >
            Confirm Upload
          </button>
        )}
      </div>
      {uploadError && <p className="text-red-400 text-sm mb-4 text-right">{uploadError}</p>}
      {selectedFile && !uploading && !uploadError && (
        <p className="text-gray-300 text-sm mb-4 text-right">Selected: {selectedFile.name}</p>
      )}


      {/* Scrollable Document List */}
      <div className="flex-grow overflow-y-auto mt-4 pr-2"> {/* Added flex-grow and overflow-y-auto */}
        {documents.length === 0 ? (
          <p className="text-gray-400 text-lg text-center mt-8">No documents uploaded yet.</p>
        ) : (
          <table className="min-w-full bg-gray-700 rounded-lg overflow-hidden">
            <thead className="bg-gray-600 sticky top-0 z-10"> {/* Made header sticky */}
              <tr>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Filename</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Size</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Status</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Uploaded At</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-600">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-650">
                  <td className="py-3 px-4 text-sm font-medium text-white">{doc.filename}</td>
                  <td className="py-3 px-4 text-sm text-gray-300">{Math.round(doc.size / 1024)} KB</td>
                  <td className="py-3 px-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      doc.status === 'completed' ? 'bg-green-500 text-green-900' :
                      doc.status === 'processing' ? 'bg-yellow-500 text-yellow-900' :
                      'bg-red-500 text-red-900'
                    }`}>
                      {doc.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-300">{new Date(doc.created_at).toLocaleDateString()}</td>
                  <td className="py-3 px-4 text-sm">
                    {doc.file && (
                      <a 
                        href={doc.file} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="text-blue-400 hover:text-blue-300 mr-2"
                      >
                        View
                      </a>
                    )}
                    {/* Add more actions like Delete, Chat with document, etc. */}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default DocumentLibrary;
