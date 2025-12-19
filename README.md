# Savion - Smart Personal Finance Assistant

## Project Overview

Savion is an intelligent personal finance assistant designed to help users manage their finances effectively. It offers a suite of features, including expense tracking, financial forecasting, and advanced data analysis. The application leverages AI-powered agents to provide personalized insights and recommendations, making it a powerful tool for financial planning.

This project was recently migrated from Supabase to a self-hosted MongoDB solution for authentication and data persistence, ensuring greater control and security over user data. It also integrates with Google's Gemini API for its advanced AI capabilities.

## Tech Stack

- **Frontend:** React, Vite
- **Backend:** Node.js, Express
- **Database:** MongoDB
- **Authentication:** bcrypt, JSON Web Tokens (JWT)
- **AI:** Google Gemini API

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    ```

2.  **Install dependencies for the frontend:**
    ```bash
    cd savion
    npm install
    ```

3.  **Install dependencies for the backend:**
    ```bash
    # Assuming backend is in the root or a separate directory
    npm install
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the root of the project and add the following:
    ```
    MONGO_URI=your_mongodb_connection_string
    JWT_SECRET=your_jwt_secret
    GEMINI_API_KEY=your_gemini_api_key
    ```

5.  **Run the application:**
    - **Frontend:** `npm run dev`
    - **Backend:** `node server.js` (or your entry file)

## Authentication Flow (MongoDB)

Authentication is handled via a custom implementation using MongoDB, bcrypt, and JWT.

-   **User Registration:** New users are registered through the `/api/auth/register` endpoint. Passwords are encrypted using `bcrypt` before being stored in the database.
-   **User Login:** Users log in via the `/api/auth/login` endpoint. Upon successful authentication, a JWT is generated and returned to the client.
-   **Protected Routes:** Routes requiring authentication are protected by a middleware that verifies the JWT sent in the `Authorization` header.
-   **Session Management:** User sessions are tracked in the database, storing the JWT, device information, and IP address for security purposes.

## Gemini API Usage

The Google Gemini API is used for various AI-powered features, including:

-   **Chatbot:** The chatbot uses the `gemini-pro` model to provide intelligent responses to user queries.
-   **Financial Analysis:** The application leverages Gemini to analyze financial data and provide users with insights and recommendations.

All Gemini API requests are handled through the backend to ensure the API key is kept secure. The relevant endpoints are:

-   `/api/gemini/chat`
-   `/api/gemini/analyze/:userId`
-   `/api/gemini/clear-history/:userId`
-   `/api/gemini/conversation-summary/:userId`
