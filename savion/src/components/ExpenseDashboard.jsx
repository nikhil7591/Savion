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
  Filler,
} from "chart.js";
import { useNavigate } from "react-router-dom";
import Chatbot from "./Chatbot";
import AdvancedAnalytics from "./AdvancedAnalytics";
import {
  FaRobot,
  FaBell,
  FaChartLine,
  FaShieldAlt,
  FaDownload,
  FaUpload,
  FaUserCircle,
  FaMoon,
  FaSun,
} from "react-icons/fa";
import "./ExpenseDashboard.css";

ChartJS.register(
  ArcElement,
  BarElement,
  LineElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  PointElement,
  Filler
);

/* -------------------------------------------------------------
   Enhanced Voice Input
--------------------------------------------------------------*/
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
    return (
      types.find((t) => {
        try {
          return MediaRecorder.isTypeSupported(t);
        } catch {
          return false;
        }
      }) || "audio/webm"
    );
  };

  const startRecording = async () => {
    try {
      setError("");
      setLastTranscription("");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });

      const mimeType = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, { mimeType });

      let recordedChunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          recordedChunks.push(e.data);
        }
      };

      recorder.onstart = () => setRecording(true);

      recorder.onstop = async () => {
        setRecording(false);
        try {
          if (!recordedChunks.length) throw new Error("No audio recorded.");

          const blob = new Blob(recordedChunks, { type: mimeType });
          const fd = new FormData();
          fd.append("file", blob, "voice.webm");

          // UPDATED FOR PORT 8000
          const res = await fetch("http://localhost:8000/api/transcribe", {
            method: "POST",
            body: fd,
          });

          if (!res.ok) throw new Error(await res.text());

          const data = await res.json();
          if (!data.text) throw new Error("Speech not detected.");

          setLastTranscription(data.text);
          onResult?.(data.text);
          onFieldsExtracted?.(data.fields);
        } catch (err) {
          console.error("Voice process error:", err);
          setError(err.message);
        } finally {
          setProcessing(false);
        }
      };

      setMediaRecorder(recorder);
      setChunks([]);
      recorder.start();
    } catch (err) {
      console.error("Mic error:", err);
      setError("Microphone access denied.");
    }
  };

  const stopRecording = () => {
    if (!mediaRecorder) return;
    setProcessing(true);
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
  };

  return (
    <div className="voice-card">
      <h4 className="card-title">Voice Input</h4>
      <button
        className={`btn btn-primary ${recording ? "recording" : ""}`}
        disabled={processing}
        onClick={recording ? stopRecording : startRecording}
      >
        {processing ? "Processing..." : recording ? "Stop" : "Voice"}
      </button>
      {error && <p className="msg error">❌ {error}</p>}
      {lastTranscription && <p className="msg success">🎤 {lastTranscription}</p>}
    </div>
  );
}

