import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
import json

class FirebaseManager:
    def __init__(self, key_path='firebase-key.json'):
        self.key_path = key_path
        self.db = None
        self._initialize()

    def _initialize(self):
        if not os.path.exists(self.key_path):
            print(f"Warning: Firebase key file '{self.key_path}' not found.")
            return

        try:
            cred = credentials.Certificate(self.key_path)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print("Firebase initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")

    def upload_project_data(self, project_id, data):
        """
        Uploads project parameters to Firestore.
        """
        if not self.db:
            print("Firestore client not initialized.")
            return False

        try:
            doc_ref = self.db.collection('proyectos').document(project_id)
            doc_ref.set(data)
            print(f"Project '{project_id}' uploaded successfully.")
            return True
        except Exception as e:
            print(f"Error uploading project data: {e}")
            return False

    def get_project_data(self, project_id):
        """
        Fetches project parameters from Firestore.
        """
        if not self.db:
            print("Firestore client not initialized.")
            return None

        try:
            doc_ref = self.db.collection('proyectos').document(project_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                print(f"Project '{project_id}' not found.")
                return None
        except Exception as e:
            print(f"Error fetching project data: {e}")
            return None

if __name__ == "__main__":
    # Example usage / Test
    fm = FirebaseManager()
    # fm.upload_project_data('test_project', {'test': 'data'})
