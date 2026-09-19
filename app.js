document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('att-date');
    if (dateInput) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
    loadStudents();
});

let studentsData = [];

async function loadStudents() {
    try {
        const res = await fetch('/api/students');
        studentsData = await res.json();
        
        renderStarsaList();
        renderStudentSelect();
    } catch (err) {
        console.error("Ошибка загрузки студентов:", err);
    }
}

function renderStarsaList() {
    const container = document.getElementById('student-list');
    if (!container) return;
    container.innerHTML = '';

    if (studentsData.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#888;">Студенты не найдены. Добавьте студентов.</p>';
        return;
    }

    studentsData.forEach(student => {
        const div = document.createElement('div');
        div.className = 'student-item';
        div.innerHTML = `
            <span><strong>${student.full_name}</strong></span>
            <div class="student-actions">
                <label>
                    <input type="checkbox" data-id="${student.id}" class="absent-checkbox"> Yo'q
                </label>
                <button class="btn edit" onclick="editStudent(${student.id}, '${student.full_name}')">✏️</button>
                <button class="btn delete" onclick="deleteStudent(${student.id})">🗑️</button>
            </div>
        `;
        container.appendChild(div);
    });
}

async function addStudent() {
    const input = document.getElementById('new-student-name');
    const full_name = input.value.trim();

    if (!full_name) {
        alert("Введите имя и фамилию!");
        return;
    }

    const res = await fetch('/api/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name })
    });

    if (res.ok) {
        input.value = '';
        loadStudents();
    } else {
        alert("Ошибка при добавлении!");
    }
}

async function editStudent(id, currentName) {
    const newName = prompt("Введите новое имя и фамилию:", currentName);
    if (!newName || newName.trim() === '') return;

    const res = await fetch(`/api/students/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: newName.trim() })
    });

    if (res.ok) {
        loadStudents();
    } else {
        alert("Ошибка редактирования!");
    }
}

async function deleteStudent(id) {
    if (!confirm("Вы уверены, что хотите удалить этого студента?")) return;

    const res = await fetch(`/api/students/${id}`, {
        method: 'DELETE'
    });

    if (res.ok) {
        loadStudents();
    } else {
        alert("Ошибка при удалении!");
    }
}

function renderStudentSelect() {
    const select = document.getElementById('student-select');
    if (!select) return;
    select.innerHTML = '<option value="">Выберите студента</option>';
    studentsData.forEach(s => {
        select.innerHTML += `<option value="${s.id}">${s.full_name}</option>`;
    });
}

async function submitAttendance() {
    const date = document.getElementById('att-date').value;
    const checkboxes = document.querySelectorAll('.absent-checkbox');
    
    if (studentsData.length === 0) {
        alert("Сначала добавьте студентов!");
        return;
    }

    const records = [];
    checkboxes.forEach(cb => {
        records.push({
            student_id: cb.dataset.id,
            status: cb.checked ? "Yo'q" : "Bor"
        });
    });

    const res = await fetch('/api/attendance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, records })
    });

    const data = await res.json();
    alert(data.message);
}

async function uploadSpravka(event) {
    event.preventDefault();

    const formData = new FormData();
    formData.append('student_id', document.getElementById('student-select').value);
    formData.append('reason', document.getElementById('reason').value);
    formData.append('file', document.getElementById('spravka-file').files[0]);

    const res = await fetch('/api/upload_spravka', {
        method: 'POST',
        body: formData
    });

    const data = await res.json();
    if (res.ok) {
        alert(data.message);
        document.getElementById('spravka-form').reset();
    } else {
        alert(data.error || "Ошибка при загрузке!");
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    if (event && event.target) {
        event.target.classList.add('active');
    }
    const targetTab = document.getElementById(tabName);
    if (targetTab) {
        targetTab.classList.add('active');
    }
}