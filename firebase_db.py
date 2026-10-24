import os, json, time
import firebase_admin
from firebase_admin import credentials, firestore

# Global firestore client
_firestore_db = None
_using_firebase = False

def init_firebase():
    global _firestore_db, _using_firebase
    if _firestore_db is not None:
        return _firestore_db

    try:
        # Check for service account JSON file or env variable
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(os.path.dirname(__file__), "service-account-key.json")
        cred_json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

        if cred_json_str:
            cred_dict = json.loads(cred_json_str)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _firestore_db = firestore.client()
            _using_firebase = True
            print(">>> Connected to Firebase Firestore using FIREBASE_SERVICE_ACCOUNT_JSON env.")
        elif os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _firestore_db = firestore.client()
            _using_firebase = True
            print(f">>> Connected to Firebase Firestore using {cred_path}")
        else:
            print(">>> Firebase service account key not found. Using local SQLite fallback seamlessly.")
            _using_firebase = False
    except Exception as e:
        print(">>> Firebase initialization error (falling back to SQLite):", e)
        _using_firebase = False

    return _firestore_db

def is_firebase_active():
    return _using_firebase and _firestore_db is not None

def get_db():
    return _firestore_db

