from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date, datetime, timedelta
import io, os, tempfile, subprocess, re
import pandas as pd
from sqlmodel import select, Session
from pydantic import BaseModel
from .db import init_db, get_session
from .models import Transaction
from .ml import categorize_descriptions, forecast, detect_anomalies
from .agents import ConversationalAgent, CategorizationAgent, PredictionAgent, AnomalyAgent, GoalSettingAgent, NotificationAgent, RiskAssessmentAgent, PredictiveAnalyticsAgent
from .gemini_ai import get_gemini_assistant
from .websocket_handler import websocket_endpoint, manager
from . import auth

# ------------ FastAPI App ------------
app = FastAPI(title="Savion Backend", version="0.2.0")

allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174").split(",")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

app.add_middleware(
    CORSMiddleware,
    allow_origins="*" if "ALL" in allowed else allowed,
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# ------------ Schemas ------------
class TxIn(BaseModel):
    user_id: str
    type: str  # 'income' or 'expense'
    category: str
    amount: float
    date: date

class TxOut(TxIn):
    id: int
    created_at: datetime

# ------------ CRUD Transaction APIs ------------
@app.get("/api/transactions", response_model=List[TxOut])
def list_transactions(user_id: str = Query(...), session: Session = Depends(get_session)):
    stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
    return session.exec(stmt).all()

@app.post("/api/transactions", response_model=TxOut)
def create_transaction(tx: TxIn, session: Session = Depends(get_session)):
    item = Transaction(**tx.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@app.put("/api/transactions/{tx_id}", response_model=TxOut)
def update_transaction(tx_id: int, tx: TxIn, session: Session = Depends(get_session)):
    item = session.get(Transaction, tx_id)
    if not item:
        raise HTTPException(404, "Transaction not found")
    for k, v in tx.model_dump().items():
        setattr(item, k, v)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: int, session: Session = Depends(get_session)):
    item = session.get(Transaction, tx_id)
    if not item:
        raise HTTPException(404, "Transaction not found")
    session.delete(item)
    session.commit()
    return {"deleted": tx_id}

# ------------ Enhanced CSV Upload/Export ------------
@app.post("/api/upload_csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """
    Enhanced CSV upload with better error handling and flexibility
    """
    if not file.filename.lower().endswith('.csv'):
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
                    sep=None,  # Auto-detect separator
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
            
            # Convert to string and clean
            amount_str = str(value).strip()
            
            # Remove common currency symbols and formatting
            amount_str = re.sub(r'[₹$€£,\s]', '', amount_str)
            
            # Handle parentheses for negative amounts
            if amount_str.startswith('(') and amount_str.endswith(')'):
                amount_str = '-' + amount_str[1:-1]
            
            # Extract numeric value
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
            
            # Income indicators
            income_keywords = [
                'income', 'credit', 'deposit', 'received', 'inflow', 
                'salary', 'bonus', 'refund', 'cr', 'in'
            ]
            
            # Expense indicators  
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
            
            # If amount is positive, assume income, negative assume expense
            return "expense"  # default
        
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
                # Try pandas date parsing
                parsed_date = pd.to_datetime(value, dayfirst=True, errors='coerce')
                if not pd.isna(parsed_date):
                    return parsed_date.date()
            except:
                pass
            
            # Fallback to current date
            return datetime.now().date()
        
        # Process each row
        successful_inserts = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Extract and clean data
                raw_amount = row[found_columns["amount"]]
                amount = clean_amount(raw_amount)
                
                if amount is None or amount == 0:
                    errors.append({
                        "row": int(idx + 2),  # +2 for 1-indexed and header
                        "error": f"Invalid amount: '{raw_amount}'"
                    })
                    continue
                
                # Determine transaction type
                type_val = clean_transaction_type(row[found_columns["type"]])
                
                # For negative amounts, flip the type
                if amount < 0:
                    amount = abs(amount)
                    type_val = "expense" if type_val == "income" else "income"
                
                category = clean_category(row[found_columns["category"]])
                transaction_date = clean_date(row[found_columns["date"]])
                
                # Get user ID
                tx_user_id = user_id
                if user_col:
                    tx_user_id = str(row[user_col]).strip()
                
                if not tx_user_id:
                    errors.append({
                        "row": int(idx + 2),
                        "error": "Missing user ID"
                    })
                    continue
                
                # Create transaction
                transaction = Transaction(
                    user_id=tx_user_id,
                    type=type_val,
                    category=category,
                    amount=float(amount),
                    date=transaction_date
                )
                
                session.add(transaction)
                successful_inserts += 1
                
            except Exception as e:
                errors.append({
                    "row": int(idx + 2),
                    "error": f"Processing error: {str(e)}"
                })
                continue
        
        # Commit successful transactions
        try:
            session.commit()
            print(f"Successfully inserted {successful_inserts} transactions")
        except Exception as e:
            session.rollback()
            raise HTTPException(500, f"Database error: {str(e)}")
        
        return {
            "success": True,
            "inserted": successful_inserts,
            "total_rows": len(df),
            "errors": errors[:10],  # Limit error list
            "error_count": len(errors)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in CSV upload: {e}")
        raise HTTPException(500, f"Failed to process CSV: {str(e)}")

@app.get("/api/export_csv")
def export_csv(user_id: str = Query(...), session: Session = Depends(get_session)):
    stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
    items = session.exec(stmt).all()
    if not items:
        return {"csv": ""}
    df = pd.DataFrame([{
        "Type": it.type, "Category": it.category, "Amount": it.amount, "Date": it.date.isoformat()
    } for it in items])
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

# ------------ Analytics ------------
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
    session: Session = Depends(get_session),
):
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if from_:
        stmt = stmt.where(Transaction.date >= from_)
    if to:
        stmt = stmt.where(Transaction.date <= to)
    items = session.exec(stmt).all()
    income = sum(it.amount for it in items if it.type == "income")
    expense = sum(it.amount for it in items if it.type == "expense")
    series = [it.amount if it.type == "expense" else -it.amount for it in items]
    return {
        "total_income": income,
        "total_expense": expense,
        "balance": income - expense,
        "series": series,
    }

@app.get("/api/predict")
def predict(user_id: str = Query(...), session: Session = Depends(get_session)):
    stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
    items = session.exec(stmt).all()
    vals = [it.amount if it.type == "expense" else 0.0 for it in items]
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

# ------------ Enhanced Voice Input Processing ------------
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
        if days_back == 0:  # If today is the target day, go back a week
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
        if days_ahead == 0:  # If today is the target day
            return today.isoformat()
        target_date = today + timedelta(days=days_ahead)
        return target_date.isoformat()
    
    return datetime.now().date().isoformat()

def parse_expense_voice(text: str) -> dict:
    """
    Enhanced voice parsing with better natural language understanding
    """
    text = text.lower().strip()
    print(f"Parsing voice input: '{text}'")
    
    # Initialize result
    result = {
        "type": "expense",  # default
        "category": None,
        "amount": None,
        "date": None,
    }
    
    # 1. Extract Amount - Look for various patterns
    amount_patterns = [
        r'(\d+(?:\.\d{1,2})?)\s*(?:rupees?|rs\.?|₹|dollars?|\$)',  # "50 rupees", "100 rs"
        r'(?:rupees?|rs\.?|₹|dollars?|\$)\s*(\d+(?:\.\d{1,2})?)',   # "rs 50", "₹ 100"
        r'(?:spent|paid|cost|costs|worth)\s+(?:about\s+)?(?:rupees?\s*)?(\d+(?:\.\d{1,2})?)',  # "spent 50"
        r'(?:for\s+)?(\d+(?:\.\d{1,2})?)\s+(?:bucks|only)',       # "50 bucks", "100 only"
        r'\b(\d+(?:\.\d{1,2})?)\b',  # fallback: any number
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
    
    # Expense keywords can override if found later
    for keyword in expense_keywords:
        if keyword in text:
            result["type"] = "expense"
            break
    
    # 3. Extract Category - Enhanced keyword mapping
    category_keywords = {
        # Food related
        "food": ["food", "eat", "restaurant", "pizza", "burger", "lunch", "dinner", "breakfast", "meal", "snack"],
        "groceries": ["grocery", "groceries", "vegetables", "fruits", "shopping for food", "market"],
        
        # Transport
        "transport": ["uber", "ola", "taxi", "bus", "metro", "train", "petrol", "fuel", "auto", "rickshaw"],
        
        # Shopping
        "shopping": ["amazon", "flipkart", "myntra", "clothes", "shopping", "online", "purchase"],
        
        # Bills & Utilities  
        "utilities": ["electricity", "water", "gas", "internet", "wifi", "phone", "mobile", "recharge"],
        "rent": ["rent", "house rent", "apartment"],
        
        # Entertainment
        "entertainment": ["movie", "netflix", "spotify", "game", "entertainment", "fun", "party"],
        
        # Healthcare
        "healthcare": ["doctor", "medicine", "hospital", "medical", "pharmacy", "health"],
        
        # Income categories
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
    
    # 4. Extract Date - Enhanced patterns
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
                result["date"] = date_func(match) if callable(date_func) else date_func()
                break
            except:
                continue
    
    # Set default category if not found
    if not result["category"]:
        result["category"] = "Other"
    
    # Set default date if not found  
    if not result["date"]:
        result["date"] = datetime.now().date().isoformat()
    
    print(f"Parsed result: {result}")
    return result

# ------------ Voice Input with Enhanced Processing ------------
from faster_whisper import WhisperModel

_whisper_model = None

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    global _whisper_model
    if _whisper_model is None:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
        try:
            _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception as e:
            raise HTTPException(500, f"Failed to load Whisper model: {str(e)}")
    
    # Create temporary file with proper extension
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".webm"
    
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as in_tmp:
        content = await file.read()
        
        # Check if file has content
        if len(content) == 0:
            raise HTTPException(400, "Empty audio file received")
        
        in_tmp.write(content)
        in_path = in_tmp.name
    
    print(f"Received audio file: {len(content)} bytes, extension: {file_ext}")
    
    # Try multiple conversion approaches
    converted_path = None
    conversion_successful = False
    
    # Approach 1: Direct conversion to WAV
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
        
        # Verify the converted file exists and has content
        if os.path.exists(converted_path) and os.path.getsize(converted_path) > 0:
            conversion_successful = True
            print("FFmpeg conversion successful")
        
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"FFmpeg direct conversion failed: {e}")
        if converted_path and os.path.exists(converted_path):
            os.remove(converted_path)
    
    # Approach 2: Try with different FFmpeg options if first failed
    if not conversion_successful:
        try:
            converted_path = in_path + "_alt.wav"
            subprocess.check_call([
                "ffmpeg", "-y",
                "-f", "webm",  # Force input format
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
    
    # Approach 3: Use original file if conversion failed
    if not conversion_successful:
        print("Using original file format for transcription")
        converted_path = in_path
    
    try:
        # Verify file exists and has content before transcription
        if not os.path.exists(converted_path) or os.path.getsize(converted_path) == 0:
            raise HTTPException(400, "Audio file is empty or corrupted")
        
        print(f"Attempting transcription on: {converted_path} ({os.path.getsize(converted_path)} bytes)")
        
        # Transcribe audio with compatible parameters only
        segments, info = _whisper_model.transcribe(
            converted_path,
            beam_size=3,
            language="en", 
            condition_on_previous_text=False,
            temperature=0.0
            # Removed incompatible parameters: compression_ratio_threshold, logprob_threshold, no_speech_threshold
        )
        
        # Collect all transcribed text
        transcribed_segments = list(segments)
        text = " ".join([seg.text for seg in transcribed_segments]).strip()
        
        print(f"Transcribed text: '{text}'")
        
        if not text:
            raise HTTPException(400, "No speech detected in audio")
        
        # Parse the transcribed text for transaction fields
        fields = parse_expense_voice(text)
        
        return {
            "text": text,
            "fields": fields,
            "confidence": getattr(info, 'language_probability', 0.9),
            "segments": len(transcribed_segments)
        }
        
    except Exception as e:
        print(f"Transcription error: {e}")
        # Provide more specific error messages
        if "Invalid data" in str(e):
            raise HTTPException(400, "Audio file format not supported or corrupted. Please try recording again.")
        elif "No speech" in str(e):
            raise HTTPException(400, "No speech detected. Please speak clearly and try again.")
        elif "unexpected keyword argument" in str(e):
            # Handle version compatibility issues
            try:
                # Fallback with minimal parameters
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
        # Cleanup temporary files
        try:
            if os.path.exists(in_path):
                os.remove(in_path)
            if converted_path != in_path and converted_path and os.path.exists(converted_path):
                os.remove(converted_path)
        except Exception as e:
            print(f"Cleanup error: {e}")

# Also add this endpoint to check audio file formats
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
    
# ------------ Notification & Alert Helper ------------
def send_notification(user_id: str, message: str):
    # TODO: Integrate with email, SMS, push, or websocket
    print(f"Notify {user_id}: {message}")

def send_alert(user_id: str, message: str):
    # TODO: Integrate with alarm/alert system
    print(f"ALERT for {user_id}: {message}")

# ------------ CRUD Transaction APIs (Upgrade) ------------
@app.post("/api/transactions", response_model=TxOut)
def create_transaction(tx: TxIn, session: Session = Depends(get_session)):
    item = Transaction(**tx.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    # Notify user on addition
    send_notification(item.user_id, f"New transaction added: {item.type} {item.amount} for {item.category} on {item.date}")
    # Check balance and alert if negative
    stmt = select(Transaction).where(Transaction.user_id == item.user_id)
    items = session.exec(stmt).all()
    income = sum(it.amount for it in items if it.type == "income")
    expense = sum(it.amount for it in items if it.type == "expense")
    balance = income - expense
    if balance < 0:
        send_alert(item.user_id, f"Your balance is negative: {balance}")
    return item

# ------------ Investment Advice Endpoint ------------
@app.get("/api/investment_advice")
def investment_advice(user_id: str = Query(...), session: Session = Depends(get_session)):
    stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
    items = session.exec(stmt).all()
    income = sum(it.amount for it in items if it.type == "income")
    expense = sum(it.amount for it in items if it.type == "expense")
    balance = income - expense
    # Simple advice logic
    if balance < 0:
        advice = "Your balance is negative. Reduce expenses or increase income. Consider emergency fund."
    elif expense > income * 0.8:
        advice = "High spending detected. Try to save at least 20% of your income."
    else:
        advice = "Good financial health. Consider investing in SIPs or mutual funds."
    # Future prediction (reuse forecast)
    vals = [it.amount if it.type == "expense" else 0.0 for it in items]
    fc = forecast(vals, periods=4)
    return {
        "advice": advice,
        "forecast_next_months": fc,
        "current_balance": balance
    }

# ------------ Conversational AI Agent Endpoints ------------
class ChatQueryIn(BaseModel):
    user_id: str
    query: str

@app.post("/api/chat")
def chat_with_agent(inp: ChatQueryIn, session: Session = Depends(get_session)):
    """Main conversational interface for all agentic features"""
    try:
        agent = ConversationalAgent(session)
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

# ------------ Gemini AI Enhanced Chat Endpoints ------------
@app.post("/api/gemini/chat")
async def gemini_chat(inp: ChatQueryIn, session: Session = Depends(get_session)):
    """Enhanced chat using Gemini AI with user's financial data"""
    try:
        gemini_assistant = get_gemini_assistant()
        if gemini_assistant.is_available():
            response = await gemini_assistant.process_query(inp.user_id, inp.query, session)
        else:
            response = gemini_assistant._fallback_response(inp.user_id, inp.query, session)
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
async def gemini_analyze_data(user_id: str, session: Session = Depends(get_session)):
    """Get comprehensive data analysis using Gemini AI"""
    try:
        gemini_assistant = get_gemini_assistant()
        if gemini_assistant.is_available():
            analysis = gemini_assistant.analyze_data_patterns(user_id, session)
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
            "configured": gemini_assistant.is_configured,
            "api_key_set": bool(gemini_assistant.api_key),
            "message": "Gemini AI is ready" if gemini_assistant.is_available() else "Gemini AI not configured. Set GEMINI_API_KEY environment variable."
        }
    except Exception as e:
        return {
            "available": False,
            "configured": False,
            "api_key_set": False,
            "message": f"Error checking Gemini AI status: {str(e)}"
        }

# ------------ WebSocket Real-time Chat ------------
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

# ------------ Enhanced Categorization Agent ------------
class CategorizeTransactionIn(BaseModel):
    user_id: str
    transaction_id: int
    new_category: str

@app.post("/api/categorize_transaction")
def categorize_transaction(inp: CategorizeTransactionIn, session: Session = Depends(get_session)):
    """Enhanced transaction categorization with correction support"""
    try:
        agent = CategorizationAgent()
        result = agent.correct_classification(inp.transaction_id, inp.new_category)
        
        # Update the transaction in database
        transaction = session.get(Transaction, inp.transaction_id)
        if transaction and transaction.user_id == inp.transaction_id:
            transaction.category = inp.new_category
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            result["transaction"] = transaction
        
        return result
    except Exception as e:
        return {"error": f"Failed to categorize transaction: {str(e)}"}

# ------------ Spending Prediction Agent ------------
@app.get("/api/predict_spending")
def predict_spending(user_id: str = Query(...), periods: int = Query(4), session: Session = Depends(get_session)):
    """Enhanced spending prediction with LSTM models"""
    try:
        stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
        transactions = session.exec(stmt).all()
        
        expense_values = [t.amount for t in transactions if t.type == 'expense']
        
        agent = PredictionAgent()
        result = agent.predict_spending(user_id, expense_values, periods)
        
        return result
    except Exception as e:
        return {"error": f"Failed to predict spending: {str(e)}"}

# ------------ Anomaly Detection Agent ------------
@app.get("/api/detect_anomalies")
def detect_anomalies_endpoint(user_id: str = Query(...), days: int = Query(30), session: Session = Depends(get_session)):
    """Enhanced anomaly detection using Isolation Forest"""
    try:
        # Get transactions from last N days
        start_date = datetime.now().date() - timedelta(days=days)
        stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.date >= start_date
        ).order_by(Transaction.date)
        transactions = session.exec(stmt).all()
        
        agent = AnomalyAgent()
        result = agent.detect_anomalies(user_id, transactions)
        
        return result
    except Exception as e:
        return {"error": f"Failed to detect anomalies: {str(e)}"}

