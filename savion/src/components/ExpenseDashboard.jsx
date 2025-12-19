
import React, { useState, useEffect } from "react";
import {
  listTx,
  createTx,
  updateTx,
  deleteTx,
  getSummary,
  getForecast,
  uploadCSV,
  exportCSV,
  downloadTemplate,
} from "../api";
import { Pie, Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  LineElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  PointElement,
} from "chart.js";
import { useNavigate } from "react-router-dom";
import Chatbot from "./Chatbot";
import AdvancedAnalytics from "./AdvancedAnalytics";
import { FaRobot, FaBell, FaChartLine, FaShieldAlt, FaDownload, FaUpload, FaUserCircle } from "react-icons/fa";
import "./ExpenseDashboard.css";

ChartJS.register(
  ArcElement,
  BarElement,
  LineElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  PointElement
);

// Enhanced Voice Input Component (kept logic — only layout/styling changed)
function EnhancedVoiceInput({ onResult, onFieldsExtracted }) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [lastTranscription, setLastTranscription] = useState("");
  const [error, setError] = useState("");

  const getSupportedMimeType = () => {
    const types = [
      "audio/wav",
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
      "audio/mp4",
      "audio/mpeg",
    ];
    return types.find((type) => {
      try {
        return MediaRecorder.isTypeSupported(type);
      } catch {
        return false;
      }
    }) || "audio/webm";
  };

  const startRecording = async () => {
    try {
      setError("");
      setLastTranscription("");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        },
      });

      const mimeType = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, {
        mimeType,
        bitsPerSecond: 128000,
      });

      setMediaRecorder(recorder);
      setChunks([]);

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          setChunks((prev) => [...prev, e.data]);
        }
      };

      recorder.onstart = () => setRecording(true);
      recorder.onstop = () => setRecording(false);

      recorder.start(1000);
    } catch (err) {
      console.error("Mic access denied:", err);
      setError("Microphone access denied. Please allow microphone access and try again.");
    }
  };

  const stopRecording = () => {
    if (!mediaRecorder || mediaRecorder.state !== "recording") return;
    setProcessing(true);
    setError("");

    mediaRecorder.stop();
    if (mediaRecorder.stream) {
      mediaRecorder.stream.getTracks().forEach((t) => t.stop());
    }

    mediaRecorder.onstop = async () => {
      try {
        if (chunks.length === 0) throw new Error("No audio data recorded");

        const mimeType = mediaRecorder.mimeType || "audio/webm";
        const blob = new Blob(chunks, { type: mimeType });

        if (blob.size < 1000) throw new Error("Recording too short or empty");

        const formData = new FormData();
        const fileExtension = mimeType.includes("wav") ? "wav" : mimeType.includes("ogg") ? "ogg" : "webm";
        formData.append("file", blob, `voice.${fileExtension}`);

        const res = await fetch("http://localhost:8000/api/transcribe", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`Server error ${res.status}: ${errorText}`);
        }

        const data = await res.json();
        if (!data.text || data.text.trim() === "") {
          throw new Error("No speech detected in recording");
        }

        setLastTranscription(data.text);
        if (onResult) onResult(data.text);
        if (onFieldsExtracted && data.fields) onFieldsExtracted(data.fields);
      } catch (err) {
        console.error("Processing failed:", err);
        setError(`Failed to process recording: ${err.message}`);
      } finally {
        setProcessing(false);
        setChunks([]);
      }
    };
  };

  const getButtonText = () => {
    if (processing) return "Processing...";
    if (recording) return "Stop";
    return "Voice";
  };

  return (
    <div className="voice-card">
      <div className="voice-top">
        <h4 className="card-title">Voice Input</h4>
        <small className="muted">Add transactions quickly by speaking</small>
      </div>

      <div className="voice-body">
        <button
          className={`btn btn-primary voice-toggle ${recording ? "recording" : ""} ${processing ? "loading" : ""}`}
          onClick={recording ? stopRecording : startRecording}
          disabled={processing}
          title="Click to start/stop voice recording"
        >
          {getButtonText()}
        </button>

        <div className="voice-status">
          {error && <div className="msg error">❌ {error}</div>}
          {lastTranscription && <div className="msg success">🎯 "{lastTranscription}"</div>}
          {recording && <div className="recording-indicator small">Recording…</div>}
        </div>
      </div>
    </div>
  );
}

