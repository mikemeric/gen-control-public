# ==============================================================================
# DATABASE.PY - V1.1.5 (Support Paiement Manuel "Low-Tech")
# ==============================================================================
import sqlite3
import threading
import bcrypt
from datetime import datetime, timedelta

class ThreadSafeDatabase:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ThreadSafeDatabase, cls).__new__(cls)
                    cls._instance.db_path = "gen_control_v1_1_secure.db"
                    cls._instance._init_database()
        return cls._instance

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def execute_read(self, query, params=()):
        with self._lock:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                return cursor.fetchall()
            finally:
                conn.close()

    def execute_write(self, query, params=()):
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def _init_database(self):
        conn = self.get_connection()
        c = conn.cursor()
        
        # TABLES EXISTANTES (Users, Equipment, Audits, Overrides)
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL, password_hash BYTES NOT NULL, role TEXT DEFAULT 'user',
                      license_tier TEXT DEFAULT 'DISCOVERY', signup_ip TEXT, two_factor_secret TEXT,
                      subscription_end TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS equipment
                     (equipment_id TEXT PRIMARY KEY, equipment_name TEXT, profile_base TEXT, power_kw REAL,
                      is_calibrated INTEGER DEFAULT 0, last_calibration TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS audits
                     (audit_uuid TEXT PRIMARY KEY, timestamp TIMESTAMP, created_by TEXT, equipment_id TEXT,
                      materiel_type TEXT, materiel_name TEXT, scenario_code TEXT, index_start REAL, index_end REAL,
                      power_kw REAL, fuel_declared_l REAL, estimated_min REAL, estimated_typ REAL, estimated_max REAL,
                      uncertainty_pct REAL, deviation_pct REAL, z_score REAL, verdict TEXT, confidence_pct INTEGER,
                      validated_by_operator INTEGER)''')

        c.execute('''CREATE TABLE IF NOT EXISTS equipment_load_overrides
                     (equipment_id TEXT, scenario_code TEXT, load_min REAL, load_typ REAL, load_max REAL,
                      learned_from_n_samples INTEGER, confidence_score REAL, last_updated TIMESTAMP, is_active INTEGER DEFAULT 1,
                      PRIMARY KEY (equipment_id, scenario_code))''')

        # 5. TRANSACTIONS (Adapté pour le MANUEL)
        c.execute('''CREATE TABLE IF NOT EXISTS transactions
                     (tx_ref TEXT PRIMARY KEY,
                      username TEXT,
                      amount REAL,
                      status TEXT, -- PENDING, APPROVED, REJECTED
                      payment_method TEXT,
                      mobile_money_id TEXT, -- L'ID saisi par le client
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # MIGRATIONS DE SECOURS
        try: c.execute("ALTER TABLE users ADD COLUMN subscription_end TIMESTAMP")
        except: pass
        try: c.execute("ALTER TABLE transactions ADD COLUMN mobile_money_id TEXT")
        except: pass

        # SEED ADMIN
        c.execute("SELECT count(*) FROM users")
        if c.fetchone()[0] == 0:
            pw_hash = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
            c.execute("INSERT INTO users (username, password_hash, role, license_tier, signup_ip, subscription_end) VALUES (?, ?, ?, ?, ?, ?)", 
                      ("admin", pw_hash, "admin", "CORPORATE", "127.0.0.1", "2099-12-31 23:59:59"))
            conn.commit()
        conn.close()

    # --- MÉTIER : GESTION PAIEMENT MANUEL ---
    
    def declare_manual_payment(self, tx_ref, username, amount, mobile_id):
        """Le client déclare avoir payé"""
        self.execute_write(
            "INSERT INTO transactions (tx_ref, username, amount, status, payment_method, mobile_money_id) VALUES (?, ?, ?, 'PENDING', 'MANUAL_OM_MOMO', ?)",
            (tx_ref, username, amount, mobile_id)
        )

    def approve_transaction(self, tx_ref):
        """L'Admin valide => Active la licence"""
        # 1. Récupérer infos transaction
        rows = self.execute_read("SELECT username, amount FROM transactions WHERE tx_ref = ?", (tx_ref,))
        if not rows: return False
        username = rows[0]['username']
        
        # 2. Passer en APPROVED
        self.execute_write("UPDATE transactions SET status = 'APPROVED' WHERE tx_ref = ?", (tx_ref,))
        
        # 3. Mettre à jour l'utilisateur (30 jours)
        new_end = datetime.now() + timedelta(days=30)
        self.execute_write("UPDATE users SET license_tier = 'PRO', subscription_end = ? WHERE username = ?", (new_end, username))
        return True

    def reject_transaction(self, tx_ref):
        """L'Admin refuse"""
        self.execute_write("UPDATE transactions SET status = 'REJECTED' WHERE tx_ref = ?", (tx_ref,))

    @classmethod
    def get_instance(cls):
        if cls._instance is None: cls()
        return cls._instance