# ------------ Goal Setting Agent ------------
class CreateGoalIn(BaseModel):
    user_id: str
    goal_amount: float
    timeframe_months: int

class ExpenseReductionIn(BaseModel):
    user_id: str
    target_reduction_percent: float

@app.post("/api/create_savings_goal")
def create_savings_goal(inp: CreateGoalIn, session: Session = Depends(get_session)):
    """Create a savings goal with recommendations"""
    try:
        agent = GoalSettingAgent(session)
        result = agent.create_savings_goal(inp.user_id, inp.goal_amount, inp.timeframe_months)
        return result
    except Exception as e:
        return {"error": f"Failed to create savings goal: {str(e)}"}

@app.post("/api/expense_reduction_suggestions")
def get_expense_reduction_suggestions(inp: ExpenseReductionIn, session: Session = Depends(get_session)):
    """Get suggestions for reducing expenses"""
    try:
        agent = GoalSettingAgent(session)
        result = agent.get_expense_reduction_suggestions(inp.user_id, inp.target_reduction_percent)
        return result
    except Exception as e:
        return {"error": f"Failed to get expense reduction suggestions: {str(e)}"}

# ------------ Proactive Notification Agent ------------
@app.get("/api/check_alerts")
def check_alerts(user_id: str = Query(...), session: Session = Depends(get_session)):
    """Check for spending alerts and notifications"""
    try:
        agent = NotificationAgent(session)
        alerts = agent.check_spending_alerts(user_id)
        return {"alerts": alerts, "alert_count": len(alerts)}
    except Exception as e:
        return {"error": f"Failed to check alerts: {str(e)}"}

