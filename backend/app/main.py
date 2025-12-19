# app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date, datetime, timedelta
import io, os, tempfile, subprocess, re
import pandas as pd
from pydantic import BaseModel, Field

from contextlib import asynccontextmanager
from asyncio import CancelledError

from . import db
from .models import Transaction, User
from .ml import categorize_descriptions, forecast, detect_anomalies
from .agents import (
    ConversationalAgent, CategorizationAgent, PredictionAgent,
    AnomalyAgent, GoalSettingAgent, NotificationAgent,
    RiskAssessmentAgent, PredictiveAnalyticsAgent
)
from .gemini_ai import get_gemini_assistant
from .websocket_handler import websocket_endpoint, manager
from .advanced_analytics import build_advanced_analytics


from bson import ObjectId
import bcrypt
import jwt
import json

# ====================================================================================
#                         APPLICATION LIFESPAN (CLEAN START / SHUTDOWN)
# ====================================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan to prevent CancelledError on Windows and ensure
    database initialization/cleanup happen reliably.
    """
    try:
        print("🚀 Starting Savion Backend...")
        # initialize DB (synchronous or asynchronous depending on your db module)
        try:
            db.init_db()
            print("✅ DB initialized.")
        except Exception as e:
            print(f"⚠️ DB init error: {e}")
        yield
    except CancelledError:
        print("⚠ Server interrupted. Cleaning up...")
    finally:
        try:
            db.close_db()
            print("🔌 DB connection closed.")
        except Exception as e:
            print(f"⚠️ DB close error: {e}")
        print("✅ Shutdown complete.")


app = FastAPI(
    title="Savion Backend",
    version="0.2.0",
    lifespan=lifespan
)

# ====================================================================================
#                                  CORS CONFIG
# ====================================================================================

allowed = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins="*" if "ALL" in allowed else allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================================================================
#                                HEALTH CHECK
# ====================================================================================

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# ====================================================================================
#                               AUTH SECTION
# ====================================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"

class SignUpRequest(BaseModel):
    email: str
    password: str
    name: str

class SignInRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    user: dict

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(req: SignUpRequest):
    try:
        existing_user = db.get_user_by_email(req.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_pwd = hash_password(req.password)
        user_data = {
            "email": req.email,
            "name": req.name,
            "password_hash": hashed_pwd,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        user_id = db.create_user(user_data)
        token = create_access_token(str(user_id), req.email)
        return AuthResponse(
            access_token=token,
            user={"id": str(user_id), "email": req.email, "name": req.name}
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@app.post("/api/auth/signin", response_model=AuthResponse)
def signin(req: SignInRequest):
    try:
        user = db.get_user_by_email(req.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not verify_password(req.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_access_token(str(user["_id"]), req.email)
        return AuthResponse(
            access_token=token,
            user={"id": str(user["_id"]), "email": user["email"], "name": user.get("name", "")}
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signin failed: {str(e)}")

@app.get("/api/auth/verify")
def verify_auth(token: str = Query(...)):
    try:
        payload = verify_token(token)
        user = db.get_user_by_id(payload["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {
            "valid": True,
            "user": {"id": str(user["_id"]), "email": user["email"], "name": user.get("name", "")}
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token verification failed")

# ====================================================================================
#                            TRANSACTION SCHEMAS & CRUD
# ====================================================================================

class TxIn(BaseModel):
    user_id: str
    type: str  # 'income' or 'expense'
    category: str
    amount: float
    date: date

class TxOut(TxIn):
    id: Optional[str] = Field(alias="_id", default=None)
    created_at: datetime

    class Config:
        populate_by_name = True

@app.get("/api/transactions", response_model=List[TxOut])
def list_transactions(user_id: str = Query(...)):
    transactions = db.get_transactions(user_id)
    for tx in transactions:
        if "_id" in tx:
            tx["_id"] = str(tx["_id"])
    return transactions

@app.post("/api/transactions", response_model=dict)
def create_transaction(tx: TxIn):
    transaction_data = {
        "user_id": tx.user_id,
        "type": tx.type,
        "category": tx.category,
        "amount": tx.amount,
        "date": tx.date if isinstance(tx.date, datetime) else datetime.combine(tx.date, datetime.min.time()),
    }
    result = db.create_transaction(transaction_data)
    result["_id"] = str(result["_id"])
    return result

@app.put("/api/transactions/{tx_id}", response_model=dict)
def update_transaction(tx_id: str, tx: TxIn):
    try:
        update_data = {
            "user_id": tx.user_id,
            "type": tx.type,
            "category": tx.category,
            "amount": tx.amount,
            "date": tx.date if isinstance(tx.date, datetime) else datetime.combine(tx.date, datetime.min.time()),
        }
        result = db.update_transaction(tx_id, update_data)
        if not result:
            raise HTTPException(404, "Transaction not found")
        result["_id"] = str(result["_id"])
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: str):
    try:
        success = db.delete_transaction(tx_id)
        if not success:
            raise HTTPException(404, "Transaction not found")
        return {"deleted": tx_id}
    except Exception as e:
        raise HTTPException(400, str(e))

# ====================================================================================
#                         ENHANCED CSV UPLOAD / EXPORT
# ====================================================================================

@app.post("/api/upload_csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: Optional[str] = Query(None),
):
    """Enhanced CSV upload with better error handling and flexibility"""
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(400, "Please upload a CSV file")
    
    try:
        content = await file.read()
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    io.BytesIO(content), 
                    encoding=encoding,
                    engine='python',
                    sep=None,
                    skipinitialspace=True,
                    na_values=['', 'NA', 'N/A', 'null', 'NULL', 'None'],
                    keep_default_na=True
                )
                print(f"Successfully parsed CSV with {encoding} encoding")
                break
            except Exception as e:
                print(f"Failed to parse with {encoding}: {e}")
                continue
        
        if df is None:
            raise HTTPException(400, "Could not parse CSV file. Please check the file format.")
        
        if df.empty:
            raise HTTPException(400, "CSV file is empty")
        
        print(f"CSV shape: {df.shape}")
        print(f"CSV columns: {list(df.columns)}")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        raw_cols = list(df.columns)
        
        # Create normalized column mapping
        def normalize_column_name(col_name):
            return str(col_name).strip().lower().replace(' ', '').replace('_', '').replace('-', '')
        
        norm_map = {normalize_column_name(c): c for c in raw_cols}
        print(f"Normalized column mapping: {norm_map}")
        
        def find_column(variants):
            """Find a column by checking multiple variant names"""
            for variant in variants:
                normalized = normalize_column_name(variant)
                if normalized in norm_map:
                    return norm_map[normalized]
            return None
        
        # Enhanced column variants
        column_variants = {
            "type": [
                "type", "transaction_type", "txn_type", "transactiontype", 
                "transaction type", "debit_credit", "debitcredit", "dr_cr",
                "income_expense", "category_type", "payment_type"
            ],
            "category": [
                "category", "cat", "description", "desc", "purpose", 
                "merchant", "vendor", "payee", "details", "remarks", 
                "transaction_description", "memo", "note"
            ],
            "amount": [
                "amount", "amt", "value", "sum", "total", "price", 
                "transaction_amount", "debit", "credit", "balance",
                "withdrawal", "deposit", "payment"
            ],
            "date": [
                "date", "transaction_date", "txn_date", "transactiondate",
                "datetime", "timestamp", "time", "posted_date", "value_date"
            ]
        }
        
        # Find required columns
        found_columns = {}
        missing_columns = []
        
        for required_field, variants in column_variants.items():
            col = find_column(variants)
            if col:
                found_columns[required_field] = col
                print(f"Found {required_field} column: '{col}'")
            else:
                missing_columns.append(required_field)
        
        if missing_columns:
            available_cols = ", ".join(raw_cols)
            raise HTTPException(
                400, 
                f"Missing required columns: {missing_columns}. "
                f"Available columns: [{available_cols}]. "
                f"Expected columns like: {[variants[0] for variants in column_variants.values()]}"
            )
        
        # Find user column if user_id not provided
        user_col = None
        if not user_id:
            user_variants = ["user_id", "userid", "user", "user id", "account", "account_id"]
            user_col = find_column(user_variants)
            if not user_col:
                raise HTTPException(
                    400, 
                    "Either provide user_id parameter or include a user column in CSV"
                )
        
        # Data cleaning functions
        def clean_amount(value):
            """Clean and parse amount values"""
            if pd.isna(value):
                return None
            
            amount_str = str(value).strip()
            amount_str = re.sub(r'[₹$€£,\s]', '', amount_str)
            
            if amount_str.startswith('(') and amount_str.endswith(')'):
                amount_str = '-' + amount_str[1:-1]
            
            match = re.search(r'-?\d+(?:\.\d+)?', amount_str)
            if match:
                try:
                    return float(match.group())
                except ValueError:
                    return None
            return None
        
        def clean_transaction_type(value):
            """Clean and standardize transaction types"""
            if pd.isna(value):
                return "expense"
            
            type_str = str(value).strip().lower()
            
            income_keywords = [
                'income', 'credit', 'deposit', 'received', 'inflow', 
                'salary', 'bonus', 'refund', 'cr', 'in'
            ]
            
            expense_keywords = [
                'expense', 'debit', 'withdrawal', 'spent', 'outflow',
                'payment', 'dr', 'out', 'paid'
            ]
            
            for keyword in income_keywords:
                if keyword in type_str:
                    return "income"
            
            for keyword in expense_keywords:
                if keyword in type_str:
                    return "expense"
            
            return "expense"
        
        def clean_category(value):
            """Clean category values"""
            if pd.isna(value):
                return "Other"
            return str(value).strip().title()
        
        def clean_date(value):
            """Parse date values"""
            if pd.isna(value):
                return datetime.now().date()
            
            try:
                parsed_date = pd.to_datetime(value, dayfirst=True, errors='coerce')
                if not pd.isna(parsed_date):
                    return parsed_date.date()
            except:
                pass
            
            return datetime.now().date()
        
        # Process each row
        successful_inserts = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                raw_amount = row[found_columns["amount"]]
                amount = clean_amount(raw_amount)
                
                if amount is None or amount == 0:
                    errors.append({
                        "row": int(idx + 2),
                        "error": f"Invalid amount: '{raw_amount}'"
                    })
                    continue
                
                type_val = clean_transaction_type(row[found_columns["type"]])
                
                if amount < 0:
                    amount = abs(amount)
                    type_val = "expense" if type_val == "income" else "income"
                
                category = clean_category(row[found_columns["category"]])
                transaction_date = clean_date(row[found_columns["date"]])
                
                tx_user_id = user_id
                if user_col:
                    tx_user_id = str(row[user_col]).strip()
                
                if not tx_user_id:
                    errors.append({
                        "row": int(idx + 2),
                        "error": "Missing user ID"
                    })
                    continue
                
                transaction_data = {
                    "user_id": tx_user_id,
                    "type": type_val,
                    "category": category,
                    "amount": float(amount),
                    "date": datetime.combine(transaction_date, datetime.min.time()) if isinstance(transaction_date, date) else transaction_date,
                }
                
                db.create_transaction(transaction_data)
                successful_inserts += 1
                
            except Exception as e:
                errors.append({
                    "row": int(idx + 2),
                    "error": f"Processing error: {str(e)}"
                })
                continue
        
        print(f"Successfully inserted {successful_inserts} transactions")
        
        return {
            "success": True,
            "inserted": successful_inserts,
            "total_rows": len(df),
            "errors": errors[:10],
            "error_count": len(errors)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in CSV upload: {e}")
        raise HTTPException(500, f"Failed to process CSV: {str(e)}")

@app.get("/api/export_csv")
def export_csv(user_id: str = Query(...)):
    transactions = db.get_transactions(user_id)
    if not transactions:
        return {"csv": ""}
    
    df = pd.DataFrame([{
        "Type": tx.get("type"), 
        "Category": tx.get("category"), 
        "Amount": tx.get("amount"), 
        "Date": tx.get("date").isoformat() if isinstance(tx.get("date"), datetime) else tx.get("date")
    } for tx in transactions])
    
    return {"csv": df.to_csv(index=False)}

@app.get("/api/csv_template")
def get_csv_template():
    """Return a CSV template for users"""
    template_data = {
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "type": ["expense", "income", "expense"],
        "category": ["Food", "Salary", "Transport"],
        "amount": [50.00, 5000.00, 25.50],
    }
    
    df = pd.DataFrame(template_data)
    csv_content = df.to_csv(index=False)
    
    return {
        "csv": csv_content,
        "instructions": {
            "required_columns": ["date", "type", "category", "amount"],
            "date_format": "YYYY-MM-DD or DD/MM/YYYY",
            "type_values": ["income", "expense", "credit", "debit"],
            "amount_format": "Numeric value (e.g., 50.00, -25.50)"
        }
    }

# ====================================================================================
#                                    ANALYTICS
# ====================================================================================

# ====================== ADVANCED ANALYTICS (NEW MODULE) ======================

@app.get("/api/advanced_analytics")
def api_advanced_analytics(user_id: str = Query(...)):
    """
    Compute full advanced analytics based on MongoDB transactions.
    Returns risk assessment, predictions, and weekly insights.
    """
    try:
        analytics = build_advanced_analytics(user_id)
        return analytics
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Advanced Analytics Error: {str(e)}")


class SummaryOut(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    series: List[float]

@app.get("/api/summary", response_model=SummaryOut)
def summary(
    user_id: str = Query(...),
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None, alias="to"),
):
    transactions = db.get_transactions(user_id)
    
    if from_:
        from_dt = datetime.combine(from_, datetime.min.time())
        transactions = [t for t in transactions if isinstance(t.get("date"), datetime) and t["date"] >= from_dt]
    
    if to:
        to_dt = datetime.combine(to, datetime.max.time())
        transactions = [t for t in transactions if isinstance(t.get("date"), datetime) and t["date"] <= to_dt]
    
    income = sum(t["amount"] for t in transactions if t.get("type") == "income")
    expense = sum(t["amount"] for t in transactions if t.get("type") == "expense")
    series = [t["amount"] if t.get("type") == "expense" else -t["amount"] for t in transactions]
    
    return {
        "total_income": income,
        "total_expense": expense,
        "balance": income - expense,
        "series": series,
    }

@app.get("/api/predict")
def predict(user_id: str = Query(...)):
    transactions = db.get_transactions(user_id)
    vals = [t["amount"] if t.get("type") == "expense" else 0.0 for t in transactions]
    fc = forecast(vals, periods=4)
    return {"forecast": fc}

class AnomalyIn(BaseModel):
    values: List[float]

@app.post("/api/anomaly")
def anomaly(inp: AnomalyIn):
    return {"anomalies": detect_anomalies(inp.values)}

class CategorizeIn(BaseModel):
    descriptions: List[str]

@app.post("/api/categorize")
def categorize(inp: CategorizeIn):
    return {"categories": categorize_descriptions(inp.descriptions)}

# ====================================================================================
#                          ENHANCED VOICE INPUT PROCESSING
# ====================================================================================

def parse_relative_date(day_word: str) -> str:
    """Parse relative dates like 'last monday'"""
    days = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    if day_word.lower() in days:
        today = datetime.now().date()
        target_day = days[day_word.lower()]
        days_back = (today.weekday() - target_day + 7) % 7
        if days_back == 0:
            days_back = 7
        target_date = today - timedelta(days=days_back)
        return target_date.isoformat()
    
    return datetime.now().date().isoformat()

def parse_day_name(day_word: str) -> str:
    """Parse day names for current/next week"""
    days = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    if day_word.lower() in days:
        today = datetime.now().date()
        target_day = days[day_word.lower()]
        days_ahead = (target_day - today.weekday()) % 7
        if days_ahead == 0:
            return today.isoformat()
        target_date = today + timedelta(days=days_ahead)
        return target_date.isoformat()
    
    return datetime.now().date().isoformat()

def parse_expense_voice(text: str) -> dict:
    """Enhanced voice parsing with better natural language understanding"""
    text = text.lower().strip()
    print(f"Parsing voice input: '{text}'")
    
    result = {
        "type": "expense",
        "category": None,
        "amount": None,
        "date": None,
    }
    
    # 1. Extract Amount
    amount_patterns = [
        r'(\d+(?:\.\d{1,2})?)\s*(?:rupees?|rs\.?|₹|dollars?|\$)',
        r'(?:rupees?|rs\.?|₹|dollars?|\$)\s*(\d+(?:\.\d{1,2})?)',
        r'(?:spent|paid|cost|costs|worth)\s+(?:about\s+)?(?:rupees?\s*)?(\d+(?:\.\d{1,2})?)',
        r'(?:for\s+)?(\d+(?:\.\d{1,2})?)\s+(?:bucks|only)',
        r'\b(\d+(?:\.\d{1,2})?)\b',
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                result["amount"] = float(match.group(1))
                break
            except (ValueError, IndexError):
                continue
    
    # 2. Determine transaction type
    income_keywords = ["received", "got", "earned", "income", "salary", "bonus", "refund"]
    expense_keywords = ["spent", "paid", "bought", "purchased", "expense", "cost", "bill"]
    
    for keyword in income_keywords:
        if keyword in text:
            result["type"] = "income"
            break
    
    for keyword in expense_keywords:
        if keyword in text:
            result["type"] = "expense"
            break
    
    # 3. Extract Category
    category_keywords = {
        "food": ["food", "eat", "restaurant", "pizza", "burger", "lunch", "dinner", "breakfast", "meal", "snack"],
        "groceries": ["grocery", "groceries", "vegetables", "fruits", "shopping for food", "market"],
        "transport": ["uber", "ola", "taxi", "bus", "metro", "train", "petrol", "fuel", "auto", "rickshaw"],
        "shopping": ["amazon", "flipkart", "myntra", "clothes", "shopping", "online", "purchase"],
        "utilities": ["electricity", "water", "gas", "internet", "wifi", "phone", "mobile", "recharge"],
        "rent": ["rent", "house rent", "apartment"],
        "entertainment": ["movie", "netflix", "spotify", "game", "entertainment", "fun", "party"],
        "healthcare": ["doctor", "medicine", "hospital", "medical", "pharmacy", "health"],
        "salary": ["salary", "pay", "paycheck", "wage"],
        "freelance": ["freelance", "client", "project", "work"],
    }
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text:
                result["category"] = category.title()
                break
        if result["category"]:
            break
    
    # 4. Extract Date
    date_patterns = [
        (r'yesterday', lambda: (datetime.now().date() - timedelta(days=1)).isoformat()),
        (r'today', lambda: datetime.now().date().isoformat()),
        (r'last (\w+)', lambda m: parse_relative_date(m.group(1))),
        (r'on (\w+)', lambda m: parse_day_name(m.group(1))),
    ]
    
    for pattern, date_func in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                # if lambda expects match, call with match; else call directly
                if hasattr(date_func, "__call__"):
                    # if pattern has capture groups, pass match
                    try:
                        res = date_func(match)
                    except TypeError:
                        res = date_func()
                    result["date"] = res
                else:
                    result["date"] = date_func()
                break
            except:
                continue
    
    if not result["category"]:
        result["category"] = "Other"
    
    if not result["date"]:
        result["date"] = datetime.now().date().isoformat()
    
    print(f"Parsed result: {result}")
    return result

# ====================================================================================
#                       VOICE INPUT + WHISPER TRANSCRIPTION
# ====================================================================================

try:
    from faster_whisper import WhisperModel
except Exception:
    print("⚠️ faster_whisper not installed. Voice transcription will be disabled.")
    WhisperModel = None

_whisper_model = None

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    if WhisperModel is None:
        raise HTTPException(status_code=503, detail="Voice transcription is not available")
    global _whisper_model
    if _whisper_model is None:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
        try:
            _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception as e:
            raise HTTPException(500, f"Failed to load Whisper model: {str(e)}")
    
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".webm"
    
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as in_tmp:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(400, "Empty audio file received")
        
        in_tmp.write(content)
        in_path = in_tmp.name
    
    print(f"Received audio file: {len(content)} bytes, extension: {file_ext}")
    
    converted_path = None
    conversion_successful = False
    
    try:
        converted_path = in_path + ".wav"
        subprocess.check_call([
            "ffmpeg", "-y", 
            "-i", in_path,
            "-ar", "16000", 
            "-ac", "1", 
            "-c:a", "pcm_s16le",
            converted_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        
        if os.path.exists(converted_path) and os.path.getsize(converted_path) > 0:
            conversion_successful = True
            print("FFmpeg conversion successful")
        
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"FFmpeg direct conversion failed: {e}")
        if converted_path and os.path.exists(converted_path):
            os.remove(converted_path)
    
    if not conversion_successful:
        try:
            converted_path = in_path + "_alt.wav"
            subprocess.check_call([
                "ffmpeg", "-y",
                "-f", "webm",
                "-i", in_path,
                "-ar", "16000",
                "-ac", "1",
                "-acodec", "pcm_s16le",
                converted_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            
            if os.path.exists(converted_path) and os.path.getsize(converted_path) > 0:
                conversion_successful = True
                print("FFmpeg alternative conversion successful")
                
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"FFmpeg alternative conversion failed: {e}")
            if converted_path and os.path.exists(converted_path):
                os.remove(converted_path)
    
    if not conversion_successful:
        print("Using original file format for transcription")
        converted_path = in_path
    
    try:
        if not os.path.exists(converted_path) or os.path.getsize(converted_path) == 0:
            raise HTTPException(400, "Audio file is empty or corrupted")
        
        print(f"Attempting transcription on: {converted_path} ({os.path.getsize(converted_path)} bytes)")
        
        segments, info = _whisper_model.transcribe(
            converted_path,
            beam_size=3,
            language="en", 
            condition_on_previous_text=False,
            temperature=0.0
        )
        
        transcribed_segments = list(segments)
        text = " ".join([seg.text for seg in transcribed_segments]).strip()
        
        print(f"Transcribed text: '{text}'")
        
        if not text:
            raise HTTPException(400, "No speech detected in audio")
        
        fields = parse_expense_voice(text)
        
        return {
            "text": text,
            "fields": fields,
            "confidence": getattr(info, 'language_probability', 0.9),
            "segments": len(transcribed_segments)
        }
        
    except Exception as e:
        print(f"Transcription error: {e}")
        if "Invalid data" in str(e):
            raise HTTPException(400, "Audio file format not supported or corrupted. Please try recording again.")
        elif "No speech" in str(e):
            raise HTTPException(400, "No speech detected. Please speak clearly and try again.")
        elif "unexpected keyword argument" in str(e):
            try:
                segments, info = _whisper_model.transcribe(converted_path, language="en")
                transcribed_segments = list(segments)
                text = " ".join([seg.text for seg in transcribed_segments]).strip()
                
                if text:
                    fields = parse_expense_voice(text)
                    return {
                        "text": text,
                        "fields": fields,
                        "confidence": 0.8,
                        "segments": len(transcribed_segments)
                    }
                else:
                    raise HTTPException(400, "No speech detected")
            except Exception as fallback_error:
                raise HTTPException(500, f"Transcription failed: {str(fallback_error)}")
        else:
            raise HTTPException(500, f"Transcription failed: {str(e)}")
        
    finally:
        try:
            if os.path.exists(in_path):
                os.remove(in_path)
            if converted_path != in_path and converted_path and os.path.exists(converted_path):
                os.remove(converted_path)
        except Exception as e:
            print(f"Cleanup error: {e}")

@app.post("/api/test_audio")
async def test_audio_format(file: UploadFile = File(...)):
    """Test endpoint to check audio file format and content"""
    content = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "first_bytes": content[:20].hex() if content else "empty",
    }

# ====================================================================================
#                         NOTIFICATION & INVESTMENT ADVICE
# ====================================================================================

def send_notification(user_id: str, message: str):
    print(f"Notify {user_id}: {message}")

def send_alert(user_id: str, message: str):
    print(f"ALERT for {user_id}: {message}")

@app.get("/api/investment_advice")
def investment_advice(user_id: str = Query(...)):
    transactions = db.get_transactions(user_id)
    income = sum(t["amount"] for t in transactions if t.get("type") == "income")
    expense = sum(t["amount"] for t in transactions if t.get("type") == "expense")
    balance = income - expense
    
    advice = []
    if balance < 0:
        advice.append("Your balance is negative. Reduce expenses or increase income. Consider emergency fund.")
    elif expense > income * 0.8:
        advice.append("High spending detected. Try to save at least 20% of your income.")
    else:
        advice.append("Good financial health. Consider investing in SIPs or mutual funds.")
    
    if balance > 0:
        if balance > income * 0.1:
            advice.append("Excellent savings rate! Consider diversifying investments.")
        else:
            advice.append("Good start! Try to increase your savings rate gradually.")
    
    vals = [t["amount"] if t.get("type") == "expense" else 0.0 for t in transactions]
    fc = forecast(vals, periods=4)
    
    return {
        "advice": advice,
        "forecast_next_months": fc,
        "current_balance": balance,
        "savings_rate": (balance / income * 100) if income > 0 else 0,
        "recommendations": [
            "Set up automatic savings transfers",
            "Review and optimize your expense categories",
            "Consider tax-saving investment options",
            "Build an emergency fund of 3-6 months expenses"
        ]
    }

# ====================================================================================
#                          CONVERSATIONAL AGENTS & GEMINI AI
# ====================================================================================

class ChatQueryIn(BaseModel):
    user_id: str
    query: str

@app.post("/api/chat")
def chat_with_agent(inp: ChatQueryIn):
    """Main conversational interface for all agentic features"""
    try:
        agent = ConversationalAgent()
        response = agent.process_query(inp.user_id, inp.query)
        return response
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "type": "error",
            "query": inp.query,
            "error": f"Failed to process query: {str(e)}",
            "suggestions": [
                "Try asking about your spending",
                "Ask for budget analysis",
                "Request spending predictions",
                "Check for unusual transactions"
            ]
        }

@app.post("/api/gemini/chat")
async def gemini_chat(inp: ChatQueryIn):
    """Enhanced chat using Gemini AI with user's financial data"""
    try:
        gemini_assistant = get_gemini_assistant()
        if gemini_assistant.is_available():
            response = await gemini_assistant.process_query(inp.user_id, inp.query)
        else:
            response = gemini_assistant._fallback_response(inp.user_id, inp.query)
        return response
    except Exception as e:
        print(f"Gemini chat error: {e}")
        return {
            "type": "error",
            "query": inp.query,
            "error": f"Gemini AI error: {str(e)}",
            "fallback_response": "I'm having trouble processing your request. Please try again or check your internet connection."
        }