export default function ExpenseDashboard({ user, logout }) {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    type: "expense",
    category: "",
    amount: "",
    date: new Date().toISOString().substr(0, 10),
  });

  const [filterDates, setFilterDates] = useState({ from: "", to: "" });
  const [summary, setSummary] = useState({
    total_income: 0,
    total_expense: 0,
    balance: 0,
  });
  const [forecast, setForecast] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showChatbot, setShowChatbot] = useState(false);
  const [showAdvancedAnalytics, setShowAdvancedAnalytics] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [insights, setInsights] = useState(null);

  const refreshData = React.useCallback(async () => {
    if (!user?.id) return;
    try {
      setLoading(true);
      const data = await listTx(user.id);
      setTransactions(data || []);

      const s = await getSummary(user.id, filterDates.from || undefined, filterDates.to || undefined);
      setSummary(s || { total_income: 0, total_expense: 0, balance: 0 });

      const fc = await getForecast(user.id);
      setForecast((fc && fc.forecast) || []);

      await fetchAlerts();
      await fetchInsights();
    } catch (error) {
      console.error("Error refreshing data:", error);
    } finally {
      setLoading(false);
    }
  }, [user?.id, filterDates.from, filterDates.to]);

  const fetchAlerts = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/check_alerts?user_id=${user.id}`);
      if (response.ok) {
        const data = await response.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  };

  const fetchInsights = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/weekly_insights?user_id=${user.id}`);
      if (response.ok) {
        const data = await response.json();
        setInsights(data);
      }
    } catch (error) {
      console.error("Error fetching insights:", error);
    }
  };

  useEffect(() => {
    if (user?.id) {
      refreshData();
    }
  }, [user?.id, refreshData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.category || !form.amount || !form.date) return alert("Fill all fields");

    try {
      const payload = {
        ...form,
        user_id: user.id,
        amount: parseFloat(form.amount),
      };

      if (editingId !== null) {
        await updateTx(editingId, payload);
      } else {
        await createTx(payload);
      }

      setEditingId(null);
      setForm({
        type: "expense",
        category: "",
        amount: "",
        date: new Date().toISOString().substr(0, 10),
      });

      refreshData();
    } catch (error) {
      console.error("Error submitting transaction:", error);
      alert("Failed to save transaction. Please try again.");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Are you sure you want to delete this transaction?")) return;

    try {
      await deleteTx(id);
      refreshData();
    } catch (error) {
      console.error("Error deleting transaction:", error);
      alert("Failed to delete transaction. Please try again.");
    }
  };

  const exportCSVClick = async () => {
    try {
      const { csv } = await exportCSV(user.id);
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "expenses.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Export failed:", error);
      alert("Failed to export CSV. Please try again.");
    }
  };

  const importCSVClick = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("Please select a CSV file.");
      return;
    }

    try {
      setLoading(true);
      const result = await uploadCSV(user.id, file);

      if (result.success) {
        alert(
          `✅ Import completed!\n• Inserted: ${result.inserted} transactions\n• Rows processed: ${result.total_rows}\n• Errors: ${result.error_count}`
        );
        refreshData();
      } else {
        alert("Import failed. Please check your CSV format.");
      }
    } catch (err) {
      console.error("CSV import error:", err);
      alert(`Import failed: ${err.message || "Unknown error"}.`);
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  const downloadTemplateClick = async () => {
    try {
      const data = await downloadTemplate();
      const blob = new Blob([data.csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "expense_template.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download template:", err);
      alert("Failed to download template. Please try again.");
    }
  };

  const handleVoiceResult = (text) => {
    console.log("Voice transcribed:", text);
  };

  const handleVoiceFields = async (fields) => {
    if (!fields.amount || fields.amount <= 0) {
      alert("Could not detect a valid amount from voice input. Please try again or enter manually.");
      return;
    }

    const transaction = {
      user_id: user.id,
      type: fields.type || "expense",
      category: fields.category || "Other",
      amount: fields.amount,
      date: fields.date || new Date().toISOString().split("T")[0],
    };

    try {
      await createTx(transaction);
      alert(`✅ Added ${transaction.type}: ₹${transaction.amount} for ${transaction.category}`);
      refreshData();
    } catch (err) {
      console.error("Failed to create transaction from voice:", err);
      alert("Failed to add transaction. Please try again.");
    }
  };

  const filteredTransactions = transactions.filter((tx) => {
    const txDate = new Date(tx.date);
    const from = filterDates.from ? new Date(filterDates.from) : null;
    const to = filterDates.to ? new Date(filterDates.to) : null;
    if (from && txDate < from) return false;
    if (to && txDate > to) return false;
    return true;
  });

  const pieData = {
    labels: ["Income", "Expense"],
    datasets: [
      {
        data: [summary.total_income, summary.total_expense],
        backgroundColor: ["#2b6cff", "#60a5fa"],
        hoverOffset: 6,
      },
    ],
  };

  const categories = [...new Set(transactions.map((t) => t.category))];
  const catTotals = categories.map((cat) =>
    transactions.filter((t) => t.type === "expense" && t.category === cat).reduce((sum, t) => sum + t.amount, 0)
  );
  const barData = {
    labels: categories,
    datasets: [
      {
        label: "Expenses",
        data: catTotals,
        backgroundColor: "#2b6cff",
        borderRadius: 6,
      },
    ],
  };

  const lineData = {
    labels: ["Next 1", "Next 2", "Next 3", "Next 4"],
    datasets: [
      {
        label: "Predicted Spending",
        data: forecast,
        fill: true,
        backgroundColor: "rgba(43,108,255,0.08)",
        borderColor: "#2b6cff",
        tension: 0.35,
        pointRadius: 4,
      },
    ],
  };

  return (
    <div className="expense-dashboard premium">
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
        </div>
      )}

      <header className="topbar">
        <div className="brand">
          <div className="logo-mark">S</div>
          <div>
            <h1>Savion</h1>
            <small className="muted">Smart Personal Finance</small>
          </div>
        </div>

        <div className="top-actions">
          <div className="icons">
            <div className="icon-btn">
              <FaBell />
              {alerts.length > 0 && <span className="dot">{alerts.length}</span>}
            </div>
            <div className="icon-btn insights">
              <FaChartLine />
            </div>
          </div>

          <div className="profile">
            <div className="avatar">
              <FaUserCircle />
            </div>
            <div className="profile-text">
              <div className="name">{user?.name || user?.email}</div>
              <button className="link small" onClick={() => navigate("/edit-profile")}>Edit profile</button>
            </div>

            <button className="btn btn-ghost logout" onClick={logout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Alerts */}
      {alerts.length > 0 && (
        <section className="alerts-panel">
          <div className="alerts-inner">
            <h4>Financial Alerts</h4>
            <div className="alerts-grid">
              {alerts.map((alert, index) => (
                <div key={index} className={`alert-pill alert-${alert.severity || "medium"}`}>
                  <div className="msg-line">{alert.message}</div>
                  {alert.suggestion && <div className="muted small">{alert.suggestion}</div>}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <main className="container">
        <section className="controls-grid">
          <div className="card form-card">
            <h4 className="card-title">Add Transaction</h4>
            <form className="expense-form" onSubmit={handleSubmit}>
              <div className="row">
                <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  <option value="expense">Expense</option>
                  <option value="income">Income</option>
                </select>

                <input
                  type="text"
                  placeholder="Category"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                />
              </div>

              <div className="row">
                <input
                  type="number"
                  placeholder="Amount"
                  value={form.amount}
                  onChange={(e) => setForm({ ...form, amount: e.target.value })}
                />
                <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
              </div>

              <div className="row actions">
                <button className="btn btn-primary" type="submit" disabled={loading}>
                  {editingId ? "Update" : "Add Transaction"}
                </button>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() =>
                    setForm({ type: "expense", category: "", amount: "", date: new Date().toISOString().substr(0, 10) })
                  }
                >
                  Reset
                </button>
              </div>
            </form>
          </div>

          <EnhancedVoiceInput onResult={handleVoiceResult} onFieldsExtracted={handleVoiceFields} />

          <div className="card actions-card">
            <div className="card-top">
              <h4 className="card-title">Backup & Import</h4>
              <small className="muted">CSV operations</small>
            </div>

            <div className="actions-list">
              <button className="btn btn-secondary" onClick={exportCSVClick} disabled={loading}>
                <FaDownload /> Export CSV
              </button>

              <label className="import-label btn btn-secondary">
                <FaUpload /> Import CSV
                <input type="file" hidden accept=".csv" onChange={importCSVClick} disabled={loading} />
              </label>

              <button className="btn btn-ghost small" onClick={downloadTemplateClick}>
                Download Template
              </button>

              <button className="btn btn-primary ghost" onClick={() => setShowChatbot(true)}>
                <FaRobot /> AI Assistant
              </button>

              <button className="btn btn-outline" onClick={() => setShowAdvancedAnalytics(true)}>
                <FaShieldAlt /> Advanced Analytics
              </button>
            </div>
          </div>
        </section>

        {/* Filters & Summary */}
        <section className="summary-grid">
          <div className="card summary-card">
            <div className="summary-top">
              <h4 className="card-title">Summary</h4>
              <small className="muted">Overview</small>
            </div>
            <div className="summary-body">
              <div className="stat">
                <div className="label">Income</div>
                <div className="value">₹{summary.total_income.toLocaleString()}</div>
              </div>
              <div className="stat">
                <div className="label">Expenses</div>
                <div className="value">₹{summary.total_expense.toLocaleString()}</div>
              </div>
              <div className="stat">
                <div className="label">Balance</div>
                <div className="value">₹{summary.balance.toLocaleString()}</div>
              </div>
            </div>
          </div>

          <div className="card filter-card">
            <h4 className="card-title">Filter</h4>
            <div className="filter-body">
              <div className="row">
                <label>From</label>
                <input type="date" value={filterDates.from} onChange={(e) => setFilterDates({ ...filterDates, from: e.target.value })} />
              </div>
              <div className="row">
                <label>To</label>
                <input type="date" value={filterDates.to} onChange={(e) => setFilterDates({ ...filterDates, to: e.target.value })} />
              </div>
              <div className="row actions">
                <button className="btn btn-primary" onClick={refreshData} disabled={loading}>
                  Apply
                </button>
                <button className="btn btn-outline" onClick={() => setFilterDates({ from: "", to: "" })}>
                  Clear
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Charts */}
        <section className="charts-grid">
          <div className="card chart-card">
            <h4 className="card-title">Income vs Expense</h4>
            <div className="chart-area">
              {summary.total_income > 0 || summary.total_expense > 0 ? <Pie data={pieData} /> : <div className="no-data">No data to display</div>}
            </div>
          </div>

          <div className="card chart-card">
            <h4 className="card-title">Expenses by Category</h4>
            <div className="chart-area">
              {categories.length > 0 ? <Bar data={barData} /> : <div className="no-data">No expense data to display</div>}
            </div>
          </div>

          <div className="card chart-card">
            <h4 className="card-title">Spending Forecast</h4>
            <div className="chart-area">
              {forecast.length > 0 ? <Line data={lineData} /> : <div className="no-data">Insufficient data for forecast</div>}
            </div>
          </div>
        </section>

        {/* Transactions Table */}
        <section className="table-card card">
          <div className="table-top">
            <h4 className="card-title">Transactions</h4>
            <small className="muted">Recent activity</small>
          </div>
          <div className="expense-list">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.map((tx) => (
                  <tr key={tx.id}>
                    <td>{new Date(tx.date).toLocaleDateString()}</td>
                    <td>
                      <span className={`type-badge ${tx.type}`}>{tx.type}</span>
                    </td>
                    <td>{tx.category}</td>
                    <td>₹{tx.amount.toLocaleString()}</td>
                    <td className="actions-td">
                      <button
                        className="edit-btn"
                        onClick={() => {
                          setEditingId(tx.id);
                          setForm({ type: tx.type, category: tx.category, amount: tx.amount, date: tx.date });
                          window.scrollTo({ top: 0, behavior: "smooth" });
                        }}
                        disabled={loading}
                      >
                        Edit
                      </button>

                      <button className="delete-btn" onClick={() => handleDelete(tx.id)} disabled={loading}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredTransactions.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: "center", padding: "2rem" }}>
                      {loading ? "Loading transactions..." : "No transactions found."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {showChatbot && <Chatbot userId={user.id} onClose={() => setShowChatbot(false)} />}
      {showAdvancedAnalytics && <AdvancedAnalytics userId={user.id} onClose={() => setShowAdvancedAnalytics(false)} />}
    </div>
  );
}
