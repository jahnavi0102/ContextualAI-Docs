import React, { useState, useEffect, useCallback, useRef } from 'react';
import { FaPlus, FaPaperPlane, FaSpinner, FaFileAlt } from 'react-icons/fa'; // Import icons

// Define the structure for a single source citation
interface SourceCitation {
  document_id: string;
  filename: string;
  chunk_position: number;
  score: number;
}

interface ChatInterfaceProps {
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  onClose: () => void; 
}

interface ChatSession {
  id: number;
  title: string;
  created_at: string;
}

interface ChatMessage {
  id: number;
  session: number;
  role: 'user' | 'ai';
  content: string;
  timestamp: string;
  // Updated metadata type: it could be a string (if not parsed by DRF) or an object
  metadata?: string | { sources?: SourceCitation[] }; 
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ fetchWithAuth, onClose }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessageContent, setNewMessageContent] = useState<string>('');

  const [loadingSessions, setLoadingSessions] = useState<boolean>(true);
  const [errorSessions, setErrorSessions] = useState<string | null>(null);
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false);
  const [errorMessages, setErrorMessages] = useState<string | null>(null);
  const [sendingMessage, setSendingMessage] = useState<boolean>(false);
  const [sendMessageError, setSendMessageError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null); // Ref for auto-scrolling
  const ws = useRef<WebSocket | null>(null); // Ref to hold the WebSocket instance

  // Helper function to safely parse metadata
  const parseMetadata = (metadata: string | { sources?: SourceCitation[] } | undefined): { sources?: SourceCitation[] } => {
    if (!metadata) return {};
    
    if (typeof metadata === 'string') {
      try {
        const parsed = JSON.parse(metadata);
        console.log('Parsed metadata from string:', parsed); // Debug log
        return parsed;
      } catch (error) {
        console.error('Error parsing metadata string:', error, 'Original metadata:', metadata);
        return {};
      }
    }
    
    console.log('Metadata already parsed:', metadata); // Debug log
    return metadata;
  };

  // Function to scroll to the bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // --- Fetch Chat Sessions ---
  const fetchSessions = useCallback(async () => {
    setLoadingSessions(true);
    setErrorSessions(null);
    try {
      const response = await fetchWithAuth('http://127.0.0.1:8000/api/chat/sessions/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch chat sessions.');
      }

      const data: ChatSession[] = await response.json();
      setSessions(data);
      // If no session is selected and there are sessions, select the first one
      if (data.length > 0 && selectedSessionId === null) {
        setSelectedSessionId(data[0].id);
      } else if (data.length === 0) {
        setSelectedSessionId(null);
      }
    } catch (err: any) {
      setErrorSessions(err.message);
      console.error("Error fetching chat sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  }, [fetchWithAuth, selectedSessionId]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // --- Fetch Messages for Selected Session (Initial load or manual refresh) ---
  const fetchMessages = useCallback(async () => {
    if (selectedSessionId === null) {
      setMessages([]);
      return;
    }

    setLoadingMessages(true);
    setErrorMessages(null);
    try {
      const response = await fetchWithAuth(`http://127.0.0.1:8000/api/chat/sessions/${selectedSessionId}/messages/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch messages.');
      }

      const data: ChatMessage[] = await response.json();
      console.log('Raw fetched messages:', data); // Debug log
      
      // Ensure metadata is parsed if it comes as a string
      const parsedData = data.map(msg => {
        const parsedMetadata = parseMetadata(msg.metadata);
        console.log(`Message ${msg.id} metadata:`, parsedMetadata); // Debug log
        return {
          ...msg,
          metadata: parsedMetadata
        };
      });
      setMessages(parsedData);
    } catch (err: any) {
      setErrorMessages(err.message);
      console.error("Error fetching messages:", err);
    } finally {
      setLoadingMessages(false);
    }
  }, [fetchWithAuth, selectedSessionId]);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // --- WebSocket Connection Management ---
  useEffect(() => {
    if (selectedSessionId === null) {
      if (ws.current) {
        ws.current.close();
      }
      return;
    }

    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      console.warn("No access token found for WebSocket connection. Ensure user is logged in.");
      return; 
    }

    const wsUrl = `ws://127.0.0.1:8000/ws/chat/${selectedSessionId}/?token=${accessToken}`;
    
    if (ws.current) {
      ws.current.close();
    }

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log(`WebSocket connected for session ${selectedSessionId}`);
    };

    ws.current.onmessage = (event) => {
      try {
        const receivedData = JSON.parse(event.data);
        console.log('Raw WebSocket message received:', receivedData); // Debug log
        
        // The WebSocket message might have a 'message' property containing the actual ChatMessage
        const receivedMessage: ChatMessage = receivedData.message || receivedData;
        console.log('Processed WebSocket message:', receivedMessage); // Debug log

        setMessages(prev => {
          const exists = prev.some(msg => msg.id === receivedMessage.id);
          if (!exists) {
            // Parse metadata if it's a string from WebSocket
            const parsedMetadata = parseMetadata(receivedMessage.metadata);
            const processedMessage = {
              ...receivedMessage,
              metadata: parsedMetadata
            };
            console.log('Adding processed message:', processedMessage); // Debug log
            return [...prev, processedMessage];
          }
          return prev;
        });
      } catch (error) {
        console.error("Error parsing WebSocket message:", error, "Raw data:", event.data);
      }
    };

    ws.current.onerror = (error) => {
      console.error(`WebSocket error for session ${selectedSessionId}:`, error);
      setErrorMessages('WebSocket error. Messages might not be real-time. Check backend server and token.');
    };

    ws.current.onclose = (event) => {
      console.log(`WebSocket disconnected for session ${selectedSessionId}. Code: ${event.code}, Reason: ${event.reason}`);
      if (event.code !== 1000) { 
        console.log("Attempting to reconnect WebSocket...");
        setTimeout(() => {
          setSelectedSessionId(selectedSessionId); 
        }, 3000); 
      }
    };

    return () => {
      if (ws.current) {
        console.log(`Closing WebSocket for session ${selectedSessionId}`);
        ws.current.close();
      }
    };
  }, [selectedSessionId]); 

  // --- Create New Chat Session ---
  const handleCreateNewSession = async () => {
    setLoadingSessions(true); 
    setErrorSessions(null);
    try {
      const response = await fetchWithAuth('http://127.0.0.1:8000/api/chat/sessions/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}), 
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create new session.');
      }

      const newSession: ChatSession = await response.json();
      setSessions(prev => [newSession, ...prev]); 
      setSelectedSessionId(newSession.id); 
      setMessages([]); 
      setNewMessageContent(''); 
    } catch (err: any) {
      setErrorSessions(err.message);
      console.error("Error creating new session:", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  // --- Send Message ---
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessageContent.trim() || selectedSessionId === null) {
      setSendMessageError('Message cannot be empty or no session selected.');
      return;
    }

    setSendingMessage(true);
    setSendMessageError(null);

    let userMessage: ChatMessage | undefined; 

    try {
      userMessage = { 
        id: Date.now(), 
        session: selectedSessionId,
        role: 'user',
        content: newMessageContent,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMessage!]); 
      setNewMessageContent('');

      const response = await fetchWithAuth(`http://127.0.0.1:8000/api/chat/sessions/${selectedSessionId}/send/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: userMessage.content }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to send message.');
      }

    } catch (err: any) {
      setSendMessageError(err.message);
      console.error("Error sending message:", err);
      if (userMessage) { 
        setMessages(prev => prev.filter(msg => msg.id !== userMessage!.id)); 
      }
    } finally {
      setSendingMessage(false);
    }
  };

  return (
    <div className="flex h-full rounded-lg shadow-lg bg-gray-800 text-white">
      {/* Sidebar for Chat Sessions */}
      <div className="w-1/4 border-r border-gray-700 p-4 flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Chats</h2>
          <button
            onClick={handleCreateNewSession}
            className="p-2 bg-blue-600 hover:bg-blue-700 rounded-full transition-colors duration-200"
            title="Start New Chat"
            disabled={loadingSessions}
          >
            {loadingSessions ? <FaSpinner className="animate-spin" /> : <FaPlus />}
          </button>
        </div>
        {errorSessions && <p className="text-red-400 text-sm mb-2">{errorSessions}</p>}
        {loadingSessions ? (
          <p className="text-gray-400">Loading sessions...</p>
        ) : sessions.length === 0 ? (
          <p className="text-gray-400">No chat sessions. Start a new one!</p>
        ) : (
          <div className="flex-grow overflow-y-auto pr-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => setSelectedSessionId(session.id)}
                className={`w-full text-left p-3 mb-2 rounded-lg transition-colors duration-200
                  ${selectedSessionId === session.id ? 'bg-blue-700' : 'hover:bg-gray-700 bg-gray-600'}`}
              >
                <h3 className="font-semibold text-lg">{session.title || `Chat ${session.id}`}</h3>
                <p className="text-xs text-gray-400">Created: {new Date(session.created_at).toLocaleDateString()}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="flex-grow p-4 overflow-y-auto bg-gray-700 rounded-tr-lg" style={{ minHeight: '100px' }}>
          {loadingMessages ? (
            <div className="flex items-center justify-center h-full text-gray-400">Loading messages...</div>
          ) : errorMessages ? (
            <div className="flex items-center justify-center h-full text-red-400">Error: {errorMessages}</div>
          ) : selectedSessionId === null ? (
            <div className="flex items-center justify-center h-full text-gray-400">Select a chat or start a new one.</div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-400">No messages yet. Send your first message!</div>
          ) : (
            messages.map((message) => {
              // Safely parse metadata - should already be parsed but double-check
              const parsedMetadata = parseMetadata(message.metadata);
              console.log(`Rendering message ${message.id}, metadata:`, parsedMetadata); // Debug log

              return (
                <div
                  key={message.id}
                  className={`mb-4 p-3 rounded-lg max-w-3/4 ${
                    message.role === 'user' ? 'bg-blue-600 ml-auto' : 'bg-gray-600 mr-auto'
                  }`}
                >
                  <p className="font-semibold text-sm capitalize mb-1">{message.role === 'user' ? 'You' : 'DocAI'}</p>
                  <p className="text-base whitespace-pre-wrap">{message.content}</p>
                  <p className="text-xs text-gray-400 text-right mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>

                  {/* --- Source Citations Display --- */}
                  {message.role === 'ai' && parsedMetadata && parsedMetadata.sources && Array.isArray(parsedMetadata.sources) && parsedMetadata.sources.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-gray-500 bg-gray-700 rounded-lg p-2">
                      <div className="flex items-center mb-2">
                        <FaFileAlt className="mr-2 text-blue-400" />
                        <p className="font-semibold text-sm text-blue-300">Sources ({parsedMetadata.sources.length}):</p>
                      </div>
                      <ul className="space-y-1">
                        {parsedMetadata.sources.map((source, index) => (
                          <li key={index} className="text-xs text-gray-300 bg-gray-800 rounded p-2">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <p className="font-medium text-blue-200">{source.filename}</p>
                                <p className="text-gray-400">Chunk: {source.chunk_position}</p>
                              </div>
                              <div className="text-right ml-2">
                                <span className={`px-2 py-1 rounded text-xs ${
                                  source.score > 0.8 ? 'bg-green-600' : 
                                  source.score > 0.6 ? 'bg-yellow-600' : 'bg-red-600'
                                }`}>
                                  {(source.score * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Debug info - remove this in production */}
                  {message.role === 'ai' && process.env.NODE_ENV === 'development' && (
                    <div className="mt-2 text-xs text-gray-500">
                      <details>
                        <summary>Debug: Raw Metadata</summary>
                        <pre className="bg-gray-900 p-2 rounded text-xs overflow-x-auto">
                          {JSON.stringify(message.metadata, null, 2)}
                        </pre>
                      </details>
                    </div>
                  )}
                  {/* --- End Source Citations Display --- */}
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} /> {/* For auto-scrolling */}
        </div>

        {/* Message Input */}
        {selectedSessionId !== null && (
          <form onSubmit={handleSendMessage} className="p-4 border-t border-gray-600 bg-gray-800 rounded-br-lg flex items-center">
            <textarea
              value={newMessageContent}
              onChange={(e) => setNewMessageContent(e.target.value)}
              placeholder="Type your message..."
              rows={1}
              className="flex-grow p-3 rounded-lg bg-gray-700 text-white border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 mr-3 resize-none"
              disabled={sendingMessage}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
            />
            <button
              type="submit"
              className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200"
              disabled={sendingMessage || !newMessageContent.trim()}
            >
              {sendingMessage ? <FaSpinner className="animate-spin" /> : <FaPaperPlane />}
            </button>
            {sendMessageError && <p className="text-red-400 text-sm ml-3">{sendMessageError}</p>}
          </form>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;