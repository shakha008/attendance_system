import os
import sqlite3
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. Flask obyektini yaratish (Xatolik kelib chiqmasligi uchun eng tepada bo'lishi shart)
app = Flask(__name__)

# Uploads papkasini sozlash
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS absence_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            reason TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- API STUENTLAR ---

@app.route('/api/students', methods=['GET'])
def get_students():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY full_name ASC').fetchall()
    conn.close()
    return jsonify([dict(student) for student in students])

@app.route('/api/students', methods=['POST'])
def add_student():
    data = request.json
    full_name = data.get('full_name')
    if not full_name:
        return jsonify({"error": "Ism kiritilmadi!"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO students (full_name) VALUES (?)', (full_name,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Talaba qo'shildi!"}), 201

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    data = request.json
    full_name = data.get('full_name')
    if not full_name:
        return jsonify({"error": "Ism kiritilmadi!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE students SET full_name = ? WHERE id = ?', (full_name, student_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Talaba ismi o'zgartirildi!"}), 200

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
    cursor.execute('DELETE FROM attendance WHERE student_id = ?', (student_id,))
    cursor.execute('DELETE FROM absence_reasons WHERE student_id = ?', (student_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Talaba o'chirildi!"}), 200

# --- API DAVOMAT VA SPRAVKA ---

@app.route('/api/attendance', methods=['POST'])
def save_attendance():
    data = request.json
    date = data.get('date')
    records = data.get('records')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    for item in records:
        cursor.execute('''
            SELECT id FROM attendance WHERE student_id = ? AND date = ?
        ''', (item['student_id'], date))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE attendance SET status = ? WHERE id = ?
            ''', (item['status'], existing['id']))
        else:
            cursor.execute('''
                INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)
            ''', (item['student_id'], date, item['status']))
            
    conn.commit()
    conn.close()
    return jsonify({"message": "Davomat saqlandi!"}), 200

@app.route('/api/upload_spravka', methods=['POST'])
def upload_spravka():
    student_id = request.form.get('student_id')
    reason = request.form.get('reason')
    file = request.files.get('file')

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Noto'g'ri fayl formati!"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO absence_reasons (student_id, reason, file_path) VALUES (?, ?, ?)',
        (student_id, reason, filename)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Spravka qabul qilindi!"}), 200

# --- PDF GENERATSIYA VA RASM CHIQARISH ---

@app.route('/api/report/pdf', methods=['GET'])
def generate_pdf():
    pdf_path = "static/davomat_hisobot.pdf"
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=15,
        alignment=1
    )
    story.append(Paragraph("Guruh Davomat va Sababli Qoldirishlar Hisoboti", title_style))
    story.append(Spacer(1, 10))

    conn = get_db_connection()
    records = conn.execute('''
        SELECT 
            s.full_name, 
            a.date, 
            a.status,
            COALESCE((
                SELECT reason 
                FROM absence_reasons r 
                WHERE r.student_id = a.student_id 
                ORDER BY r.id DESC LIMIT 1
            ), 'Sababsiz') as reason,
            (
                SELECT file_path 
                FROM absence_reasons r 
                WHERE r.student_id = a.student_id 
                ORDER BY r.id DESC LIMIT 1
            ) as file_path
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        GROUP BY a.student_id, a.date
        ORDER BY a.date DESC, s.full_name ASC
    ''').fetchall()
    conn.close()

    table_data = [["#", "Talaba Ismi", "Sana", "Holat", "Sababi", "Spravka Rasmi"]]

    for idx, row in enumerate(records, 1):
        status_text = row['status']
        reason_text = row['reason'] if status_text == "Yo'q" else "-"
        
        # Spravka rasmini chiqarish
        img_element = "-"
        if status_text == "Yo'q" and row['file_path']:
            full_img_path = os.path.join(app.config['UPLOAD_FOLDER'], row['file_path'])
            if os.path.exists(full_img_path) and row['file_path'].lower().endswith(('png', 'jpg', 'jpeg')):
                try:
                    img_element = RLImage(full_img_path, width=45, height=45)
                except Exception:
                    img_element = "Rasm fayli"

        table_data.append([
            str(idx),
            row['full_name'],
            row['date'],
            status_text,
            reason_text,
            img_element
        ])

    t = Table(table_data, colWidths=[25, 130, 75, 55, 110, 85])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
    ]))

    story.append(t)
    doc.build(story)

    return send_from_directory('static', 'davomat_hisobot.pdf', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)