/* -------------------------------------------------------------
   MAIN DASHBOARD COMPONENT
--------------------------------------------------------------*/
export default function ExpenseDashboard({ user, logout, theme, toggleTheme }) {
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
  const [alerts, setAlerts] = useState([]);
  const [insights, setInsights] = useState(null);
  const [showChatbot, setShowChatbot] = useState(false);
  const [showAdvancedAnalytics, setShowAdvancedAnalytics] = useState(false);

  /* ---------------------------- Fetch Alerts ---------------------------- */
  const fetchAlerts = async () => {
    try {
      const r = await fetch(
        `http://localhost:8000/api/check_alerts?user_id=${user.id}`
      );
      if (r.ok) {
        const data = await r.json();
        setAlerts(data.alerts || []);
      }
    } catch (e) {
      console.error("Alerts error:", e);
    }
  };

  /* ---------------------------- Fetch Insights ---------------------------- */
  const fetchInsights = async () => {
    try {
      const r = await fetch(
        `http://localhost:8000/api/weekly_insights?user_id=${user.id}`
      );
      if (r.ok) {
        const data = await r.json();
        setInsights(data);
      }
    } catch (e) {
      console.error("Insights error:", e);
    }
  };

  /* ---------------------------- Refresh Data ---------------------------- */
  const refreshData = React.useCallback(async () => {
    try {
      setLoading(true);

      const tx = await listTx(user.id);
      setTransactions(tx);

      const s = await getSummary(
        user.id,
        filterDates.from || undefined,
        filterDates.to || undefined
      );
      setSummary(s);

      const fc = await getForecast(user.id);
      setForecast(fc.forecast || []);

      await fetchAlerts();
      await fetchInsights();
    } catch (e) {
      console.error("Refresh error:", e);
    } finally {
      setLoading(false);
    }
  }, [user.id, filterDates]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  /* ---------------------------- Submit Transaction ---------------------------- */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.category || !form.amount) return alert("Fill all fields");

    try {
      const tx = {
        ...form,
        user_id: user.id,
        amount: parseFloat(form.amount),
      };

      if (editingId) {
        await updateTx(editingId, tx);
      } else {
        await createTx(tx);
      }

      setEditingId(null);
      setForm({
        type: "expense",
        category: "",
        amount: "",
        date: new Date().toISOString().substr(0, 10),
      });

      refreshData();
    } catch (e) {
      console.error("Submit error:", e);
      alert("Failed to save transaction.");
    }
  };

  /* ---------------------------- Delete ---------------------------- */
  const handleDelete = async (id) => {
    if (!confirm("Delete this transaction?")) return;

    try {
      await deleteTx(id);
      refreshData();
    } catch (e) {
      console.error("Delete error:", e);
      alert("Failed to delete transaction.");
    }
  };

  /* ---------------------------- Export CSV ---------------------------- */
  const exportCSVClick = async () => {
    try {
      const data = await exportCSV(user.id);
      const blob = new Blob([data.csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "expenses.csv";
      a.click();

      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("CSV export error:", e);
      alert("Failed to export.");
    }
  };

  /* ---------------------------- Import CSV ---------------------------- */
  const importCSVClick = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      setLoading(true);
      await uploadCSV(user.id, file);
      refreshData();
      alert("CSV imported successfully.");
    } catch (e) {
      console.error("CSV import error:", e);
      alert("Import failed.");
    } finally {
      setLoading(false);
    }
  };

  /* ---------------------------- Template Download ---------------------------- */
  const downloadTemplateClick = async () => {
    try {
      const data = await downloadTemplate();
      const blob = new Blob([data.csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "expense_template.csv";
      a.click();

      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Template download error:", e);
    }
  };

  /* ---------------------------- Charts ---------------------------- */
  const categories = [...new Set(transactions.map((t) => t.category))];
  const catTotals = categories.map((cat) =>
    transactions
      .filter((t) => t.type === "expense" && t.category === cat)
      .reduce((sum, t) => sum + t.amount, 0)
  );

  // Theme-aware text color for charts
  const chartTextColor = theme === "dark" ? "#ffffff" : "#0f172a";

  const pieData = {
    labels: ["Income", "Expense"],
    datasets: [
      {
        data: [summary.total_income, summary.total_expense],
        backgroundColor: ["#2b6cff", "#60a5fa"],
      },
    ],
  };

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: {
          color: chartTextColor,
          font: { size: 12, weight: 600 },
        },
      },
    },
  };

  const barData = {
    labels: categories,
    datasets: [
      {
        label: "Expenses",
        data: catTotals,
        backgroundColor: "#2b6cff",
      },
    ],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: {
          color: chartTextColor,
          font: { size: 12, weight: 600 },
        },
      },
    },
    scales: {
      x: {
        ticks: { color: chartTextColor },
        grid: { color: theme === "dark" ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)" },
      },
      y: {
        ticks: { color: chartTextColor },
        grid: { color: theme === "dark" ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)" },
      },
    },
  };

  const lineData = {
    labels: ["Next 1", "Next 2", "Next 3", "Next 4"],
    datasets: [
      {
        label: "Predicted Spending",
        data: forecast,
        fill: true,
        backgroundColor: "rgba(43,108,255,0.1)",
        borderColor: "#2b6cff",
      },
    ],
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: {
          color: chartTextColor,
          font: { size: 12, weight: 600 },
        },
      },
    },
    scales: {
      x: {
        ticks: { color: chartTextColor },
        grid: { color: theme === "dark" ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)" },
      },
      y: {
        ticks: { color: chartTextColor },
        grid: { color: theme === "dark" ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)" },
      },
    },
  };

  /* -------------------------------------------------------------
     Render Component
  --------------------------------------------------------------*/
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
            <div className="icon-btn theme-toggle" onClick={toggleTheme} title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}>
              {theme === "light" ? <FaMoon /> : <FaSun />}
            </div>
            <div className="icon-btn">
              <FaBell />
              {alerts.length > 0 && <span className="dot">{alerts.length}</span>}
            </div>
            <div className="icon-btn">
              <FaChartLine />
            </div>
          </div>

          <div className="profile">
            <div className="avatar">
              <FaUserCircle />
            </div>
            <div className="profile-text">
              <div className="name">{user?.name || user?.email}</div>
              <button className="link small" onClick={() => navigate("/edit-profile")}>
                Edit profile
              </button>
            </div>

            <button className="btn btn-ghost logout" onClick={logout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <section className="alerts-panel">
          <div className="alerts-inner">
            <h4>Financial Alerts</h4>
            <div className="alerts-grid">
              {alerts.map((alert, i) => (
                <div key={i} className={`alert-pill alert-${alert.severity || "medium"}`}>
                  <div>{alert.message}</div>
                  {alert.suggestion && <small className="muted">{alert.suggestion}</small>}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <main className="container">
        {/* Form + Voice Input + CSV Tools */}
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
                <input
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                />
              </div>

              <div className="row actions">
                <button className="btn btn-primary" disabled={loading}>
                  {editingId ? "Update" : "Add Transaction"}
                </button>
              </div>
            </form>
          </div>

          <EnhancedVoiceInput
            onResult={(t) => console.log("Voice:", t)}
            onFieldsExtracted={async (fields) => {
              if (!fields) return;
              console.log("Extracted:", fields);
              
              try {
                const tx = {
                  type: fields.type || "expense",
                  category: fields.category || "",
                  amount: parseFloat(fields.amount) || 0,
                  date: fields.date || new Date().toISOString().substr(0, 10),
                  user_id: user.id,
                };
                
                if (!tx.category || !tx.amount) {
                  alert("Could not extract category or amount from voice input.");
                  return;
                }
                
                await createTx(tx);
                console.log("Transaction created from voice:", tx);
                refreshData();
              } catch (err) {
                console.error("Failed to create transaction from voice:", err);
                alert("Failed to save voice transaction.");
              }
            }}
          />

          <div className="card actions-card">
            <h4 className="card-title">Backup & Import</h4>

            <button className="btn btn-secondary" onClick={exportCSVClick}>
              <FaDownload /> Export CSV
            </button>

            <label className="btn btn-secondary import-label">
              <FaUpload /> Import CSV
              <input type="file" hidden accept=".csv" onChange={importCSVClick} />
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
        </section>

        {/* Summary */}
        <section className="summary-grid">
          <div className="card summary-card">
            <h4 className="card-title">Summary</h4>
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

          {/* Filter */}
          <div className="card filter-card">
            <h4 className="card-title">Filter</h4>
            <div className="filter-body">
              <div className="row">
                <label>From</label>
                <input
                  type="date"
                  value={filterDates.from}
                  onChange={(e) => setFilterDates({ ...filterDates, from: e.target.value })}
                />
              </div>
              <div className="row">
                <label>To</label>
                <input
                  type="date"
                  value={filterDates.to}
                  onChange={(e) => setFilterDates({ ...filterDates, to: e.target.value })}
                />
              </div>
              <div className="row actions">
                <button className="btn btn-primary" onClick={refreshData}>
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
              {summary.total_income > 0 || summary.total_expense > 0 ? (
                <Pie data={pieData} options={pieOptions} />
              ) : (
                <div className="no-data">No data</div>
              )}
            </div>
          </div>

          <div className="card chart-card">
            <h4 className="card-title">Expenses by Category</h4>
            <div className="chart-area">
              {categories.length > 0 ? (
                <Bar data={barData} options={barOptions} />
              ) : (
                <div className="no-data">No category data</div>
              )}
            </div>
          </div>

          <div className="card chart-card">
            <h4 className="card-title">Spending Forecast</h4>
            <div className="chart-area">
              {forecast.length > 0 ? (
                <Line data={lineData} options={lineOptions} />
              ) : (
                <div className="no-data">Insufficient data</div>
              )}
            </div>
          </div>
        </section>

        {/* Transactions Table */}
        <section className="table-card card">
          <h4 className="card-title">Transactions</h4>

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
              {transactions.map((tx, i) => (
                <tr key={tx.id || tx._id || i}>
                  <td>{new Date(tx.date).toLocaleDateString()}</td>
                  <td>
                    <span className={`type-badge ${tx.type}`}>{tx.type}</span>
                  </td>
                  <td>{tx.category}</td>
                  <td>₹{tx.amount.toLocaleString()}</td>
                  <td>
                    <button
                      className="edit-btn"
                      onClick={() => {
                        setEditingId(tx.id || tx._id);
                        setForm({
                          type: tx.type,
                          category: tx.category,
                          amount: tx.amount,
                          date: tx.date,
                        });
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }}
                    >
                      Edit
                    </button>

                    <button
                      className="delete-btn"
                      onClick={() => handleDelete(tx.id || tx._id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}

              {transactions.length === 0 && (
                <tr>
                  <td colSpan="5" className="no-data-row">
                    No transactions yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </main>

      {showChatbot && (
        <Chatbot userId={user.id} onClose={() => setShowChatbot(false)} />
      )}

      {showAdvancedAnalytics && (
        <AdvancedAnalytics
          userId={user.id}
          onClose={() => setShowAdvancedAnalytics(false)}
        />
      )}
    </div>
  );
}