@app.get("/api/gemini/analyze/{user_id}")
async def gemini_analyze_data(user_id: str):
    """Get comprehensive data analysis using Gemini AI"""
    try:
        gemini_assistant = get_gemini_assistant()
        if gemini_assistant.is_available():
            analysis = gemini_assistant.analyze_data_patterns(user_id)
        else:
            analysis = {"error": "Gemini AI not configured. Please set GEMINI_API_KEY environment variable."}
        return analysis
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

@app.delete("/api/gemini/clear-history/{user_id}")
def clear_gemini_history(user_id: str):
    """Clear conversation history for a user"""
    try:
        gemini_assistant = get_gemini_assistant()
        gemini_assistant.clear_conversation_history(user_id)
        return {"success": True, "message": "Conversation history cleared"}
    except Exception as e:
        return {"error": f"Failed to clear history: {str(e)}"}

@app.get("/api/gemini/conversation-summary/{user_id}")
def get_conversation_summary(user_id: str):
    """Get conversation summary for a user"""
    try:
        gemini_assistant = get_gemini_assistant()
        summary = gemini_assistant.get_conversation_summary(user_id)
        return summary
    except Exception as e:
        return {"error": f"Failed to get summary: {str(e)}"}

@app.get("/api/gemini/status")
def gemini_status():
    """Check Gemini AI configuration status"""
    try:
        gemini_assistant = get_gemini_assistant()
        return {
            "available": gemini_assistant.is_available(),
            "configured": getattr(gemini_assistant, "is_configured", False),
            "api_key_set": bool(getattr(gemini_assistant, "api_key", None)),
            "message": "Gemini AI is ready" if gemini_assistant.is_available() else "Gemini AI not configured. Set GEMINI_API_KEY environment variable."
        }
    except Exception as e:
        return {
            "available": False,
            "configured": False,
            "api_key_set": False,
            "message": f"Error checking Gemini AI status: {str(e)}"
        }

