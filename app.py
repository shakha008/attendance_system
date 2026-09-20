import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_attendance_2026')

# Vercel Environment Variable orqali ulanadigan PostgreSQL bazasi
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        # Agar lokal sinov uchun bo'lsa
        raise Exception("DATABASE_URL sozlanmagan! Vercel Environment Variables bo'limiga qo'shing.")

def init_db():
    if not DATABASE_URL:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role VARCHAR(20) NOT NULL,
            full_name VARCHAR(100) NOT NULL
        );
    ''')
    
    # Talabalar jadvali
    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            group_name VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # Boshlang'ich Admin (Startsa) akkaunti (login: admin, parol: admin123)
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cur.execute("INSERT INTO users (username, password, role, full_name) VALUES (%s, %s, %s, %s)",
                    ('admin', hashed_pw, 'startsa', 'Asosiy Startsa / Admin'))
        
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print("Database init error:", e)

# Authentication Route'lari
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['full_name'] = user['full_name']
                return redirect(url_for('home'))
            else:
                flash("Login yoki parol xato!", "danger")
        except Exception as e:
            flash(f"Baza bilan aloqa xatosi: {str(e)}", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Talabalarni qo'shish (Xavfsiz va umrbod saqlanadigan)
@app.route('/api/students', methods=['GET', 'POST'])
def handle_students():
    if 'user_id' not in session:
        return jsonify({'error': 'Ruxsat berilmadi'}), 403
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        full_name = data.get('full_name')
        group_name = data.get('group_name', '1-guruh')
        
        cur.execute('INSERT INTO students (full_name, group_name) VALUES (%s, %s) RETURNING id', 
                    (full_name, group_name))
        new_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Talaba qo\'shildi', 'id': new_id})
        
    cur.execute('SELECT * FROM students ORDER BY id DESC')
    students = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(students)

if __name__ == '__main__':
    app.run()
