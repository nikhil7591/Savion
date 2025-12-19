const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

class AuthClient {
  constructor() {
    this.token = localStorage.getItem("auth_token");
    const userData = localStorage.getItem("user");
    this.user = userData ? JSON.parse(userData) : null;
    
    // Ensure user_id is a string, not an object
    if (this.user && typeof this.user.id !== 'string') {
      console.warn("Invalid user data detected, clearing auth");
      this.logout();
    }
  }

  async signup(email, password, name) {
    try {
      const response = await fetch(`${API_URL}/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password, name }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Signup failed");
      }

      const data = await response.json();
      this.setToken(data.access_token, data.user);
      return { data, error: null };
    } catch (error) {
      return { data: null, error };
    }
  }

  async signin(email, password) {
    try {
      const response = await fetch(`${API_URL}/auth/signin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Signin failed");
      }

      const data = await response.json();
      this.setToken(data.access_token, data.user);
      return { data, error: null };
    } catch (error) {
      return { data: null, error };
    }
  }

  async verify() {
    if (!this.token) {
      return { valid: false, user: null };
    }

    try {
      const response = await fetch(`${API_URL}/auth/verify?token=${this.token}`, {
        headers: {
          "Authorization": `Bearer ${this.token}`,
        },
      });

      if (!response.ok) {
        this.logout();
        return { valid: false, user: null };
      }

      const data = await response.json();
      return { valid: data.valid, user: data.user };
    } catch (error) {
      this.logout();
      return { valid: false, user: null };
    }
  }

  setToken(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem("auth_token", token);
    localStorage.setItem("user", JSON.stringify(user));
    localStorage.setItem("user_id", user.id);  // Store just the ID for convenience
  }

  logout() {
    this.token = null;
    this.user = null;
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user");
    localStorage.removeItem("user_id");
  }

  getToken() {
    return this.token;
  }

  getUser() {
    return this.user;
  }

  isAuthenticated() {
    return !!this.token;
  }

  // Auth state listener
  onAuthStateChange(callback) {
    // Verify token on startup
    this.verify().then((result) => {
      if (result.valid) {
        this.user = result.user;
      } else {
        this.logout();
      }
      callback(null, result.valid ? this.user : null);
    });

    // Check token periodically (every 5 minutes)
    const interval = setInterval(() => {
      this.verify().then((result) => {
        if (!result.valid && this.token) {
          callback(null, null);
        }
      });
    }, 5 * 60 * 1000);

    // Return unsubscribe function
    return {
      unsubscribe: () => clearInterval(interval),
    };
  }
}

export const auth = new AuthClient();
