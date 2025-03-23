import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import requests


# Initialize Firebase Admin SDK
firebase_admin.initialize_app()

# Initialize Firestore
db = firestore.client()

app = Flask(__name__)
CORS(app)

# Sign-Up Endpoint
@app.route('/sign-up', methods=['POST'])
def sign_up():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        phone = data.get("phone")
        address = data.get("address")

        if not email or not password or not name or not phone or not address:
            return jsonify({"error": "All fields are required"}), 400

        # Create user in Firebase Authentication
        user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )

        # Save user details in Firestore under 'users' collection
        # Firestore automatically creates the 'users' collection if it doesn't exist
        db.collection('users').document(user.uid).set({
            "UserID": user.uid,  # Add userId to the document
            "name": name,
            "email": email,
            "phone": phone,
            "address": {
                "line1": address.get("line1"),
                "line2": address.get("line2"),
                "city": address.get("city"),
                "state": address.get("state"),
                "zipcode": address.get("zipcode")
            }
        })


        return jsonify({"message": "User created successfully", "userId": user.uid}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Login Endpoint
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Sign in using Firebase Authentication
        # Note: Firebase Admin SDK does not support verifying email/password directly
        # You need to use the Firebase REST API for this
        

        FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY")# Replace with your Firebase Web API Key
        auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        auth_response = requests.post(auth_url, json=payload)
        if auth_response.status_code != 200:
            return jsonify({"error": "Invalid email or password"}), 401

        auth_data = auth_response.json()
        user_id = auth_data["localId"]

        return jsonify({
            "message": "Login successful",
            "userId": user_id,
            "idToken": auth_data["idToken"]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400



# Verify Token (For protected routes)
@app.route('/verify-token', methods=['POST'])
def verify_token():
    try:
        data = request.json
        id_token = data.get("idToken")

        if not id_token:
            return jsonify({"error": "ID token is required"}), 400

        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        return jsonify({"message": "Token is valid", "userId": uid}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401

# if __name__ == '__main__':
    # app.run(debug=True, port=10001)
    
port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port)
