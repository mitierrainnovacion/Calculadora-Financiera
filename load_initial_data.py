from firebase_manager import FirebaseManager
from calculadora_financiera import parametros
import sys

def main():
    fm = FirebaseManager()
    
    if not fm.db:
        print("Error: Could not connect to Firebase. Please ensure 'firebase-key.json' exists and 'firebase-admin' is installed.")
        sys.exit(1)

    project_id = "default_project"
    print(f"Uploading default project data to Firebase with ID: {project_id}...")
    
    success = fm.upload_project_data(project_id, parametros)
    
    if success:
        print("Initial data loaded successfully.")
    else:
        print("Failed to load initial data.")

if __name__ == "__main__":
    main()
