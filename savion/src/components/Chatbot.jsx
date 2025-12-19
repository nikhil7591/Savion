import React, { useState, useEffect, useRef } from 'react';
import { FaRobot, FaUser, FaPaperPlane, FaMicrophone, FaStop, FaUpload, FaFileCsv, FaBolt, FaHistory } from 'react-icons/fa';
import './Chatbot.css';

const Chatbot = ({ userId, onClose }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Hi! I\'m your Smart Personal Finance Assistant powered by Gemini AI. I can analyze your uploaded data and provide intelligent insights:\n\n• 📊 Analyze your CSV/Excel financial data\n• 💡 Personalized spending insights and recommendations\n• 🔮 Predict future financial trends\n• 🚨 Detect unusual spending patterns\n• 🎯 Help set and track financial goals\n• 📈 Real-time data analysis and chat\n\nUpload your financial data or ask me anything about your finances!',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [websocket, setWebsocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [useGemini, setUseGemini] = useState(true);
  const [uploadingFile, setUploadingFile] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // WebSocket connection
  useEffect(() => {
    if (useGemini && userId) {
      const ws = new WebSocket(`ws://localhost:8000/ws/${userId}`);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setWebsocket(ws);
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'connection_established') {
          console.log('Connection established:', data.message);
          return;
        }
        handleWebSocketMessage(data);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setWebsocket(null);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
      
      return () => {
        ws.close();
      };
    }
  }, [useGemini, userId]);

  const handleWebSocketMessage = (data) => {
    if (!data || !data.type) {
      console.error('Invalid message format:', data);
      return;
    }

    switch (data.type) {
      case 'ai_response':
        if (data.response) {
          const botMessage = {
            id: Date.now(),
            type: 'bot',
            content: data.response,
            insights: data.insights || [],
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setIsLoading(false);
        }
        break;
      case 'typing':
        setIsLoading(true);
        break;
      case 'error':
        const errorMessage = {
          id: Date.now(),
          type: 'bot',
          content: `❌ ${data.message || 'An error occurred'}`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
        setIsLoading(false);
        break;
      case 'notification':
        const notificationMessage = {
          id: Date.now(),
          type: 'bot',
          content: `🔔 ${data.message}`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, notificationMessage]);
        break;
      case 'connection_established':
        console.log('Connection established:', data.message);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const sendMessage = async (messageText) => {
    if (!messageText.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: messageText,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Use WebSocket if connected, otherwise fallback to HTTP
      if (useGemini && websocket && isConnected) {
        websocket.send(JSON.stringify({
          type: 'chat',
          content: messageText
        }));
        setIsLoading(false);
        return;
      }

      // Fallback to HTTP API
      const endpoint = useGemini ? '/api/gemini/chat' : '/api/chat';
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          query: messageText
        })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      
      let botResponse = '';
      
      // Handle Gemini AI response
      if (data.type === 'gemini_response') {
        botResponse = data.response;
        
        // Add insights if available
        if (data.insights && data.insights.length > 0) {
          botResponse += '\n\n**Key Insights:**\n' + data.insights.map(insight => `• ${insight}`).join('\n');
        }
      } else {
        // Format response based on type (legacy format)
        switch (data.type) {
        case 'spending_analysis':
          botResponse = `📊 **Spending Analysis**\n\n`;
          botResponse += `Total spent: ₹${data.total_spent?.toLocaleString() || '0'}\n`;
          botResponse += `Period: ${data.period || 'All time'}\n`;
          if (data.category) {
            botResponse += `Category: ${data.category}\n`;
          }
          botResponse += `Transactions: ${data.transaction_count || 0}\n\n`;
          if (data.insights && data.insights.length > 0) {
            botResponse += `**Insights:**\n${data.insights.map(insight => `• ${insight}`).join('\n')}`;
          }
          break;

        case 'budget_analysis':
          botResponse = `💰 **Budget Analysis**\n\n`;
          botResponse += `Total spent: ₹${data.total_spent?.toLocaleString() || '0'}\n`;
          botResponse += `Budget: ₹${data.budget_amount?.toLocaleString() || 'N/A'}\n`;
          botResponse += `Status: ${data.status === 'over' ? '❌ Over budget' : '✅ Under budget'}\n`;
          if (data.overspend_amount) {
            botResponse += `Overspend: ₹${data.overspend_amount.toLocaleString()}\n`;
          }
          botResponse += `Percentage: ${data.percentage?.toFixed(1) || 0}%\n\n`;
          if (data.recommendations && data.recommendations.length > 0) {
            botResponse += `**Recommendations:**\n${data.recommendations.map(rec => `• ${rec}`).join('\n')}`;
          }
          break;

        case 'prediction':
          if (data.error) {
            botResponse = `⚠️ ${data.error}`;
          } else {
            botResponse = `🔮 **Spending Prediction**\n\n`;
            botResponse += `Average predicted spending: ₹${data.average_predicted?.toLocaleString() || '0'}\n\n`;
            botResponse += `**Next 4 periods:**\n`;
            data.forecast?.forEach((amount, index) => {
              botResponse += `Period ${index + 1}: ₹${amount.toLocaleString()}\n`;
            });
            if (data.budget_limit) {
              botResponse += `\nBudget limit: ₹${data.budget_limit.toLocaleString()}\n`;
              botResponse += `Will exceed budget: ${data.will_exceed_budget ? '❌ Yes' : '✅ No'}\n`;
            }
            if (data.recommendations && data.recommendations.length > 0) {
              botResponse += `\n**Recommendations:**\n${data.recommendations.map(rec => `• ${rec}`).join('\n')}`;
            }
          }
          break;

        case 'anomaly_detection':
          if (data.error) {
            botResponse = `⚠️ ${data.error}`;
          } else {
            botResponse = `🚨 **Anomaly Detection**\n\n`;
            botResponse += `Found ${data.anomaly_count || 0} unusual transactions\n\n`;
            if (data.anomalies && data.anomalies.length > 0) {
              botResponse += `**Unusual transactions:**\n`;
              data.anomalies.forEach((anomaly, index) => {
                const tx = anomaly.transaction;
                botResponse += `${index + 1}. ₹${tx.amount.toLocaleString()} for ${tx.category} on ${new Date(tx.date).toLocaleDateString()}\n`;
                botResponse += `   Reason: ${anomaly.reason}\n\n`;
              });
            }
            if (data.recommendations && data.recommendations.length > 0) {
              botResponse += `**Recommendations:**\n${data.recommendations.map(rec => `• ${rec}`).join('\n')}`;
            }
          }
          break;

        case 'goal_setting':
          if (data.error) {
            botResponse = `⚠️ ${data.error}\n\n**Suggestions:**\n${data.suggestions?.map(s => `• ${s}`).join('\n') || ''}`;
          } else {
            botResponse = `🎯 **Savings Goal**\n\n`;
            botResponse += `Goal: ₹${data.goal_amount?.toLocaleString() || '0'}\n`;
            botResponse += `Timeframe: ${data.timeframe || 'N/A'}\n`;
            botResponse += `Required monthly savings: ₹${data.required_monthly_savings?.toLocaleString() || '0'}\n`;
            botResponse += `Current savings: ₹${data.current_savings?.toLocaleString() || '0'}\n`;
            botResponse += `Feasible: ${data.feasible ? '✅ Yes' : '❌ No'}\n\n`;
            if (data.recommendations && data.recommendations.length > 0) {
              botResponse += `**Recommendations:**\n${data.recommendations.map(rec => `• ${rec}`).join('\n')}`;
            }
          }
          break;

        case 'summary':
          botResponse = `📈 **Financial Summary**\n\n`;
          botResponse += `Period: ${data.period || 'All time'}\n`;
          botResponse += `Total Income: ₹${data.total_income?.toLocaleString() || '0'}\n`;
          botResponse += `Total Expenses: ₹${data.total_expenses?.toLocaleString() || '0'}\n`;
          botResponse += `Balance: ₹${data.balance?.toLocaleString() || '0'}\n`;
          botResponse += `Transactions: ${data.transaction_count || 0}\n\n`;
          if (data.categories && Object.keys(data.categories).length > 0) {
            botResponse += `**Expense Categories:**\n`;
            Object.entries(data.categories).forEach(([category, amount]) => {
              botResponse += `• ${category}: ₹${amount.toLocaleString()}\n`;
            });
            botResponse += '\n';
          }
          if (data.insights && data.insights.length > 0) {
            botResponse += `**Insights:**\n${data.insights.map(insight => `• ${insight}`).join('\n')}`;
          }
          break;

        case 'general':
          botResponse = data.response || 'I can help you with your financial queries!';
          if (data.suggestions && data.suggestions.length > 0) {
            botResponse += `\n\n**Try asking:**\n${data.suggestions.map(s => `• ${s}`).join('\n')}`;
          }
          break;

        case 'error':
          botResponse = `❌ ${data.error || 'Something went wrong'}\n\n`;
          if (data.suggestions && data.suggestions.length > 0) {
            botResponse += `**Try asking:**\n${data.suggestions.map(s => `• ${s}`).join('\n')}`;
          }
          break;

        default:
          botResponse = data.response || 'I received your message but couldn\'t process it properly.';
        }
      }

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: botResponse,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: `❌ Sorry, I encountered an error: ${error.message}\n\nPlease try again or contact support if the issue persists.`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      setMediaRecorder(recorder);
      setIsRecording(true);

      const chunks = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', blob, 'voice.webm');

        try {
          const response = await fetch('http://localhost:8000/api/transcribe', {
            method: 'POST',
            body: formData,
          });

          if (response.ok) {
            const data = await response.json();
            if (data.text) {
              sendMessage(data.text);
            }
          }
        } catch (error) {
          console.error('Voice transcription error:', error);
        }

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
        setIsRecording(false);
      };

      recorder.start();
    } catch (error) {
      console.error('Voice recording error:', error);
      alert('Please allow microphone access to use voice input.');
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file type
    const allowedTypes = ['.csv', '.xlsx', '.xls'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!allowedTypes.includes(fileExtension)) {
      alert('Please upload a CSV or Excel file (.csv, .xlsx, .xls)');
      return;
    }

    setUploadingFile(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`http://localhost:8000/api/upload_csv?user_id=${userId}`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      
      if (result.success) {
        const uploadMessage = {
          id: Date.now(),
          type: 'bot',
          content: `✅ File uploaded successfully!\n\n📊 **Upload Summary:**\n• File: ${file.name}\n• Records processed: ${result.inserted}\n• Total rows: ${result.total_rows}\n${result.error_count > 0 ? `• Errors: ${result.error_count}\n` : ''}\n\nI can now analyze your financial data! Try asking me about your spending patterns, budget, or financial insights.`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, uploadMessage]);
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = {
        id: Date.now(),
        type: 'bot',
        content: `❌ Upload failed: ${error.message}\n\nPlease make sure your file has the required columns: date, type, category, amount`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setUploadingFile(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const clearChatHistory = async () => {
    if (useGemini) {
      try {
        await fetch(`http://localhost:8000/api/gemini/clear-history/${userId}`, {
          method: 'DELETE'
        });
      } catch (error) {
        console.error('Error clearing history:', error);
      }
    }
    
    setMessages([{
      id: 1,
      type: 'bot',
      content: 'Chat history cleared! How can I help you with your finances today?',
      timestamp: new Date()
    }]);
  };

  const toggleAI = () => {
    setUseGemini(!useGemini);
    if (websocket) {
      websocket.close();
    }
  };

  const quickActions = [
    { label: '📊 Data Analysis', query: 'Analyze my financial data and provide insights' },
    { label: '💰 Spending Summary', query: 'Show me my spending summary for this month' },
    { label: '🎯 Budget Check', query: 'Am I overspending this month?' },
    { label: '🔮 Predict Spending', query: 'Predict my spending for next month' },
    { label: '🚨 Find Anomalies', query: 'Check for unusual transactions this week' },
    { label: '💎 Set Goal', query: 'Help me save ₹50,000 in 6 months' },
    { label: '📈 Investment Advice', query: 'Give me investment advice based on my finances' }
  ];

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <div className="chatbot-title">
          <FaRobot className="chatbot-icon" />
          <span>Smart Finance Assistant {useGemini ? '(Gemini AI)' : '(Basic)'}</span>
          <div className="connection-status">
            {useGemini && (
              <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
                {isConnected ? '🟢 Live' : '🔴 Offline'}
              </span>
            )}
          </div>
        </div>
        <div className="header-controls">
          <button 
            className={`ai-toggle ${useGemini ? 'active' : ''}`}
            onClick={toggleAI}
            title={useGemini ? 'Switch to Basic Mode' : 'Switch to Gemini AI Mode'}
          >
            <FaBolt />
          </button>
          <button 
            className="clear-history-btn"
            onClick={clearChatHistory}
            title="Clear Chat History"
          >
            <FaHistory />
          </button>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-avatar">
              {message.type === 'bot' ? <FaRobot /> : <FaUser />}
            </div>
            <div className="message-content">
              <div className="message-text">
                {message.content.split('\n').map((line, index) => (
                  <div key={index}>
                    {line.includes('**') ? (
                      <div dangerouslySetInnerHTML={{
                        __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      }} />
                    ) : (
                      line
                    )}
                  </div>
                ))}
              </div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message bot">
            <div className="message-avatar">
              <FaRobot />
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="file-upload-section">
        <div className="upload-header">
          <FaFileCsv className="upload-icon" />
          <span>Upload Your Financial Data</span>
        </div>
        <div className="upload-controls">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
          <button
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingFile || isLoading}
          >
            <FaUpload />
            {uploadingFile ? 'Uploading...' : 'Choose File'}
          </button>
          <span className="upload-hint">
            Supports CSV and Excel files with date, type, category, amount columns
          </span>
        </div>
      </div>

      <div className="quick-actions">
        <div className="quick-actions-title">Quick Actions:</div>
        <div className="quick-actions-buttons">
          {quickActions.map((action, index) => (
            <button
              key={index}
              className="quick-action-btn"
              onClick={() => sendMessage(action.query)}
              disabled={isLoading}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      <form className="chatbot-input" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask me anything about your finances..."
          disabled={isLoading}
        />
        <button
          type="button"
          className={`voice-btn ${isRecording ? 'recording' : ''}`}
          onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
          disabled={isLoading}
        >
          {isRecording ? <FaStop /> : <FaMicrophone />}
        </button>
        <button type="submit" disabled={isLoading || !inputValue.trim()}>
          <FaPaperPlane />
        </button>
      </form>
    </div>
  );
};

export default Chatbot;
