# ==============================================================================
# DATABASE.PY - Gestion Base de Données (SaaS Ready & Multi-User Fix)
# Version: 1.1.3 (Lucas Approved)
# ==============================================================================
import sqlite3
import threading
import bcrypt

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
        """Initialise les tables et gère la migration des licences/IP"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 1. Création Table USERS
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password_hash BYTES NOT NULL,
                      role TEXT DEFAULT 'user',
                      license_tier TEXT DEFAULT 'DISCOVERY', -- DISCOVERY, PRO, CORPORATE
                      signup_ip TEXT,                        -- Anti-Abus
                      two_factor_secret TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # 2. Table EQUIPMENT
        c.execute('''CREATE TABLE IF NOT EXISTS equipment
                     (equipment_id TEXT PRIMARY KEY,
                      equipment_name TEXT,
                      profile_base TEXT,
                      power_kw REAL,
                      is_calibrated INTEGER DEFAULT 0,
                      last_calibration TIMESTAMP,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # 3. Table AUDITS (CORRIGÉE : AJOUT created_by)
        c.execute('''CREATE TABLE IF NOT EXISTS audits
                     (audit_uuid TEXT PRIMARY KEY,
                      timestamp TIMESTAMP,
                      created_by TEXT,  -- <--- CORRECTION CRITIQUE (Lien Utilisateur)
                      equipment_id TEXT,
                      materiel_type TEXT,
                      materiel_name TEXT,
                      scenario_code TEXT,
                      index_start REAL,
                      index_end REAL,
                      power_kw REAL,
                      fuel_declared_l REAL,
                      estimated_min REAL,
                      estimated_typ REAL,
                      estimated_max REAL,
                      uncertainty_pct REAL,
                      deviation_pct REAL,
                      z_score REAL,
                      verdict TEXT,
                      confidence_pct INTEGER,
                      validated_by_operator INTEGER)''')

        # 4. Table OVERRIDES (IA)
        c.execute('''CREATE TABLE IF NOT EXISTS equipment_load_overrides
                     (equipment_id TEXT,
                      scenario_code TEXT,
                      load_min REAL,
                      load_typ REAL,
                      load_max REAL,
                      learned_from_n_samples INTEGER,
                      confidence_score REAL,
                      last_updated TIMESTAMP,
                      is_active INTEGER DEFAULT 1,
                      PRIMARY KEY (equipment_id, scenario_code))''')

        # === MIGRATIONS AUTOMATIQUES (Pour ne pas casser la base existante) ===
        try:
            c.execute("SELECT license_tier FROM users LIMIT 1")
        except sqlite3.OperationalError:
            print("MIGRATION : Ajout colonne license_tier...")
            c.execute("ALTER TABLE users ADD COLUMN license_tier TEXT DEFAULT 'DISCOVERY'")
            c.execute("UPDATE users SET license_tier = 'CORPORATE' WHERE role = 'admin'")
            conn.commit()

        try:
            c.execute("SELECT signup_ip FROM users LIMIT 1")
        except sqlite3.OperationalError:
            print("MIGRATION : Ajout colonne signup_ip...")
            c.execute("ALTER TABLE users ADD COLUMN signup_ip TEXT DEFAULT '127.0.0.1'")
            conn.commit()
            
        try:
            c.execute("SELECT created_by FROM audits LIMIT 1")
        except sqlite3.OperationalError:
            print("MIGRATION : Ajout colonne created_by dans audits...")
            c.execute("ALTER TABLE audits ADD COLUMN created_by TEXT")
            # On attribue les anciens audits à l'admin par défaut pour ne pas les perdre
            c.execute("UPDATE audits SET created_by = 'admin' WHERE created_by IS NULL")
            conn.commit()

        # === SEED ADMIN ===
        c.execute("SELECT count(*) FROM users")
        if c.fetchone()[0] == 0:
            pw_hash = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
            c.execute("INSERT INTO users (username, password_hash, role, license_tier, signup_ip) VALUES (?, ?, ?, ?, ?)", 
                      ("admin", pw_hash, "admin", "CORPORATE", "127.0.0.1"))
            conn.commit()
            print("Base initialisée avec Admin (CORPORATE).")

        conn.close()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls()
        return cls._instance