@app.get("/api/weekly_insights")
def get_weekly_insights(user_id: str = Query(...), session: Session = Depends(get_session)):
    """Get weekly insights and recommendations"""
    try:
        agent = NotificationAgent(session)
        insights = agent.generate_weekly_insights(user_id)
        return insights
    except Exception as e:
        return {"error": f"Failed to generate weekly insights: {str(e)}"}

# ------------ Risk Assessment Agent ------------
@app.get("/api/risk_assessment")
def get_risk_assessment(user_id: str = Query(...), session: Session = Depends(get_session)):
    """Get comprehensive risk assessment"""
    try:
        agent = RiskAssessmentAgent(session)
        assessment = agent.comprehensive_risk_assessment(user_id)
        return assessment
    except Exception as e:
        return {"error": f"Failed to assess risk: {str(e)}"}

# ------------ Predictive Analytics Agent ------------
@app.get("/api/predictive_analytics")
def get_predictive_analytics(user_id: str = Query(...), session: Session = Depends(get_session)):
    """Get comprehensive predictive analytics"""
    try:
        agent = PredictiveAnalyticsAgent(session)
        predictions = agent.comprehensive_prediction(user_id)
        return predictions
    except Exception as e:
        return {"error": f"Failed to generate predictions: {str(e)}"}

