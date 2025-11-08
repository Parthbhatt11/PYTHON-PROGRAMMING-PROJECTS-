# main_modern.py
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import datetime
import textwrap

# --- (Feature 2) Check for tkcalendar ---
try:
    from tkcalendar import DateEntry
    TKCALENDAR_AVAILABLE = True
except Exception:
    TKCALENDAR_AVAILABLE = False
# --------------------------------------

# Optional PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# -------------------- Database Setup --------------------
# Use os.path.abspath to handle running from different directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "hospital.db")

# Create invoices folder
INVOICES_DIR = os.path.join(BASE_DIR, "invoices")
os.makedirs(INVOICES_DIR, exist_ok=True)

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # Users (simple local auth if needed later)
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE, password TEXT, role TEXT
    )''')
    # Doctors
    cur.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialization TEXT,
        phone TEXT,
        email TEXT,
        address TEXT
    )''')
    # Patients
    cur.execute('''CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        contact TEXT,
        address TEXT,
        disease TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # --- Migration for 'address' column in patients ---
    try:
        cur.execute("ALTER TABLE patients ADD COLUMN address TEXT")
    except Exception:
        pass
    
    # Appointments
    cur.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        date TEXT,
        time TEXT,
        purpose TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    )''')
    # Medicines / Inventory
    cur.execute('''CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT,
        price REAL,
        stock INTEGER DEFAULT 0
    )''')
    # Invoices
    cur.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        date TEXT,
        total REAL,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- (Feature 1) Add settings table ---
    cur.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
                ('clinic_name', 'My Clinic Name'))
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
                ('clinic_details', '123 Health St | Wellness City | Contact: 000-000-0000'))

    # --- (Feature 1) Add Services table ---
    cur.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL
    )''')
    cur.execute("INSERT OR IGNORE INTO services (name, price) VALUES ('Consultation', 500.00)")
    cur.execute("INSERT OR IGNORE INTO services (name, price) VALUES ('Follow-up', 250.00)")
    # --- End of update ---

    conn.commit()

    # Add optional columns to patients if they don't exist: blood_group, date_of_admission
    try:
        cur.execute("ALTER TABLE patients ADD COLUMN blood_group TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE patients ADD COLUMN date_of_admission TEXT")
    except Exception:
        pass

    conn.commit()
    conn.close()

init_db()

# -------------------- Utility Functions --------------------
def fetchall(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    conn.close()

def insert_invoice_return_id(patient_id, date, total, details):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO invoices (patient_id, date, total, details) VALUES (?, ?, ?, ?)",
                (patient_id, date, total, details))
    invoice_id = cur.lastrowid
    conn.commit()
    conn.close()
    return invoice_id

# -------------------- GUI Setup --------------------
root = tk.Tk()
root.title("Medical Management System — Modern")
root.geometry("1150x720")
root.minsize(1000, 650)
root.configure(bg="#f3f6fb")

# --- (Feature 2) Check for tkcalendar ---
if not TKCALENDAR_AVAILABLE:
    root.withdraw()
    messagebox.showerror("Missing Library", 
                         "The 'tkcalendar' library is not found.\n\nPlease install it by running:\npip install tkcalendar")
    root.destroy()
    exit()
# ----------------------------------------

# Use ttk style for base widgets
style = ttk.Style()
try:
    style.theme_use('clam')
except Exception:
    pass

style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), foreground="#0f172a")
style.configure("Card.TFrame", background="white", relief="flat")
style.configure("Small.TLabel", font=("Helvetica", 10))
style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))

# Colored sidebar (use tk.Frame for easier coloring)
SIDEBAR_BG = "#0b5ed7"      # bright blue
SIDEBAR_BTN_BG = "#0b66d6"
SIDEBAR_BTN_FG = "white"

sidebar = tk.Frame(root, bg=SIDEBAR_BG, width=220)
sidebar.pack(side="left", fill="y")

content = tk.Frame(root, bg="#f3f6fb")
content.pack(side="left", fill="both", expand=True, padx=18, pady=18)

# Header
header_frame = tk.Frame(content, bg="#f3f6fb")
header_frame.pack(fill="x")
ttk.Label(header_frame, text="Clinic Management", style="Header.TLabel").pack(side="left")
today_lbl = ttk.Label(header_frame, text=datetime.datetime.now().strftime("%b %d, %Y"), style="Small.TLabel")
today_lbl.pack(side="right")

# Card area
card_area = tk.Frame(content, bg="#f3f6fb")
card_area.pack(fill="both", expand=True, pady=(12,0))

def clear_frame(f):
    for widget in f.winfo_children():
        widget.destroy()

# -------------------- Views --------------------

def view_dashboard():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)
    # stats row
    stats_frame = tk.Frame(frame, bg="white")
    stats_frame.pack(fill="x", pady=6)

    def stat_box(title, value, color):
        box = tk.Frame(stats_frame, bg=color, width=220, height=80)
        box.pack(side="left", padx=10, pady=8)
        box.pack_propagate(False)
        ttk.Label(box, text=title, background=color, foreground="white", font=("Helvetica", 10)).pack(anchor="nw", padx=10, pady=8)
        ttk.Label(box, text=str(value), background=color, foreground="white", font=("Helvetica", 16, "bold")).pack(anchor="nw", padx=10)

    patients_count = fetchall("SELECT COUNT(*) FROM patients")[0][0]
    doctors_count = fetchall("SELECT COUNT(*) FROM doctors")[0][0]
    appts_today = fetchall("SELECT COUNT(*) FROM appointments WHERE date=?", (datetime.date.today().isoformat(),))[0][0]
    meds_low = fetchall("SELECT COUNT(*) FROM medicines WHERE stock <= 5")[0][0]

    stat_box("Total Patients", patients_count, "#0ea5e9")    # cyan
    stat_box("Total Doctors", doctors_count, "#34d399")      # green
    stat_box("Appointments Today", appts_today, "#f59e0b")   # amber
    stat_box("Low Stock Medicines", meds_low, "#ef4444")     # red

    # upcoming appointments
    recent = ttk.Frame(frame, padding=8, style="Card.TFrame")
    recent.pack(fill="both", expand=True, pady=12)
    ttk.Label(recent, text="Upcoming Appointments (next 7 days)", font=("Helvetica", 12, "bold")).pack(anchor="w")

    cols = ("ID", "Patient", "Doctor (Spec)", "Date", "Time")
    tree = ttk.Treeview(recent, columns=cols, show="headings", height=8)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center")
    tree.pack(fill="both", expand=True, pady=8)

    rows = fetchall("""
        SELECT a.id,
               COALESCE(p.name, '<Unknown>'),
               COALESCE(d.name || ' — ' || d.specialization, d.name),
               a.date, a.time
        FROM appointments a
        LEFT JOIN patients p ON a.patient_id = p.id
        LEFT JOIN doctors d ON a.doctor_id = d.id
        WHERE date BETWEEN ? AND ?
        ORDER BY a.date, a.time
    """, (datetime.date.today().isoformat(), (datetime.date.today()+datetime.timedelta(days=7)).isoformat()))
    for r in rows:
        tree.insert("", tk.END, values=r)

# Doctors view
def view_doctors():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)
    top = tk.Frame(frame, bg="white")
    top.pack(fill="x")
    ttk.Label(top, text="Doctors", font=("Helvetica", 14, "bold")).pack(side="left")
    tk.Button(top, text="Add Doctor", bg="#10b981", fg="white", bd=0, command=open_add_doctor_window).pack(side="right", padx=8)

    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill="both", expand=True, pady=8)
    
    cols = ("ID", "Name", "Specialization", "Phone", "Email", "Address")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=150, anchor="center")
    tree.pack(fill="both", expand=True)

    for r in fetchall("SELECT id, name, specialization, phone, email, address FROM doctors ORDER BY name"):
        tree.insert("", tk.END, values=r)

    def delete_selected():
        sel = tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select a doctor to delete.")
            return
        did = tree.item(sel)['values'][0]
        if messagebox.askyesno("Confirm", "Delete this doctor?"):
            execute("DELETE FROM doctors WHERE id=?", (did,))
            view_doctors()

    tk.Button(frame, text="Delete Selected", bg="#ef4444", fg="white", bd=0, command=delete_selected).pack(pady=6)

def open_add_doctor_window():
    win = tk.Toplevel(root)
    win.title("Add Doctor")
    win.geometry("460x400") # Made window taller
    win.configure(bg="#f8fafc")
    win.grab_set()
    win.transient(root)
    
    ttk.Label(win, text="Add New Doctor", font=("Helvetica", 12, "bold")).pack(pady=8)
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=6)

    name_var = tk.StringVar()
    spec_var = tk.StringVar()
    phone_var = tk.StringVar()
    email_var = tk.StringVar()
    address_var = tk.StringVar()

    tk.Label(frm, text="Name:", bg="#f8fafc").grid(row=0, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=name_var, width=40).grid(row=0, column=1, pady=6, sticky="w")
    tk.Label(frm, text="Specialization:", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=spec_var, width=40).grid(row=1, column=1, pady=6, sticky="w")
    tk.Label(frm, text="Phone:", bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=phone_var, width=40).grid(row=2, column=1, pady=6, sticky="w")
    
    tk.Label(frm, text="Email:", bg="#f8fafc").grid(row=3, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=email_var, width=40).grid(row=3, column=1, pady=6, sticky="w")
    tk.Label(frm, text="Address:", bg="#f8fafc").grid(row=4, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=address_var, width=40).grid(row=4, column=1, pady=6, sticky="w")


    def save():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Input", "Name is required.", parent=win)
            return
        
        execute("INSERT INTO doctors (name, specialization, phone, email, address) VALUES (?, ?, ?, ?, ?)",
                (name, 
                 spec_var.get().strip(), 
                 phone_var.get().strip(),
                 email_var.get().strip(),
                 address_var.get().strip()
                ))
        win.destroy()
        view_doctors() # Refresh the doctor list

    tk.Button(win, text="Save", bg="#0ea5e9", fg="white", bd=0, command=save, width=12).pack(pady=10)

# Patients view
def view_patients():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)
    top = tk.Frame(frame, bg="white")
    top.pack(fill="x")
    ttk.Label(top, text="Patients", font=("Helvetica", 14, "bold")).pack(side="left")
    tk.Button(top, text="Add Patient", bg="#10b981", fg="white", bd=0, command=open_add_patient_window).pack(side="right", padx=8)

    search_frame = tk.Frame(frame, bg="white")
    search_frame.pack(fill="x", pady=6)
    search_var = tk.StringVar()
    ttk.Entry(search_frame, textvariable=search_var, width=30).pack(side="left", padx=6)
    def on_search():
        q = search_var.get().strip()
        load(q)
    tk.Button(search_frame, text="Search", bg="#0ea5e9", fg="white", bd=0, command=on_search).pack(side="left", padx=4)

    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill="both", expand=True, pady=8)
    
    cols = ("ID", "Name", "Age", "Gender", "Contact", "Address", "Disease")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=140, anchor="center")
    tree.pack(fill="both", expand=True)

    def load(q=""):
        tree.delete(*tree.get_children())
        if q:
            rows = fetchall("""SELECT id, name, age, gender, contact, address, disease FROM patients
                                WHERE name LIKE ? OR contact LIKE ? ORDER BY name""", (f"%{q}%", f"%{q}%"))
        else:
            rows = fetchall("SELECT id, name, age, gender, contact, address, disease FROM patients ORDER BY name")
        for r in rows:
            tree.insert("", tk.END, values=r)

    def delete_sel():
        sel = tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select a patient to delete.")
            return
        pid = tree.item(sel)['values'][0]
        if messagebox.askyesno("Confirm", "Delete this patient and related appointments?"):
            execute("DELETE FROM appointments WHERE patient_id=?", (pid,))
            execute("DELETE FROM patients WHERE id=?", (pid,))
            load()

    def edit_sel():
        sel = tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select a patient to edit.")
            return
        pid = tree.item(sel)['values'][0]
        open_edit_patient(pid, load)

    tk.Button(frame, text="Edit Selected", bg="#f59e0b", fg="white", bd=0, command=edit_sel).pack(side="left", padx=6)
    tk.Button(frame, text="Delete Selected", bg="#ef4444", fg="white", bd=0, command=delete_sel).pack(side="left", padx=6)

    load()


def open_add_patient_window():
    win = tk.Toplevel(root)
    win.title("Add Patient")
    win.geometry("520x620")
    win.configure(bg="#f8fafc")
    win.grab_set() # Make it modal
    win.transient(root) # Keep it on top

    ttk.Label(win, text="Add Patient", font=("Helvetica", 12, "bold")).pack(pady=8)
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=6)

    name_var = tk.StringVar()
    age_var = tk.StringVar()
    gender_var = tk.StringVar()
    contact_var = tk.StringVar()
    address_var = tk.StringVar()
    disease_var = tk.StringVar()
    blood_group_var = tk.StringVar()
    doa_var = tk.StringVar()

    # --- UI Layout ---
    fields = [
        ("Name:", name_var),
        ("Age:", age_var),
        ("Gender:", gender_var),
        ("Contact:", contact_var),
        ("Address:", address_var),
        ("Disease:", disease_var),
        ("Blood Group (optional):", blood_group_var),
        ("Date of Admission (YYYY-MM-DD) (optional):", doa_var)
    ]

    for i, (label_text, var) in enumerate(fields):
        tk.Label(frm, text=label_text, bg="#f8fafc").grid(row=i, column=0, sticky="w", pady=6)
        if label_text == "Gender:":
            ttk.Combobox(frm, textvariable=gender_var, values=["Male","Female","Other"], width=37).grid(row=i, column=1, pady=6, sticky="w")
        
        # --- (Feature 2) Use DateEntry for Date of Admission ---
        elif label_text.startswith("Date of Admission"):
            # show_none=True allows the field to be optional/empty
            de = DateEntry(frm, textvariable=doa_var, width=37, date_pattern='y-mm-dd', 
                            show_none=True, nonevalue="")
            de.grid(row=i, column=1, pady=6, sticky="w")
            doa_var.set("") # Start as empty
        # -------------------------------------------------------
        else:
            ttk.Entry(frm, textvariable=var, width=40).grid(row=i, column=1, pady=6, sticky="w")

    # --- Save Function ---
    def save():
        name = name_var.get().strip()
        contact = contact_var.get().strip()

        if not name:
            messagebox.showwarning("Input", "Name is required", parent=win)
            return

        if contact:
            dup = fetchall("SELECT id FROM patients WHERE name=? AND contact=?", (name, contact))
            if dup:
                messagebox.showwarning("Duplicate", "A patient with same name and contact already exists.", parent=win)
                return

        doa = doa_var.get().strip()
        # --- (Feature 2) Removed date validation, as DateEntry handles it ---
        
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""INSERT INTO patients (name, age, gender, contact, address, disease, blood_group, date_of_admission)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                          (name,
                           int(age_var.get().strip()) if age_var.get().strip().isdigit() else None,
                           gender_var.get().strip() or None,
                           contact or None,
                           address_var.get().strip() or None,
                           disease_var.get().strip() or None,
                           blood_group_var.get().strip() or None,
                           doa or None))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Patient added successfully!", parent=win)
            win.destroy()
            view_patients() # Refresh the patient list
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add patient: {e}", parent=win)

    # --- Save Button ---
    tk.Button(win, text="Save Patient", bg="#0ea5e9", fg="white", bd=0, command=save, width=15).pack(pady=20)


def open_edit_patient(pid, reload_callback=None):
    data = fetchall("SELECT id, name, age, gender, contact, address, disease, blood_group, date_of_admission FROM patients WHERE id=?", (pid,))
    if not data:
        messagebox.showerror("Not found", "Patient not found.")
        return
    
    p = data[0]
    win = tk.Toplevel(root)
    win.title("Edit Patient")
    win.geometry("520x620")
    win.configure(bg="#f8fafc")
    win.grab_set()
    win.transient(root)
    
    ttk.Label(win, text="Edit Patient", font=("Helvetica", 12, "bold")).pack(pady=8)
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=6)

    name_var = tk.StringVar(value=p[1])
    age_var = tk.StringVar(value=str(p[2]) if p[2] else "")
    gender_var = tk.StringVar(value=p[3] or "")
    contact_var = tk.StringVar(value=p[4] or "")
    address_var = tk.StringVar(value=p[5] or "")
    disease_var = tk.StringVar(value=p[6] or "")
    blood_group_var = tk.StringVar(value=p[7] or "")
    doa_var = tk.StringVar(value=p[8] or "") # Set variable first

    # --- UI Layout ---
    fields = [
        ("Name:", name_var),
        ("Age:", age_var),
        ("Gender:", gender_var),
        ("Contact:", contact_var),
        ("Address:", address_var),
        ("Disease:", disease_var),
        ("Blood Group (optional):", blood_group_var),
        ("Date of Admission (YYYY-MM-DD) (optional):", doa_var)
    ]
    
    for i, (label_text, var) in enumerate(fields):
        tk.Label(frm, text=label_text, bg="#f8fafc").grid(row=i, column=0, sticky="w", pady=6)
        if label_text == "Gender:":
             ttk.Combobox(frm, textvariable=gender_var, values=["Male","Female","Other"], width=37).grid(row=i, column=1, pady=6, sticky="w")
        
        # --- (Feature 2) Use DateEntry for Date of Admission ---
        elif label_text.startswith("Date of Admission"):
            de = DateEntry(frm, textvariable=doa_var, width=37, date_pattern='y-mm-dd',
                             show_none=True, nonevalue="")
            de.grid(row=i, column=1, pady=6, sticky="w")
        # -------------------------------------------------------
        else:
            ttk.Entry(frm, textvariable=var, width=40).grid(row=i, column=1, pady=6, sticky="w")

    def update():
        doa = doa_var.get().strip()
        # --- (Feature 2) Removed date validation, as DateEntry handles it ---

        execute("""UPDATE patients SET name=?, age=?, gender=?, contact=?, address=?, disease=?, blood_group=?, date_of_admission=? WHERE id=?""",
                (name_var.get().strip(),
                 int(age_var.get().strip()) if age_var.get().strip().isdigit() else None, 
                 gender_var.get().strip() or None,
                 contact_var.get().strip(),
                 address_var.get().strip(),
                 disease_var.get().strip(),
                 blood_group_var.get().strip() or None,
                 doa or None,
                 pid))
        win.destroy()
        if reload_callback:
            reload_callback()

    tk.Button(win, text="Update", bg="#0ea5e9", fg="white", bd=0, command=update).pack(pady=8)


# Appointments view
def view_appointments():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)
    top = tk.Frame(frame, bg="white")
    top.pack(fill="x")
    ttk.Label(top, text="Appointments", font=("Helvetica", 14, "bold")).pack(side="left")
    tk.Button(top, text="New Appointment", bg="#10b981", fg="white", bd=0, command=open_add_appointment_window).pack(side="right", padx=8)

    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill="both", expand=True, pady=8)
    cols = ("ID", "Patient", "Doctor (Spec)", "Date", "Time", "Purpose")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    rows = fetchall("""SELECT a.id,
                                COALESCE(p.name,'<Unknown>') as patient,
                                COALESCE(d.name || ' — ' || d.specialization, d.name) as doctor,
                                a.date, a.time, a.purpose
                         FROM appointments a
                         LEFT JOIN patients p ON a.patient_id = p.id
                         LEFT JOIN doctors d ON a.doctor_id = d.id
                         ORDER BY a.date, a.time""")
    for r in rows:
        tree.insert("", tk.END, values=r)

    def delete_sel():
        sel = tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select appointment to delete.")
            return
        aid = tree.item(sel)['values'][0]
        if messagebox.askyesno("Confirm", "Delete appointment?"):
            execute("DELETE FROM appointments WHERE id=?", (aid,))
            view_appointments()

    tk.Button(frame, text="Delete Selected", bg="#ef4444", fg="white", bd=0, command=delete_sel).pack(pady=6)
    
    # --- (Feature 1) Enabled "Generate Invoice" button ---
    tk.Button(frame, text="Generate Invoice for Selected", bg="#0ea5e9", fg="white", bd=0, command=lambda: generate_invoice_for_selected(tree)).pack(pady=6)


# --- (Feature 1) Updated function to call the new billing window ---
def generate_invoice_for_selected(tree):
    sel = tree.focus()
    if not sel:
        messagebox.showwarning("Select", "Select appointment to generate invoice.")
        return
    aid = tree.item(sel)['values'][0]
    
    data = fetchall("""SELECT a.id, a.patient_id, p.name AS patient_name
                       FROM appointments a
                       LEFT JOIN patients p ON a.patient_id = p.id
                       WHERE a.id = ?""", (aid,))
    if not data:
        messagebox.showerror("Error", "Appointment not found.")
        return
    ap = data[0]
    # Pass patient_id and patient_name to the new billing window
    open_billing_window(patient_id=ap[1], patient_name=ap[2] or "Unknown")


def open_add_appointment_window():
    win = tk.Toplevel(root)
    win.title("New Appointment")
    win.geometry("580x420")
    win.configure(bg="#f8fafc")
    win.grab_set()
    win.transient(root)

    ttk.Label(win, text="Book Appointment", font=("Helvetica", 12, "bold")).pack(pady=8)
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=6)

    patients = fetchall("SELECT id, name FROM patients ORDER BY name")
    doctors = fetchall("SELECT id, name, specialization FROM doctors ORDER BY name")

    patient_map = {f"{p[1]} (#{p[0]})": p[0] for p in patients}
    doctor_map = {f"{d[1]} — {d[2]} (#{d[0]})" if d[2] else f"{d[1]} (#{d[0]})": d[0] for d in doctors}

    patient_var = tk.StringVar()
    doctor_var = tk.StringVar()
    # date_var is removed, handled by DateEntry
    time_var = tk.StringVar()
    purpose_var = tk.StringVar()

    tk.Label(frm, text="Patient:", bg="#f8fafc").grid(row=0, column=0, sticky="w", pady=6)
    pcb = ttk.Combobox(frm, values=list(patient_map.keys()), textvariable=patient_var, width=44)
    pcb.grid(row=0, column=1, pady=6, sticky="w")
    
    tk.Label(frm, text="Doctor:", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=6)
    dcb = ttk.Combobox(frm, values=list(doctor_map.keys()), textvariable=doctor_var, width=44)
    dcb.grid(row=1, column=1, pady=6, sticky="w")
    
    # --- (Feature 2) Replaced Entry with DateEntry ---
    tk.Label(frm, text="Date:", bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=6)
    date_entry = DateEntry(frm, width=41, date_pattern='y-mm-dd')
    date_entry.grid(row=2, column=1, pady=6, sticky="w")
    # -----------------------------------------------
    
    # --- (Feature 5) Replaced Entry with Combobox for Time ---
    tk.Label(frm, text="Time:", bg="#f8fafc").grid(row=3, column=0, sticky="w", pady=6)
    # Generate times from 8:00 AM to 7:30 PM
    times = [f"{h:02d}:{m:02d}" for h in range(8, 20) for m in (0, 30)]
    time_cb = ttk.Combobox(frm, values=times, textvariable=time_var, width=41)
    time_cb.grid(row=3, column=1, pady=6, sticky="w")
    # ----------------------------------------------------

    tk.Label(frm, text="Purpose:", bg="#f8fafc").grid(row=4, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=purpose_var, width=44).grid(row=4, column=1, pady=6, sticky="w")

    def save():
        pkey = patient_map.get(patient_var.get())
        dkey = doctor_map.get(doctor_var.get())
        date = date_entry.get() # Get from DateEntry
        time = time_var.get().strip()
        
        if not pkey or not dkey or not date or not time:
            messagebox.showwarning("Input", "Fill all fields.", parent=win)
            return
        
        # --- (Feature 5) Prevent Appointment Conflicts ---
        conflict = fetchall("SELECT COUNT(*) FROM appointments WHERE doctor_id = ? AND date = ? AND time = ?",
                             (dkey, date, time))
        
        if conflict and conflict[0][0] > 0:
            messagebox.showwarning("Conflict", 
                                  "This doctor already has an appointment at this date and time.", 
                                  parent=win)
            return
        # ------------------------------------------------
        
        # --- (Feature 2) Removed old date/time validation ---
        execute("""INSERT INTO appointments (patient_id, doctor_id, date, time, purpose)
                     VALUES (?, ?, ?, ?, ?)""", (pkey, dkey, date, time, purpose_var.get().strip()))
        win.destroy()
        view_appointments() # Refresh main list
        view_dashboard()    # Refresh dashboard stats

    tk.Button(win, text="Save", bg="#0ea5e9", fg="white", bd=0, command=save).pack(pady=8)

# ----- Medicines / Pharmacy -----
def view_medicines():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)

    top = ttk.Frame(frame)
    top.pack(fill="x")
    ttk.Label(top, text="Medicines / Inventory", font=("Helvetica", 14, "bold")).pack(side="left")
    tk.Button(top, text="Add Medicine", bg="#10b981", fg="white", bd=0, command=open_add_medicine_window).pack(side="right")

    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill="both", expand=True, pady=8)

    cols = ("ID", "Name", "SKU", "Price", "Stock")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    for r in fetchall("SELECT id, name, sku, price, stock FROM medicines ORDER BY name"):
        tree.insert("", tk.END, values=r)

    def delete_sel():
        sel = tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select medicine to delete.")
            return
        mid = tree.item(sel)['values'][0]
        if messagebox.askyesno("Confirm", "Delete medicine?"):
            execute("DELETE FROM medicines WHERE id=?", (mid,))
            view_medicines()
    tk.Button(frame, text="Delete Selected", bg="#ef4444", fg="white", bd=0, command=delete_sel).pack(pady=6)
    tk.Button(frame, text="Sell / Invoice", bg="#0ea5e9", fg="white", bd=0, command=open_sell_medicine_window).pack(pady=6)

def open_add_medicine_window():
    win = tk.Toplevel(root)
    win.title("Add Medicine")
    win.geometry("420x300")
    win.configure(bg="#f8fafc")
    win.grab_set()
    win.transient(root)
    
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=8)

    name_var = tk.StringVar()
    sku_var = tk.StringVar()
    price_var = tk.StringVar()
    stock_var = tk.StringVar()

    tk.Label(frm, text="Name:", bg="#f8fafc").grid(row=0, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=name_var, width=40).grid(row=0, column=1, pady=6, sticky="w")
    tk.Label(frm, text="SKU:", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=sku_var, width=40).grid(row=1, column=1, pady=6, sticky="w")
    tk.Label(frm, text="Price:", bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=price_var, width=40).grid(row=2, column=1, pady=6, sticky="w")
    tk.Label(frm, text="Stock:", bg="#f8fafc").grid(row=3, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=stock_var, width=40).grid(row=3, column=1, pady=6, sticky="w")

    def save():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Input", "Name required.", parent=win)
            return
        try:
            price = float(price_var.get()) if price_var.get() else 0.0
            stock = int(stock_var.get()) if stock_var.get().isdigit() else 0
        except ValueError:
            messagebox.showwarning("Input", "Price and Stock must be valid numbers.", parent=win)
            return

        execute("INSERT INTO medicines (name, sku, price, stock) VALUES (?, ?, ?, ?)",
                (name, sku_var.get().strip(), price, stock))
        win.destroy()
        view_medicines()

    tk.Button(win, text="Save", bg="#0ea5e9", fg="white", bd=0, command=save).pack(pady=10)


def open_sell_medicine_window():
    win = tk.Toplevel(root)
    win.title("Sell Medicines / Create Invoice")
    win.geometry("760x520") # Window size is fine with new layout
    win.configure(bg="#f8fafc")
    win.grab_set()
    win.transient(root)
    
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=8)

    # --- Row 0: Patient ---
    tk.Label(frm, text="Select Patient", bg="#f8fafc").grid(row=0, column=0, sticky="w", pady=6)
    patients = fetchall("SELECT id, name FROM patients ORDER BY name")
    patient_map = {f"{p[1]} (#{p[0]})":p[0] for p in patients}
    patient_var = tk.StringVar()
    ttk.Combobox(frm, values=list(patient_map.keys()), textvariable=patient_var, width=44).grid(row=0, column=1, pady=6, sticky="w", columnspan=2)

    # --- Row 1: Medicine ---
    tk.Label(frm, text="Medicines", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=6)
    meds = fetchall("SELECT id, name, price, stock FROM medicines ORDER BY name")
    
    med_map = {f"{m[1]} — Rs.{m[2]} (stock:{m[3]}) (#{m[0]})": (m[0], m[2], m[3]) for m in meds}
    med_var = tk.StringVar()
    
    med_cb = ttk.Combobox(frm, values=list(med_map.keys()), textvariable=med_var, width=44)
    med_cb.grid(row=1, column=1, pady=6, sticky="w", columnspan=2)

    # --- Row 2: Qty and Add Button (NEW LAYOUT) ---
    qty_var = tk.StringVar(value="1")
    tk.Label(frm, text="Qty", bg="#f8fafc").grid(row=2, column=0, sticky="w", padx=6, pady=6)
    ttk.Entry(frm, textvariable=qty_var, width=8).grid(row=2, column=1, sticky="w", pady=6)
    
    add_item_btn = tk.Button(frm, text="Add Item", bg="#0ea5e9", fg="white", bd=0)
    add_item_btn.grid(row=2, column=2, padx=6, pady=6, sticky="w")

    # --- Row 3: Invoice Items Treeview ---
    invoice_items = []
    items_frame = ttk.Frame(frm)
    items_frame.grid(row=3, column=0, columnspan=3, pady=8, sticky="ew")
    items_frame.columnconfigure(0, weight=1)

    tree = ttk.Treeview(items_frame, columns=("Name", "Qty", "Price", "Total"), show="headings")
    for c in ("Name","Qty","Price","Total"):
        tree.heading(c, text=c)
        tree.column(c, anchor="center")
    tree.pack(fill="both", expand=True)

    # --- Add Item Logic ---
    def add_item():
        key = med_var.get()
        if not key or key not in med_map:
            messagebox.showwarning("Select", "Select medicine.", parent=win)
            return
        mid, price, stock = med_map[key]
        
        try:
            qty = int(qty_var.get() or 0)
        except ValueError:
            messagebox.showwarning("Qty", "Enter valid quantity.", parent=win)
            return

        if qty <= 0:
            messagebox.showwarning("Qty", "Enter valid quantity.", parent=win)
            return
        
        for i, item_tuple in enumerate(invoice_items):
            if item_tuple[0] == 'medicine' and item_tuple[1] == mid: # Check type and id
                new_qty = item_tuple[3] + qty
                if new_qty > stock:
                    messagebox.showwarning("Stock", f"Only {stock} units available (you have {item_tuple[3]} in cart).", parent=win)
                    return
                new_total = new_qty * price
                invoice_items[i] = ('medicine', mid, item_tuple[2], new_qty, price, new_total)
                tree_item_id = tree.get_children()[i]
                tree.item(tree_item_id, values=(item_tuple[2], new_qty, f"{price:.2f}", f"{new_total:.2f}"))
                return

        if qty > stock:
            messagebox.showwarning("Stock", f"Only {stock} units available.", parent=win)
            return
        
        name = key.split(" — ")[0]
        total = price * qty
        # --- (Feature 1) Added 'medicine' type to item tuple ---
        invoice_items.append(('medicine', mid, name, qty, price, total))
        tree.insert("", tk.END, values=(name, qty, f"{price:.2f}", f"{total:.2f}"))

    add_item_btn.configure(command=add_item)

    # --- Remove Item Logic ---
    def remove_item():
        sel = tree.focus()
        if not sel:
            return
        idx = tree.index(sel)
        tree.delete(sel)
        invoice_items.pop(idx)

    tk.Button(frm, text="Remove Selected Item", bg="#ef4444", fg="white", bd=0, command=remove_item).grid(row=4, column=0, padx=6, pady=6, sticky="w")

    # --- Finalize Logic ---
    def finalize_invoice():
        if not patient_var.get():
            messagebox.showwarning("Patient", "Select patient.", parent=win)
            return
        if not invoice_items:
            messagebox.showwarning("Items", "Add items.", parent=win)
            return
        pid = patient_map[patient_var.get()]
        total = sum(i[5] for i in invoice_items) # Index 5 is total
        # --- (Feature 1) Updated details to get correct indices ---
        details = ";".join([f"{i[2]}|{i[3]}|{i[4]}" for i in invoice_items]) # Name|Qty|Price
        
        inv_id = insert_invoice_return_id(pid, datetime.date.today().isoformat(), total, details)
        
        # --- (Feature 1) Only deduct stock for 'medicine' items ---
        for item in invoice_items:
            if item[0] == 'medicine':
                mid, _, _, qty, _, _ = item
                execute("UPDATE medicines SET stock = stock - ? WHERE id=?", (qty, mid))
        
        messagebox.showinfo("Invoice", f"Invoice saved. Total: {total:.2f}", parent=win)
        
        if REPORTLAB_AVAILABLE:
            try:
                create_invoice_pdf(inv_id)
                messagebox.showinfo("PDF", f"PDF invoice created at: {os.path.join(INVOICES_DIR, f'invoice_{inv_id}.pdf')}", parent=win)
            except Exception as e:
                messagebox.showerror("PDF Error", f"Could not generate PDF: {e}", parent=win)
        else:
            messagebox.showwarning("ReportLab", "ReportLab not found — install with 'pip install reportlab' to export PDF.", parent=win)
        
        win.destroy()
        view_medicines() 
        view_dashboard() 

    tk.Button(frm, text="Finalize Invoice & Save", bg="#10b981", fg="white", bd=0, command=finalize_invoice).grid(row=5, column=0, columnspan=3, pady=12)


# Invoices view
def view_invoices():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Invoices", font=("Helvetica", 14, "bold")).pack(anchor="w")

    cols = ("ID", "Patient", "Date", "Total")
    
    # Use selectmode="extended" to allow multi-select
    tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="extended")
    
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=150, anchor="center")
    tree.pack(fill="both", expand=True, pady=8)
    
    rows = fetchall("""SELECT i.id, p.name, i.date, i.total FROM invoices i
                        LEFT JOIN patients p ON i.patient_id = p.id ORDER BY i.created_at DESC""")
    for r in rows:
        tree.insert("", tk.END, values=r)

    def open_pdf():
        sel = tree.selection() # Get all selected items
        if not sel:
            messagebox.showwarning("Select", "Select one or more invoices to export.")
            return
            
        if not REPORTLAB_AVAILABLE:
            messagebox.showwarning("ReportLab", "ReportLab not installed. Cannot export PDF.")
            return

        if len(sel) == 1:
            # If only one, open it
            iid = tree.item(sel[0])['values'][0]
            try:
                create_invoice_pdf(iid, open_after=True)
                messagebox.showinfo("PDF", f"Invoice {iid} generated and opened.")
            except Exception as e:
                messagebox.showerror("PDF Error", f"Could not generate PDF: {e}")
        else:
            # If multiple, just generate them
            try:
                for item_id in sel:
                    iid = tree.item(item_id)['values'][0]
                    create_invoice_pdf(iid, open_after=False) # Generate without opening
                messagebox.showinfo("PDF", f"{len(sel)} invoices generated successfully in the 'invoices' folder.")
            except Exception as e:
                messagebox.showerror("PDF Error", f"Could not generate all PDFs: {e}")

    def delete_sel_invoice():
        sel = tree.selection() # Use .selection() for multiple items
        if not sel:
            messagebox.showwarning("Select", "Select one or more invoices to delete.")
            return
        
        # Confirmation message for multiple items
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete {len(sel)} invoice(s)?\n\nThis action cannot be undone and will not restock items."):
            conn = get_conn() # Get one connection
            cur = conn.cursor()
            try:
                for item_id in sel:
                    iid = tree.item(item_id)['values'][0]
                    cur.execute("DELETE FROM invoices WHERE id=?", (iid,))
                conn.commit() # Commit all changes at once
                messagebox.showinfo("Success", f"{len(sel)} invoice(s) have been deleted.")
                view_invoices() # Refresh the list
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Failed to delete invoices: {e}")
            finally:
                conn.close() # Close the connection

    # --- Button Frame (This is the ONLY part that creates buttons) ---
    btn_frame = tk.Frame(frame, bg="white")
    btn_frame.pack(pady=6)

    tk.Button(btn_frame, text="Export Selected to PDF", bg="#0ea5e9", fg="white", bd=0, command=open_pdf).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Delete Selected", bg="#ef4444", fg="white", bd=0, command=delete_sel_invoice).pack(side="left", padx=5)

    # --- (REMOVED REDUNDANT BUTTON FRAME AND FUNCTIONS) ---


# --- (Feature 1) NEW: View for managing services ---
def view_services():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)

    top = ttk.Frame(frame)
    top.pack(fill="x")
    ttk.Label(top, text="Services", font=("Helvetica", 14, "bold")).pack(side="left")
    tk.Button(top, text="Add Service", bg="#10b981", fg="white", bd=0, command=open_add_service_window).pack(side="right")

    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill="both", expand=True, pady=8)

    cols = ("ID", "Name", "Price")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    for r in fetchall("SELECT id, name, price FROM services ORDER BY name"):
        tree.insert("", tk.END, values=r)

    def delete_sel():
        sel = tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select service to delete.")
            return
        sid = tree.item(sel)['values'][0]
        if messagebox.askyesno("Confirm", "Delete service?"):
            execute("DELETE FROM services WHERE id=?", (sid,))
            view_services()
    tk.Button(frame, text="Delete Selected", bg="#ef4444", fg="white", bd=0, command=delete_sel).pack(pady=6)

# --- (Feature 1) NEW: Window to add a service ---
def open_add_service_window():
    win = tk.Toplevel(root)
    win.title("Add Service")
    win.geometry("420x200")
    win.configure(bg="#f8fafc")
    win.grab_set()
    win.transient(root)
    
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=8)

    name_var = tk.StringVar()
    price_var = tk.StringVar()

    tk.Label(frm, text="Name:", bg="#f8fafc").grid(row=0, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=name_var, width=40).grid(row=0, column=1, pady=6, sticky="w")
    tk.Label(frm, text="Price:", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=price_var, width=40).grid(row=1, column=1, pady=6, sticky="w")

    def save():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Input", "Name required.", parent=win)
            return
        try:
            price = float(price_var.get()) if price_var.get() else 0.0
        except ValueError:
            messagebox.showwarning("Input", "Price must be a valid number.", parent=win)
            return

        execute("INSERT INTO services (name, price) VALUES (?, ?)", (name, price))
        win.destroy()
        view_services()

    tk.Button(win, text="Save", bg="#0ea5e9", fg="white", bd=0, command=save).pack(pady=10)


# --- (Feature 1) NEW: Billing window for appointments ---
def open_billing_window(patient_id, patient_name):
    win = tk.Toplevel(root)
    win.title("Create Invoice")
    win.geometry("800x600")
    win.configure(bg="#f8fafc")
    win.grab_set()
    win.transient(root)
    
    frm = tk.Frame(win, bg="#f8fafc")
    frm.pack(fill="both", expand=True, padx=12, pady=8)

    # Patient Info
    tk.Label(frm, text="Patient:", bg="#f8fafc", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", pady=6)
    tk.Label(frm, text=f"{patient_name} (ID: {patient_id})", bg="#f8fafc", font=("Helvetica", 10)).grid(row=0, column=1, sticky="w", pady=6)

    # --- Add Services ---
    tk.Label(frm, text="Add Service:", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=6)
    services = fetchall("SELECT id, name, price FROM services ORDER BY name")
    service_map = {f"{s[1]} — Rs.{s[2]}": (s[0], s[1], s[2]) for s in services}
    service_var = tk.StringVar()
    ttk.Combobox(frm, values=list(service_map.keys()), textvariable=service_var, width=44).grid(row=1, column=1, pady=6, sticky="w")
    add_service_btn = tk.Button(frm, text="Add Service", bg="#0ea5e9", fg="white", bd=0)
    add_service_btn.grid(row=1, column=2, padx=6)

    # --- Add Medicines ---
    tk.Label(frm, text="Add Medicine:", bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=6)
    meds = fetchall("SELECT id, name, price, stock FROM medicines ORDER BY name")
    med_map = {f"{m[1]} — Rs.{m[2]} (stock:{m[3]})": (m[0], m[2], m[3]) for m in meds}
    med_var = tk.StringVar()
    ttk.Combobox(frm, values=list(med_map.keys()), textvariable=med_var, width=44).grid(row=2, column=1, pady=6, sticky="w")
    
    tk.Label(frm, text="Qty:", bg="#f8fafc").grid(row=2, column=2, sticky="e", padx=4)
    qty_var = tk.StringVar(value="1")
    ttk.Entry(frm, textvariable=qty_var, width=5).grid(row=2, column=3, sticky="w")
    add_med_btn = tk.Button(frm, text="Add Medicine", bg="#0ea5e9", fg="white", bd=0)
    add_med_btn.grid(row=2, column=4, padx=6)

    # --- Invoice Items Treeview ---
    invoice_items = []
    items_frame = ttk.Frame(frm)
    items_frame.grid(row=3, column=0, columnspan=5, pady=8, sticky="ew")
    frm.columnconfigure(0, weight=1) # Allow frame to expand

    tree = ttk.Treeview(items_frame, columns=("Name", "Qty", "Price", "Total"), show="headings")
    for c in ("Name","Qty","Price","Total"):
        tree.heading(c, text=c)
        tree.column(c, anchor="center")
    tree.pack(fill="both", expand=True)

    # --- Logic for adding service ---
    def add_service_item():
        key = service_var.get()
        if not key or key not in service_map:
            messagebox.showwarning("Select", "Select a service.", parent=win)
            return
        
        sid, name, price = service_map[key]
        
        # Check if service is already in list
        for i, item_tuple in enumerate(invoice_items):
            if item_tuple[0] == 'service' and item_tuple[1] == sid:
                messagebox.showwarning("Duplicate", "This service is already in the invoice.", parent=win)
                return
        
        # Add to list and tree
        # Format: (type, id, name, qty, price_per_unit, total_price)
        invoice_items.append(('service', sid, name, 1, price, price))
        tree.insert("", tk.END, values=(name, 1, f"{price:.2f}", f"{price:.2f}"))
        service_var.set('')

    # --- Logic for adding medicine ---
    def add_medicine_item():
        key = med_var.get()
        if not key or key not in med_map:
            messagebox.showwarning("Select", "Select medicine.", parent=win)
            return
        mid, price, stock = med_map[key]
        
        try:
            qty = int(qty_var.get() or 0)
        except ValueError:
            messagebox.showwarning("Qty", "Enter valid quantity.", parent=win)
            return

        if qty <= 0:
            messagebox.showwarning("Qty", "Enter valid quantity.", parent=win)
            return
        
        # Check if item is already in the list
        for i, item_tuple in enumerate(invoice_items):
            if item_tuple[0] == 'medicine' and item_tuple[1] == mid:
                new_qty = item_tuple[3] + qty
                if new_qty > stock:
                    messagebox.showwarning("Stock", f"Only {stock} units available (you have {item_tuple[3]} in cart).", parent=win)
                    return
                new_total = new_qty * price
                invoice_items[i] = ('medicine', mid, item_tuple[2], new_qty, price, new_total)
                tree_item_id = tree.get_children()[i]
                tree.item(tree_item_id, values=(item_tuple[2], new_qty, f"{price:.2f}", f"{new_total:.2f}"))
                med_var.set('')
                qty_var.set('1')
                return

        if qty > stock:
            messagebox.showwarning("Stock", f"Only {stock} units available.", parent=win)
            return
        
        name = key.split(" — ")[0]
        total = price * qty
        invoice_items.append(('medicine', mid, name, qty, price, total))
        tree.insert("", tk.END, values=(name, qty, f"{price:.2f}", f"{total:.2f}"))
        med_var.set('')
        qty_var.set('1')

    add_service_btn.configure(command=add_service_item)
    add_med_btn.configure(command=add_medicine_item)

    # --- Remove Item Logic ---
    def remove_item():
        sel = tree.focus()
        if not sel:
            return
        idx = tree.index(sel)
        tree.delete(sel)
        invoice_items.pop(idx)

    tk.Button(frm, text="Remove Selected Item", bg="#ef4444", fg="white", bd=0, command=remove_item).grid(row=4, column=0, pady=6, sticky="w")

    # --- Finalize Logic ---
    def finalize_invoice():
        if not invoice_items:
            messagebox.showwarning("Items", "Add items to the invoice.", parent=win)
            return
        
        pid = patient_id
        total = sum(i[5] for i in invoice_items) # Index 5 is total_price
        details = ";".join([f"{i[2]}|{i[3]}|{i[4]}" for i in invoice_items]) # Name|Qty|Price
        
        inv_id = insert_invoice_return_id(pid, datetime.date.today().isoformat(), total, details)
        
        for item in invoice_items:
            if item[0] == 'medicine':
                mid, _, _, qty, _, _ = item
                execute("UPDATE medicines SET stock = stock - ? WHERE id=?", (qty, mid))
        
        messagebox.showinfo("Invoice", f"Invoice saved. Total: {total:.2f}", parent=win)
        
        if REPORTLAB_AVAILABLE:
            try:
                create_invoice_pdf(inv_id)
                messagebox.showinfo("PDF", f"PDF invoice created at: {os.path.join(INVOICES_DIR, f'invoice_{inv_id}.pdf')}", parent=win)
            except Exception as e:
                messagebox.showerror("PDF Error", f"Could not generate PDF: {e}", parent=win)
        else:
            messagebox.showwarning("ReportLab", "ReportLab not found — install with 'pip install reportlab' to export PDF.", parent=win)
        
        win.destroy()
        view_medicines() # Refresh stock
        view_dashboard() # Refresh low stock
        view_invoices() # Refresh invoice list

    tk.Button(frm, text="Finalize Invoice & Save", bg="#10b981", fg="white", bd=0, font=("Helvetica", 10, "bold"), command=finalize_invoice).grid(row=5, column=0, columnspan=5, pady=12)


# --- Settings View ---
def view_settings():
    clear_frame(card_area)
    frame = ttk.Frame(card_area, padding=12, style="Card.TFrame")
    frame.pack(fill="both", expand=True)
    
    ttk.Label(frame, text="Clinic Settings", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=6)

    form_frame = tk.Frame(frame, bg="white")
    form_frame.pack(fill="x", pady=10)

    name_var = tk.StringVar()
    details_var = tk.StringVar()

    try:
        rows = fetchall("SELECT key, value FROM settings")
        settings = dict(rows)
        name_var.set(settings.get('clinic_name', ''))
        details_var.set(settings.get('clinic_details', ''))
    except Exception as e:
        messagebox.showerror("Error", f"Could not load settings: {e}")

    tk.Label(form_frame, text="Clinic Name:", bg="white", font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=8)
    ttk.Entry(form_frame, textvariable=name_var, width=60).grid(row=0, column=1, sticky="w", padx=10, pady=8)

    tk.Label(form_frame, text="Clinic Details:", bg="white", font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=8)
    ttk.Entry(form_frame, textvariable=details_var, width=60).grid(row=1, column=1, sticky="w", padx=10, pady=8)
    
    tk.Label(form_frame, text="(e.g., 123 Main St | Your City | Contact: 555-1234)", bg="white", font=("Helvetica", 8, "italic")).grid(row=2, column=1, sticky="w", padx=10)

    def save_settings():
        try:
            execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                    ('clinic_name', name_var.get().strip()))
            execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                    ('clinic_details', details_var.get().strip()))
            messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    tk.Button(frame, text="Save Settings", bg="#0ea5e9", fg="white", bd=0, command=save_settings, font=("Helvetica", 10, "bold")).pack(pady=20)


def create_invoice_pdf(invoice_id, open_after=False):
    inv = fetchall("SELECT id, patient_id, date, total, details, created_at FROM invoices WHERE id=?", (invoice_id,))
    if not inv:
        return
    inv = inv[0]
    pid = inv[1]
    patient_row = fetchall("SELECT name, contact, address, blood_group FROM patients WHERE id=?", (pid,))
    if patient_row:
        patient_name = patient_row[0][0] or ""
        patient_contact = patient_row[0][1] or ""
        patient_address = patient_row[0][2] or ""
        patient_bg = patient_row[0][3] or ""
    else:
        patient_name = "<Patient Not Found>"
        patient_contact = ""
        patient_address = ""
        patient_bg = ""

    # Try to find a doctor for this invoice by scanning related appointment (best effort)
    appt = fetchall("SELECT doctor_id FROM appointments WHERE patient_id = ? ORDER BY date DESC LIMIT 1", (pid,))
    doctor_name = ""
    doctor_spec = ""
    doctor_phone = ""
    if appt:
        did = appt[0][0]
        if did:
            drow = fetchall("SELECT name, specialization, phone FROM doctors WHERE id=?", (did,))
            if drow:
                doctor_name = drow[0][0] or ""
                doctor_spec = drow[0][1] or ""
                doctor_phone = drow[0][2] or ""

    filename = os.path.join(INVOICES_DIR, f"invoice_{invoice_id}.pdf")
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    margin_left = 40
    margin_right = width - 40
    margin_top = height - 40
    margin_bottom = 40

    try:
        rows = fetchall("SELECT key, value FROM settings")
        settings = dict(rows)
        clinic_name = settings.get('clinic_name', 'Clinic / Hospital Name')
        clinic_details = settings.get('clinic_details', 'Address line 1 | Contact: 0000-000-000')
    except Exception:
        clinic_name = 'Clinic / Hospital Name'
        clinic_details = 'Address line 1 | Contact: 0000-000-000'


    # --- Header ---
    header_height = 60
    c.setFillColorRGB(11/255, 94/255, 215/255)
    c.rect(0, height - header_height, width, header_height, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(margin_left, height - 40, clinic_name)
    c.setFont("Helvetica", 10)
    c.drawString(margin_left, height - 55, clinic_details)

    # --- Invoice Metadata ---
    c.setFillColorRGB(0,0,0)
    y = height - header_height - 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_left, y, f"Invoice ID: {invoice_id}")
    
    c.setFont("Helvetica", 10)

    now = datetime.datetime.now()
    invoice_date_str = now.strftime("%Y-%m-%d")
    generated_time_str = now.strftime("%H:%M:%S") # Current system time

    c.drawRightString(margin_right, y, f"Date: {invoice_date_str}")
    y -= 15
    c.drawRightString(margin_right, y, f"Generated Time: {generated_time_str}")

    # --- Patient & Doctor Info ---
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "Patient:")
    c.setFont("Helvetica", 10)
    c.drawString(margin_left + 80, y, f"{patient_name}  |  Contact: {patient_contact}")
    y -= 15
    
    if patient_address:
        wrapped_address = textwrap.wrap(f"Address: {patient_address}", width=80)
        for line in wrapped_address:
            c.drawString(margin_left + 80, y, line)
            y -= 15
    
    if patient_bg:
        c.drawString(margin_left + 80, y, f"Blood Group: {patient_bg}")
        y -= 15

    y -= 5 # Extra padding
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "Doctor:")
    c.setFont("Helvetica", 10)
    c.drawString(margin_left + 80, y, f"{doctor_name}  |  {doctor_spec}  |  {doctor_phone}")
    y -= 25

    # --- Table Headers ---
    col_item = margin_left
    col_total = margin_right
    col_price = col_total - 80
    col_qty = col_price - 60
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col_item, y, "Item")
    c.drawRightString(col_qty, y, "Qty")
    c.drawRightString(col_price, y, "Price")
    c.drawRightString(col_total, y, "Total")
    y -= 12
    c.line(margin_left, y, margin_right, y)
    y -= 8

    # --- Items ---
    details = inv[4] or ""
    total_calc = 0.0
    if details:
        lines = details.split(";")
        for line in lines:
            y -= 16 
            if y < margin_bottom: 
                c.showPage()
                # Redraw headers on new page
                c.setFont("Helvetica-Bold", 10)
                y = margin_top - 20 
                c.drawString(col_item, y, "Item")
                c.drawRightString(col_qty, y, "Qty")
                c.drawRightString(col_price, y, "Price")
                c.drawRightString(col_total, y, "Total")
                y -= 12
                c.line(margin_left, y, margin_right, y)
                y -= 8
                
            try:
                name, qty, price = line.split("|")
                qtyn = int(qty)
                pricen = float(price)
                total_item = qtyn * pricen
                c.setFont("Helvetica", 10)
                
                c.drawString(col_item, y, str(name)[:60]) 
                c.drawRightString(col_qty, y, str(qtyn))
                c.drawRightString(col_price, y, f"Rs. {pricen:.2f}")
                c.drawRightString(col_total, y, f"Rs. {total_item:.2f}")
                
                total_calc += total_item
            except Exception:
                continue

    # --- Totals ---
    y -= 8
    c.line(margin_left, y, margin_right, y)
    y -= 18
    c.setFont("Helvetica-Bold", 11)
    
    c.drawString(col_qty, y, "Total:")
    c.drawRightString(col_total, y, f"Rs. {inv[3]:.2f}")

    # --- Footer / notes ---
    y = margin_bottom
    c.setFont("Helvetica", 9)
    c.drawString(margin_left, y, "Notes: Thank you for choosing our clinic. Please get in touch for any queries regarding this bill.")

    c.save()
    if open_after:
        try:
            os.startfile(filename)
        except AttributeError:
            import subprocess
            try:
                subprocess.call(["open", filename]) # macOS
            except Exception:
                subprocess.call(["xdg-open", filename]) # Linux
        except Exception:
            pass


# -------------------- Sidebar Buttons --------------------
buttons = [
    ("Dashboard", view_dashboard),
    ("Doctors", view_doctors),
    ("Patients", view_patients),
    ("Appointments", view_appointments),
    ("Medicines", view_medicines),
    ("Services", view_services),   # --- (Feature 1) Added Services button ---
    ("Invoices", view_invoices),
    ("Settings", view_settings), 
    ("Quit", lambda: root.destroy())
]

for (text, cmd) in buttons:
    btn = tk.Button(sidebar, text=text, bg=SIDEBAR_BTN_BG, fg=SIDEBAR_BTN_FG,
                    activebackground="#0747a6", activeforeground="white", bd=0,
                    font=("Helvetica", 11, "bold"), command=cmd)
    btn.pack(fill="x", padx=12, pady=10)

# Start on dashboard
view_dashboard()
root.mainloop()