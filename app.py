from flask import Flask, request, jsonify
import os
import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Configure JWT Secret Key (Use a strong, unique key)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "your-secret-key")  
jwt = JWTManager(app)

# Database Connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

# Route: User Signup
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not (username and email and password):
        return jsonify({"error": "All fields are required"}), 400

    hashed_password = generate_password_hash(password)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                       (username, email, hashed_password))
        user_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "User created successfully", "user_id": user_id}), 201
    except psycopg2.Error as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

# Route: User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not (email and password):
        return jsonify({"error": "Both email and password are required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            access_token = create_access_token(identity=user[0])  # Generate JWT Token
            return jsonify({"message": "Login successful", "token": access_token}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except psycopg2.Error as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

# Route: Get Profile (Requires Authentication)
@app.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            return jsonify({
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "created_at": user[3]
            }), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except psycopg2.Error as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

# Route: Update Profile (Requires Authentication)
@app.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.json
    new_username = data.get("username")
    new_email = data.get("email")

    if not (new_username or new_email):
        return jsonify({"error": "Provide at least one field to update"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if new_username:
            cursor.execute("UPDATE users SET username = %s WHERE id = %s", (new_username, user_id))
        if new_email:
            cursor.execute("UPDATE users SET email = %s WHERE id = %s", (new_email, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Profile updated successfully"}), 200
    except psycopg2.Error as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