# ------------ Advanced Analytics Dashboard ------------
@app.get("/api/advanced_analytics")
def get_advanced_analytics(user_id: str = Query(...), session: Session = Depends(get_session)):
    """Get comprehensive advanced analytics including risk and predictions"""
    try:
        # Get risk assessment
        risk_agent = RiskAssessmentAgent(session)
        risk_assessment = risk_agent.comprehensive_risk_assessment(user_id)
        
        # Get predictive analytics
        prediction_agent = PredictiveAnalyticsAgent(session)
        predictions = prediction_agent.comprehensive_prediction(user_id)
        
        # Get weekly insights
        notification_agent = NotificationAgent(session)
        weekly_insights = notification_agent.generate_weekly_insights(user_id)
        
        return {
            "risk_assessment": risk_assessment,
            "predictions": predictions,
            "weekly_insights": weekly_insights,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": f"Failed to generate advanced analytics: {str(e)}"}

# ------------ Investment Advice Enhancement ------------
@app.get("/api/investment_advice")
def investment_advice(user_id: str = Query(...), session: Session = Depends(get_session)):
    stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
    items = session.exec(stmt).all()
    income = sum(it.amount for it in items if it.type == "income")
    expense = sum(it.amount for it in items if it.type == "expense")
    balance = income - expense
    
    # Enhanced advice logic with agentic insights
    advice = []
    if balance < 0:
        advice.append("Your balance is negative. Reduce expenses or increase income. Consider emergency fund.")
    elif expense > income * 0.8:
        advice.append("High spending detected. Try to save at least 20% of your income.")
    else:
        advice.append("Good financial health. Consider investing in SIPs or mutual funds.")
    
    # Add AI-powered recommendations
    if balance > 0:
        if balance > income * 0.1:  # More than 10% of income saved
            advice.append("Excellent savings rate! Consider diversifying investments.")
        else:
            advice.append("Good start! Try to increase your savings rate gradually.")
    
    # Future prediction (reuse forecast)
    vals = [it.amount if it.type == "expense" else 0.0 for it in items]
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

# ------------ User Feedback Endpoint ------------
class FeedbackIn(BaseModel):
    user_id: str
    feedback: str

@app.post("/api/feedback")
def user_feedback(inp: FeedbackIn):
    # Store feedback, notify admin, etc.
    print(f"Feedback from {inp.user_id}: {inp.feedback}")
    send_notification(inp.user_id, "Thank you for your feedback!")
    return {"success": True, "message": "Feedback received"}