# ====================================================================================
#                                WEBSOCKET (REAL-TIME)
# ====================================================================================

@app.websocket("/ws/{user_id}")
async def websocket_route(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat with Gemini AI"""
    await websocket_endpoint(websocket, user_id)

@app.get("/api/websocket/status")
def websocket_status():
    """Get WebSocket connection status"""
    return {
        "total_connections": manager.get_total_connections(),
        "connected_users": manager.get_connected_users(),
        "status": "active"
    }

@app.post("/api/websocket/notify/{user_id}")
async def send_notification_to_user(user_id: str, notification: dict):
    """Send notification to a specific user via WebSocket"""
    try:
        await manager.send_notification(user_id, notification)
        return {"success": True, "message": "Notification sent"}
    except Exception as e:
        return {"error": f"Failed to send notification: {str(e)}"}

# ====================================================================================
#                                ALERTS & INSIGHTS
# ====================================================================================

@app.get("/api/check_alerts")
def check_alerts(user_id: str = Query(...)):
    """Check for financial alerts for a user"""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            return {"alerts": [], "message": "User not found"}
        
        txs = db.get_transactions(user_id)
        total_expense = sum(t["amount"] for t in txs if t["type"] == "expense")
        total_income = sum(t["amount"] for t in txs if t["type"] == "income")
        balance = total_income - total_expense
        
        alerts = []
        if balance < 0:
            alerts.append({
                "type": "warning",
                "message": f"Your account balance is negative: ₹{abs(balance):.2f}",
                "severity": "high"
            })
        
        daily_avg_expense = total_expense / max(1, len(txs)) if txs else 0
        recent_expenses = [t["amount"] for t in txs[-5:] if t["type"] == "expense"]
        if recent_expenses and max(recent_expenses) > daily_avg_expense * 2:
            alerts.append({
                "type": "info",
                "message": "Recent spending exceeds your average",
                "severity": "medium"
            })
        
        if total_income == 0 and len(txs) > 0:
            alerts.append({
                "type": "warning",
                "message": "No income recorded. Track your earnings!",
                "severity": "medium"
            })
        
        return {"alerts": alerts, "total_alerts": len(alerts)}
    except Exception as e:
        return {"alerts": [], "error": str(e), "total_alerts": 0}

@app.get("/api/weekly_insights")
def weekly_insights(user_id: str = Query(...)):
    """Get weekly spending insights for a user"""
    try:
        txs = db.get_transactions(user_id)
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        
        # flexible ISO parsing for stored date strings or datetimes
        def to_dt(d):
            if isinstance(d, datetime):
                return d
            try:
                # try isoformat string
                return datetime.fromisoformat(d.replace('Z', '+00:00'))
            except Exception:
                try:
                    return pd.to_datetime(d)
                except Exception:
                    return None
        
        weekly_txs = [
            t for t in txs 
            if (dt := to_dt(t.get("date"))) is not None and dt >= week_ago
        ]
        
        total_expense = sum(t["amount"] for t in weekly_txs if t["type"] == "expense")
        total_income = sum(t["amount"] for t in weekly_txs if t["type"] == "income")
        
        category_breakdown = {}
        for t in weekly_txs:
            if t["type"] == "expense":
                cat = t.get("category", "Other")
                category_breakdown[cat] = category_breakdown.get(cat, 0) + t["amount"]
        
        top_category = max(category_breakdown.items(), key=lambda x: x[1])[0] if category_breakdown else "None"
        
        daily_expenses = {}
        for t in weekly_txs:
            if t["type"] == "expense":
                date_key = (t["date"][:10] if isinstance(t.get("date"), str) else t["date"].strftime("%Y-%m-%d"))
                daily_expenses[date_key] = daily_expenses.get(date_key, 0) + t["amount"]
        
        spending_trend = "unknown"
        if len(daily_expenses) > 1:
            vals = list(daily_expenses.values())
            spending_trend = "increasing" if vals[-1] > vals[0] else "stable"
        
        insights = {
            "week_total_expense": total_expense,
            "week_total_income": total_income,
            "week_balance": total_income - total_expense,
            "average_daily_expense": total_expense / 7 if total_expense > 0 else 0,
            "top_category": top_category,
            "category_breakdown": category_breakdown,
            "daily_breakdown": daily_expenses,
            "transaction_count": len(weekly_txs),
            "spending_trend": spending_trend
        }
        
        return insights
    except Exception as e:
        return {
            "week_total_expense": 0,
            "week_total_income": 0,
            "week_balance": 0,
            "average_daily_expense": 0,
            "top_category": "None",
            "category_breakdown": {},
            "daily_breakdown": {},
            "transaction_count": 0,
            "error": str(e),
            "spending_trend": "unknown"
        }

# ====================================================================================
#                                 USER FEEDBACK
# ====================================================================================

class FeedbackIn(BaseModel):
    user_id: str
    feedback: str

@app.post("/api/feedback")
def user_feedback(inp: FeedbackIn):
    print(f"Feedback from {inp.user_id}: {inp.feedback}")
    send_notification(inp.user_id, "Thank you for your feedback!")
    return {"success": True, "message": "Feedback received"}

# End of file
