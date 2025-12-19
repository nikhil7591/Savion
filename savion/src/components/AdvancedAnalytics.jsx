import React, { useState, useEffect } from 'react';
import { FaShieldAlt, FaChartLine, FaExclamationTriangle, FaCheckCircle, FaInfoCircle } from 'react-icons/fa';
import './AdvancedAnalytics.css';

const AdvancedAnalytics = ({ userId, onClose }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('risk');

  useEffect(() => {
    fetchAdvancedAnalytics();
  }, [userId]);

  const fetchAdvancedAnalytics = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/api/advanced_analytics?user_id=${userId}`);
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const data = await response.json();
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to fetch advanced analytics:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'low': return '#28a745';
      case 'medium': return '#ffc107';
      case 'high': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const getRiskIcon = (riskLevel) => {
    switch (riskLevel) {
      case 'low': return <FaCheckCircle className="risk-icon low" />;
      case 'medium': return <FaInfoCircle className="risk-icon medium" />;
      case 'high': return <FaExclamationTriangle className="risk-icon high" />;
      default: return <FaInfoCircle className="risk-icon" />;
    }
  };

  if (loading) {
    return (
      <div className="advanced-analytics-overlay">
        <div className="advanced-analytics-container">
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>Analyzing your financial data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="advanced-analytics-overlay">
        <div className="advanced-analytics-container">
          <div className="error-message">
            <FaExclamationTriangle className="error-icon" />
            <h3>Error Loading Analytics</h3>
            <p>{error}</p>
            <button onClick={fetchAdvancedAnalytics} className="retry-btn">
              Try Again
            </button>
            <button onClick={onClose} className="close-btn">
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="advanced-analytics-overlay">
        <div className="advanced-analytics-container">
          <div className="no-data">
            <FaInfoCircle className="info-icon" />
            <h3>No Data Available</h3>
            <p>Add more transactions to enable advanced analytics</p>
            <button onClick={onClose} className="close-btn">Close</button>
          </div>
        </div>
      </div>
    );
  }

  const { risk_assessment, predictions, weekly_insights } = analytics;

  return (
    <div className="advanced-analytics-overlay">
      <div className="advanced-analytics-container">
        <div className="analytics-header">
          <h2>🔬 Advanced Financial Analytics</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="analytics-tabs">
          <button 
            className={`tab ${activeTab === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveTab('risk')}
          >
            <FaShieldAlt /> Risk Assessment
          </button>
          <button 
            className={`tab ${activeTab === 'predictions' ? 'active' : ''}`}
            onClick={() => setActiveTab('predictions')}
          >
            <FaChartLine /> Predictions
          </button>
          <button 
            className={`tab ${activeTab === 'insights' ? 'active' : ''}`}
            onClick={() => setActiveTab('insights')}
          >
            <FaInfoCircle /> Insights
          </button>
        </div>

        <div className="analytics-content">
          {activeTab === 'risk' && (
            <div className="risk-assessment">
              {risk_assessment.error ? (
                <div className="error-section">
                  <p>{risk_assessment.error}</p>
                </div>
              ) : (
                <>
                  <div className="overall-risk">
                    <h3>Overall Risk Profile</h3>
                    <div className="risk-summary">
                      <div className="risk-score">
                        {getRiskIcon(risk_assessment.risk_level)}
                        <span className="risk-level" style={{ color: getRiskColor(risk_assessment.risk_level) }}>
                          {risk_assessment.risk_level.toUpperCase()} RISK
                        </span>
                        <span className="risk-score-value">
                          {(risk_assessment.overall_risk_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="risk-breakdown">
                    <div className="risk-category">
                      <h4>💳 Credit Risk</h4>
                      <div className="risk-details">
                        <p><strong>DTI Ratio:</strong> {(risk_assessment.credit_risk.dti_ratio * 100).toFixed(1)}%</p>
                        <p><strong>Credit Score:</strong> {risk_assessment.credit_risk.estimated_credit_score}</p>
                        <p><strong>Payment Consistency:</strong> {(risk_assessment.credit_risk.payment_consistency * 100).toFixed(1)}%</p>
                        <span className={`risk-badge ${risk_assessment.credit_risk.risk_level}`}>
                          {risk_assessment.credit_risk.risk_level.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <div className="risk-category">
                      <h4>💰 Liquidity Risk</h4>
                      <div className="risk-details">
                        <p><strong>Emergency Fund:</strong> {risk_assessment.liquidity_risk.emergency_fund_months.toFixed(1)} months</p>
                        <p><strong>Income Stability:</strong> {(risk_assessment.liquidity_risk.income_stability * 100).toFixed(1)}%</p>
                        <p><strong>Liquidity Ratio:</strong> {risk_assessment.liquidity_risk.liquidity_ratio.toFixed(2)}</p>
                        <span className={`risk-badge ${risk_assessment.liquidity_risk.risk_level}`}>
                          {risk_assessment.liquidity_risk.risk_level.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <div className="risk-category">
                      <h4>📊 Market Risk</h4>
                      <div className="risk-details">
                        <p><strong>Spending Volatility:</strong> {(risk_assessment.market_risk.spending_volatility * 100).toFixed(1)}%</p>
                        <p><strong>Diversification:</strong> {(risk_assessment.market_risk.diversification_score * 100).toFixed(1)}%</p>
                        <p><strong>Market Exposure:</strong> {risk_assessment.market_risk.market_exposure}</p>
                        <span className={`risk-badge ${risk_assessment.market_risk.risk_level}`}>
                          {risk_assessment.market_risk.risk_level.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <div className="risk-category">
                      <h4>🎯 Operational Risk</h4>
                      <div className="risk-details">
                        <p><strong>Financial Discipline:</strong> {(risk_assessment.operational_risk.financial_discipline * 100).toFixed(1)}%</p>
                        <p><strong>Spending Consistency:</strong> {(risk_assessment.operational_risk.spending_consistency * 100).toFixed(1)}%</p>
                        <p><strong>Goal Achievement:</strong> {(risk_assessment.operational_risk.goal_achievement_rate * 100).toFixed(1)}%</p>
                        <span className={`risk-badge ${risk_assessment.operational_risk.risk_level}`}>
                          {risk_assessment.operational_risk.risk_level.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="risk-recommendations">
                    <h4>🛡️ Risk Mitigation Recommendations</h4>
                    <ul>
                      {risk_assessment.recommendations.map((rec, index) => (
                        <li key={index}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'predictions' && (
            <div className="predictions">
              {predictions.error ? (
                <div className="error-section">
                  <p>{predictions.error}</p>
                </div>
              ) : (
                <>
                  <div className="life-events">
                    <h3>🔮 Life Event Predictions</h3>
                    <div className="event-predictions">
                      {Object.entries(predictions.life_events).map(([event, data]) => (
                        <div key={event} className="event-prediction">
                          <h4>{event.charAt(0).toUpperCase() + event.slice(1)}</h4>
                          <div className="prediction-details">
                            <p><strong>Probability:</strong> {(data.probability * 100).toFixed(1)}%</p>
                            <p><strong>Timeline:</strong> {data.timeline}</p>
                            <p><strong>Financial Impact:</strong> ₹{data.financial_impact.toLocaleString()}</p>
                            <p><strong>Preparation:</strong> {data.preparation_needed}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="financial-trajectory">
                    <h3>📈 Financial Trajectory</h3>
                    <div className="trajectory-summary">
                      <div className="trend-item">
                        <h4>Income Trend</h4>
                        <span className={`trend ${predictions.financial_trajectory.income_trend > 0 ? 'positive' : 'negative'}`}>
                          {(predictions.financial_trajectory.income_trend * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="trend-item">
                        <h4>Expense Trend</h4>
                        <span className={`trend ${predictions.financial_trajectory.expense_trend > 0 ? 'negative' : 'positive'}`}>
                          {(predictions.financial_trajectory.expense_trend * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    <div className="annual-projection">
                      <h4>Annual Projection</h4>
                      <div className="projection-details">
                        <p><strong>Total Income:</strong> ₹{predictions.financial_trajectory.annual_projection.total_income.toLocaleString()}</p>
                        <p><strong>Total Expenses:</strong> ₹{predictions.financial_trajectory.annual_projection.total_expenses.toLocaleString()}</p>
                        <p><strong>Total Savings:</strong> ₹{predictions.financial_trajectory.annual_projection.total_savings.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>

                  <div className="scenario-analysis">
                    <h3>🎭 Scenario Analysis</h3>
                    <div className="scenarios">
                      {Object.entries(predictions.scenario_analysis).map(([scenario, data]) => (
                        <div key={scenario} className="scenario">
                          <h4>{scenario.charAt(0).toUpperCase() + scenario.slice(1)}</h4>
                          <p className="scenario-description">{data.description}</p>
                          <div className="scenario-details">
                            <p><strong>Monthly Income:</strong> ₹{data.monthly_income.toLocaleString()}</p>
                            <p><strong>Monthly Expenses:</strong> ₹{data.monthly_expenses.toLocaleString()}</p>
                            <p><strong>Monthly Savings:</strong> ₹{data.monthly_savings.toLocaleString()}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="prediction-recommendations">
                    <h4>💡 Prediction-Based Recommendations</h4>
                    <ul>
                      {predictions.recommendations.map((rec, index) => (
                        <li key={index}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'insights' && (
            <div className="insights">
              <h3>📊 Weekly Insights</h3>
              {weekly_insights.message ? (
                <div className="no-insights">
                  <p>{weekly_insights.message}</p>
                </div>
              ) : (
                <>
                  <div className="insights-summary">
                    <div className="insight-item">
                      <h4>Total Spending This Week</h4>
                      <p className="spending-amount">₹{weekly_insights.total_spending?.toLocaleString() || '0'}</p>
                    </div>
                  </div>

                  {weekly_insights.insights && weekly_insights.insights.length > 0 && (
                    <div className="key-insights">
                      <h4>Key Insights</h4>
                      <ul>
                        {weekly_insights.insights.map((insight, index) => (
                          <li key={index}>{insight}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {weekly_insights.recommendations && weekly_insights.recommendations.length > 0 && (
                    <div className="insight-recommendations">
                      <h4>Recommendations</h4>
                      <ul>
                        {weekly_insights.recommendations.map((rec, index) => (
                          <li key={index}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdvancedAnalytics;
