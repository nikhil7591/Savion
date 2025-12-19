import React, { useState, useEffect, useRef } from "react";
import {
  FaRobot,
  FaUser,
  FaPaperPlane,
  FaMicrophone,
  FaStop,
  FaUpload,
  FaFileCsv,
  FaBolt,
  FaHistory,
} from "react-icons/fa";
import "./Chatbot.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const defaultWelcome = `Hi! I'm your Smart Personal Finance Assistant powered by Gemini AI.
I can analyze your uploaded data and provide insights:
• Analyze CSV/Excel financial data
• Personalized spending insights and recommendations
• Predict future financial trends
• Detect unusual spending patterns
• Help set and track financial goals
Upload your financial data or ask me anything about your finances!`;

const Chatbot = ({ userId, onClose }) => {
  const [messages, setMessages] = useState([
    { id: 1, type: "bot", content: defaultWelcome, timestamp: new Date() },
  ]);

  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectRef = useRef({ attempts: 0, timeoutId: null });
  const [isConnected, setIsConnected] = useState(false);
  const [useGemini, setUseGemini] = useState(true);
  const [uploadingFile, setUploadingFile] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Build websocket URL
  const wsUrl = () => `ws://localhost:8000/ws/${userId}`;

  // Connect WebSocket (with reconnection/backoff)
  useEffect(() => {
    if (!useGemini || !userId) return;

    let ws;
    const connect = () => {
      ws = new WebSocket(wsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        reconnectRef.current.attempts = 0;
        // Optionally inform backend to send a welcome or register user
        ws.send(JSON.stringify({ type: "connection_init", content: "Hello from client" }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (e) {
          console.warn("WS non-JSON message:", event.data);
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
      };

      ws.onclose = (ev) => {
        console.log("WebSocket closed", ev);
        setIsConnected(false);
        // Reconnect with backoff
        if (useGemini) {
          const attempts = reconnectRef.current.attempts + 1;
          reconnectRef.current.attempts = attempts;
          const delay = Math.min(30000, 500 * 2 ** attempts); // expo backoff (max 30s)
          reconnectRef.current.timeoutId = setTimeout(connect, delay);
          console.log(`Reconnecting WebSocket in ${delay}ms (attempt ${attempts})`);
        }
      };
    };

    connect();

    return () => {
      // cleanup
      if (reconnectRef.current.timeoutId) clearTimeout(reconnectRef.current.timeoutId);
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
    };
  }, [useGemini, userId]);

  // WebSocket message handler
  const handleWebSocketMessage = (data) => {
    if (!data) return;
    // Accept a variety of field names to maximize compatibility
    const t = data.type || data.event || "";
    switch (t) {
      case "ai_response":
      case "reply":
      case "response":
      case "gemini_response": {
        const content = data.content ?? data.response ?? data.message ?? "";
        const botMessage = {
          id: Date.now(),
          type: "bot",
          content: content || JSON.stringify(data),
          insights: data.insights || [],
          timestamp: new Date(),
        };
        setMessages((m) => [...m, botMessage]);
        setIsLoading(false);
        break;
      }
      case "typing": {
        setIsLoading(true);
        break;
      }
      case "notification": {
        const botMessage = {
          id: Date.now(),
          type: "bot",
          content: `🔔 ${data.message || data.content || ""}`,
          timestamp: new Date(),
        };
        setMessages((m) => [...m, botMessage]);
        break;
      }
      case "error": {
        const botMessage = {
          id: Date.now(),
          type: "bot",
          content: `❌ ${data.message || data.error || "An error occurred"}`,
          timestamp: new Date(),
        };
        setMessages((m) => [...m, botMessage]);
        setIsLoading(false);
        break;
      }
      case "connection_established": {
        const botMessage = {
          id: Date.now(),
          type: "bot",
          content: data.message || "Connected to Savion Smart Finance Assistant.",
          timestamp: new Date(),
        };
        setMessages((m) => [...m, botMessage]);
        break;
      }
      default: {
        // Fallback: attach raw content if present
        if (data.content || data.response || data.message) {
          const botMessage = {
            id: Date.now(),
            type: "bot",
            content: data.content ?? data.response ?? data.message,
            timestamp: new Date(),
          };
          setMessages((m) => [...m, botMessage]);
        } else {
          console.debug("Unhandled WS message:", data);
        }
      }
    }
  };

  // Send a message: prefer WebSocket when possible, otherwise HTTP fallback
  const sendMessage = async (messageText) => {
    if (!messageText || !messageText.trim()) return;
    const userMessage = {
      id: Date.now(),
      type: "user",
      content: messageText,
      timestamp: new Date(),
    };
    setMessages((m) => [...m, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // If websocket connected and using Gemini, send via WS
    if (useGemini && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: "chat", content: messageText }));
        // Let backend send responses via websocket; keep loading indicator until response.
        return;
      } catch (err) {
        console.warn("WebSocket send failed, falling back to HTTP:", err);
      }
    }

    // HTTP fallback
    try {
      const endpoint = useGemini ? "/api/gemini/chat" : "/api/chat";
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, query: messageText }),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Server error ${res.status}: ${txt}`);
      }
      const data = await res.json();

      // Handle various response shapes
      let botResponse = "";
      if (data?.response) botResponse = data.response;
      else if (data?.type === "gemini_response" && data.response) botResponse = data.response;
      else {
        // Generic fallback: stringify object or show message
        botResponse = data?.message || JSON.stringify(data);
      }

      // Add insights if present (makes user-facing content friendly)
      if (data?.insights && Array.isArray(data.insights) && data.insights.length) {
        botResponse += `\n\n**Key Insights:**\n${data.insights.map((i) => `• ${i}`).join("\n")}`;
      }

      setMessages((m) => [
        ...m,
        { id: Date.now() + 1, type: "bot", content: botResponse, timestamp: new Date() },
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((m) => [
        ...m,
        {
          id: Date.now() + 1,
          type: "bot",
          content: `❌ Sorry, I couldn't send your message: ${err.message}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Form submit handler
  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  // Voice recording handlers
  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunks.push(ev.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const fd = new FormData();
        fd.append("file", blob, "voice.webm");

        try {
          const res = await fetch(`${API_BASE}/api/transcribe`, { method: "POST", body: fd });
          if (!res.ok) {
            const t = await res.text();
            throw new Error(`Transcription failed: ${t}`);
          }
          const data = await res.json();
          if (data?.text) {
            sendMessage(data.text);
          } else {
            throw new Error("No text returned from transcription");
          }
        } catch (err) {
          console.error("Voice transcription error:", err);
          setMessages((m) => [
            ...m,
            {
              id: Date.now(),
              type: "bot",
              content: `❌ Voice transcription failed: ${err.message}`,
              timestamp: new Date(),
            },
          ]);
        } finally {
          stream.getTracks?.().forEach((t) => t.stop());
          setIsRecording(false);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Start recording error:", err);
      alert("Please allow microphone access to use voice input.");
    }
  };

  const stopVoiceRecording = () => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    } catch (err) {
      console.warn("Stop recording error:", err);
    }
  };

  // File upload handler (CSV/Excel)
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const allowed = [".csv", ".xlsx", ".xls"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(ext)) {
      alert("Please upload .csv, .xlsx, or .xls file.");
      return;
    }

    setUploadingFile(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/api/upload_csv?user_id=${userId}`, {
        method: "POST",
        body: formData,
      });
      const result = await res.json();
      if (res.ok && result.success) {
        setMessages((m) => [
          ...m,
          {
            id: Date.now(),
            type: "bot",
            content: `✅ File uploaded: ${file.name}\nProcessed: ${result.inserted || 0} rows.`,
            timestamp: new Date(),
          },
        ]);
      } else {
        throw new Error(result.error || "Upload failed");
      }
    } catch (err) {
      console.error("Upload error:", err);
      setMessages((m) => [
        ...m,
        {
          id: Date.now(),
          type: "bot",
          content: `❌ Upload failed: ${err.message}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setUploadingFile(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Clear chat history both locally and optionally server-side
  const clearChatHistory = async () => {
    try {
      if (useGemini) {
        await fetch(`${API_BASE}/api/gemini/clear-history/${userId}`, { method: "DELETE" });
      }
    } catch (err) {
      console.warn("Error clearing server history:", err);
    }
    setMessages([{ id: 1, type: "bot", content: "Chat history cleared. How can I help you now?", timestamp: new Date() }]);
  };

  // Toggle AI mode
  const toggleAI = () => {
    setUseGemini((s) => !s);
    // Close websocket if open
    try {
      wsRef.current?.close();
      wsRef.current = null;
      setIsConnected(false);
    } catch {}
  };

  // Quick actions
  const quickActions = [
    { label: "📊 Data Analysis", query: "Analyze my financial data and provide insights" },
    { label: "💰 Spending Summary", query: "Show me my spending summary for this month" },
    { label: "🎯 Budget Check", query: "Am I overspending this month?" },
    { label: "🔮 Predict Spending", query: "Predict my spending for next month" },
    { label: "🚨 Find Anomalies", query: "Check for unusual transactions this week" },
    { label: "💎 Set Goal", query: "Help me save ₹50,000 in 6 months" },
    { label: "📈 Investment Advice", query: "Give me investment advice based on my finances" },
  ];

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <div className="chatbot-title">
          <FaRobot className="chatbot-icon" />
          <span>Smart Finance Assistant {useGemini ? "(Gemini AI)" : "(Basic)"}</span>
          <div className="connection-status">
            {useGemini && (
              <span className={`status-indicator ${isConnected ? "connected" : "disconnected"}`}>
                {isConnected ? "🟢 Live" : "🔴 Offline"}
              </span>
            )}
          </div>
        </div>

        <div className="header-controls">
          <button className={`ai-toggle ${useGemini ? "active" : ""}`} onClick={toggleAI} title={useGemini ? "Switch to Basic Mode" : "Switch to Gemini AI Mode"}>
            <FaBolt />
          </button>

          <button className="clear-history-btn" onClick={clearChatHistory} title="Clear Chat History">
            <FaHistory />
          </button>

          <button className="close-btn" onClick={onClose}>×</button>
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-avatar">{message.type === "bot" ? <FaRobot /> : <FaUser />}</div>

            <div className="message-content">
              <div className="message-text">
                {String(message.content)
                  .split("\n")
                  .map((line, i) => (
                    <div key={i} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") }} />
                  ))}
              </div>
              <div className="message-time">{new Date(message.timestamp).toLocaleTimeString()}</div>
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
                <span></span><span></span><span></span>
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
          <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFileUpload} style={{ display: "none" }} />
          <button className="upload-btn" onClick={() => fileInputRef.current?.click()} disabled={uploadingFile || isLoading}>
            <FaUpload /> {uploadingFile ? "Uploading..." : "Choose File"}
          </button>
          <span className="upload-hint">Supports CSV/Excel with date,type,category,amount</span>
        </div>
      </div>

      <div className="quick-actions">
        <div className="quick-actions-title">Quick Actions:</div>
        <div className="quick-actions-buttons">
          {quickActions.map((action, idx) => (
            <button key={idx} className="quick-action-btn" onClick={() => sendMessage(action.query)} disabled={isLoading}>
              {action.label}
            </button>
          ))}
        </div>
      </div>

      <form className="chatbot-input" onSubmit={handleSubmit}>
        <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Ask me anything about your finances..." disabled={isLoading} />
        <button type="button" className={`voice-btn ${isRecording ? "recording" : ""}`} onClick={() => (isRecording ? stopVoiceRecording() : startVoiceRecording())} disabled={isLoading}>
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
