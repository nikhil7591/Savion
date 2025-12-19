# Savion - Smart Personal Finance Assistant

A comprehensive full-stack personal finance management application powered by AI. Savion helps users track expenses, manage investments, receive personalized financial advice, and make data-driven financial decisions.

## 🌟 Features

- **AI-Powered Financial Assistant**: Chatbot powered by Google Gemini AI for personalized financial advice
- **Expense Tracking**: Monitor and categorize your spending habits
- **Investment Management**: Track investments and receive investment advice
- **Advanced Analytics**: Detailed financial analytics and insights
- **Real-time Alerts**: Get notified about important financial events
- **Voice Input**: Hands-free expense logging with voice commands
- **User Authentication**: Secure sign up and login with Supabase
- **User Profile Management**: Customize your profile and preferences
- **Dashboard**: Comprehensive overview of your financial status

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: Google Gemini AI
- **Authentication**: Supabase
- **Features**: Machine Learning, Web Sockets, Real-time Notifications

### Frontend
- **Framework**: React with Vite
- **Styling**: Tailwind CSS
- **UI Components**: Custom components with CSS modules
- **API Integration**: Axios for HTTP requests
- **Build Tool**: Vite

## 📋 Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn
- MongoDB instance (local or cloud)
- Google Gemini API key
- Supabase account and credentials

## 🚀 Installation

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:
   - **Windows**:
     ```bash
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up environment variables:
   - Create a `.env` file in the backend directory
   - Add your MongoDB URI, Gemini API key, and other credentials

6. Run the setup script (optional):
   ```bash
   python setup_gemini.py
   ```

7. Start the backend server:
   - **Windows (PowerShell)**:
     ```bash
     .\start_server.ps1
     ```
   - **Windows (Batch)**:
     ```bash
     .\start_server.bat
     ```
   - **macOS/Linux**:
     ```bash
     python -m uvicorn app.main:app --reload
     ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd savion
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file with your Supabase credentials:
   ```
   VITE_SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

## 📁 Project Structure

```
Savion/
├── backend/
│   ├── app/
│   │   ├── main.py              # Main FastAPI application
│   │   ├── models.py            # Data models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── db.py                # Database configuration
│   │   ├── gemini_ai.py         # Gemini AI integration
│   │   ├── finance_agent.py     # Finance agent logic
│   │   ├── investment.py        # Investment management
│   │   ├── advanced_analytics.py# Analytics features
│   │   ├── alerts.py            # Alert system
│   │   ├── notifications.py     # Notification system
│   │   ├── ml.py                # Machine learning models
│   │   ├── websocket_handler.py # WebSocket handling
│   │   └── agents.py            # AI agents
│   ├── config.py                # Configuration settings
│   ├── requirements.txt         # Python dependencies
│   ├── setup_gemini.py         # Gemini setup script
│   ├── test_*.py               # Test files
│   └── sample_finance_data.csv # Sample data
│
└── savion/
    ├── src/
    │   ├── components/
    │   │   ├── Chatbot.jsx
    │   │   ├── DashBoard.jsx
    │   │   ├── UserDashboard.jsx
    │   │   ├── AdvancedAnalytics.jsx
    │   │   ├── ExpenseDashboard.jsx
    │   │   ├── SignIn.jsx
    │   │   ├── SignUp.jsx
    │   │   ├── UserProfile.jsx
    │   │   ├── VoiceInput.jsx
    │   │   └── Welcome.jsx
    │   ├── api/
    │   │   ├── auth.js          # Authentication API
    │   │   └── client.js        # API client
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── SupabaseClient.js
    ├── public/
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

## 🔧 Environment Variables

### Backend (.env)
```
# MongoDB
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Server
SERVER_HOST=localhost
SERVER_PORT=8000
```

### Frontend (.env.local)
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_BASE_URL=http://localhost:8000
```

## 📝 Testing

Run backend tests:
```bash
cd backend
python -m pytest test_*.py
```

Or run individual tests:
```bash
python test_gemini.py
python test_mongodb.py
python test_auth.py
python test_investment_advice.py
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, email support@savion.com or open an issue in the repository.

## 🎯 Roadmap

- [ ] Mobile app (iOS/Android)
- [ ] Budget planning tools
- [ ] Tax optimization recommendations
- [ ] Cryptocurrency tracking
- [ ] Collaborative budgeting for couples
- [ ] Integration with banking APIs
- [ ] Advanced ML models for financial predictions

---

**Last Updated**: December 2025
