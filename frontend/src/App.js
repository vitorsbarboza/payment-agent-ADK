import React, { useState, useEffect, useRef } from 'react';

// Detect if running in GitHub Codespaces and use the public URL
const API_BASE_URL = window.location.hostname.includes('github.dev') 
  ? `https://${window.location.hostname.replace(/-3000\./, '-8000.')}`
  : 'http://localhost:8000';

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentState, setCurrentState] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Create session on component mount
  useEffect(() => {
    const createSession = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/session/create`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        const data = await response.json();
        setSessionId(data.session_id);
        
        // Add welcome message
        setMessages([
          {
            role: 'assistant',
            content: "Hello! I'm your Send Money Agent. I'll help you transfer money internationally. Who would you like to send money to?",
          },
        ]);
      } catch (error) {
        console.error('Error creating session:', error);
        setMessages([
          {
            role: 'error',
            content: 'Failed to connect to the server. Please refresh the page.',
          },
        ]);
      }
    };

    createSession();
  }, []);

  // Send message to backend
  const sendMessage = async (message) => {
    if (!message.trim() || !sessionId) return;

    // Add user message to chat
    const userMessage = { role: 'user', content: message };
    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: message,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();
      
      // Add assistant response to chat
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setCurrentState(data.state);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'error',
          content: 'Sorry, there was an error processing your message. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(inputMessage);
  };

  // Handle clarification button click
  const handleClarificationClick = (option) => {
    sendMessage(option.label);
  };

  // Check if we need to show clarification buttons
  const showClarificationButtons =
    currentState?.needs_clarification &&
    currentState?.clarification_options?.length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[90vh]">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6">
          <h1 className="text-2xl font-bold flex items-center">
            <svg
              className="w-8 h-8 mr-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Send Money Agent
          </h1>
          <p className="text-blue-100 mt-1 text-sm">
            Fast, secure international money transfers
          </p>
        </div>

        {/* Transfer Status Panel */}
        {currentState && (
          <div className="bg-gray-50 p-4 border-b">
            <div className="text-xs font-semibold text-gray-500 mb-2">
              TRANSFER DETAILS
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {currentState.beneficiary_name && (
                <div className="bg-white p-2 rounded-lg shadow-sm">
                  <div className="text-xs text-gray-500">Beneficiary</div>
                  <div className="font-semibold text-sm">
                    {currentState.beneficiary_name}
                  </div>
                </div>
              )}
              {currentState.destination_country && (
                <div className="bg-white p-2 rounded-lg shadow-sm">
                  <div className="text-xs text-gray-500">Country</div>
                  <div className="font-semibold text-sm">
                    {currentState.destination_country}
                  </div>
                </div>
              )}
              {currentState.amount && (
                <div className="bg-white p-2 rounded-lg shadow-sm">
                  <div className="text-xs text-gray-500">Amount</div>
                  <div className="font-semibold text-sm">
                    ${currentState.amount} {currentState.currency}
                  </div>
                </div>
              )}
              {currentState.delivery_method && (
                <div className="bg-white p-2 rounded-lg shadow-sm">
                  <div className="text-xs text-gray-500">Delivery</div>
                  <div className="font-semibold text-sm">
                    {currentState.delivery_method}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : message.role === 'error'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <div className="text-sm whitespace-pre-wrap">
                  {message.content}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl px-4 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.2s' }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.4s' }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Clarification Buttons */}
        {showClarificationButtons && !isLoading && (
          <div className="px-6 pb-4">
            <div className="text-sm text-gray-600 mb-3 font-medium">
              Please select one:
            </div>
            <div className="grid grid-cols-1 gap-2">
              {currentState.clarification_options.map((option, index) => (
                <button
                  key={index}
                  onClick={() => handleClarificationClick(option)}
                  className="w-full bg-white border-2 border-blue-200 hover:border-blue-500 hover:bg-blue-50 text-left px-4 py-3 rounded-lg transition-all duration-200 text-sm font-medium text-gray-700"
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Form */}
        {!showClarificationButtons && (
          <div className="border-t bg-white p-4">
            <form onSubmit={handleSubmit} className="flex space-x-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type your message..."
                disabled={isLoading || !sessionId}
                className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
              />
              <button
                type="submit"
                disabled={isLoading || !sessionId || !inputMessage.trim()}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200"
              >
                Send
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
