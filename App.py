from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from functools import wraps
import hashlib
import os

conn = sqlite3.connect('tickets.db')
c = conn.cursor()

# Create users table
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT UNIQUE NOT NULL,
              password TEXT NOT NULL,
              email TEXT UNIQUE NOT NULL,
              is_admin BOOLEAN DEFAULT 0,
              created_at DATETIME NOT NULL)''')

# Create events table
c.execute('''CREATE TABLE IF NOT EXISTS events
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              description TEXT,
              date DATETIME NOT NULL,
              venue TEXT NOT NULL,
              total_rows INTEGER NOT NULL,
              seats_per_row INTEGER NOT NULL,
              total_seats INTEGER NOT NULL,
              available_seats INTEGER NOT NULL,
              price DECIMAL(10,2) NOT NULL,
              created_at DATETIME NOT NULL)''')

# Create tickets table
c.execute('''CREATE TABLE IF NOT EXISTS tickets
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              row_number INTEGER NOT NULL,
              seat_column INTEGER NOT NULL,
              purchase_date DATETIME NOT NULL,
              status TEXT CHECK(status IN ('active', 'cancelled', 'used')) NOT NULL,
              FOREIGN KEY (event_id) REFERENCES events (id),
              FOREIGN KEY (user_id) REFERENCES users (id))''')

conn.commit()
conn.close()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'is_admin' not in session or not session['is_admin']:
            flash('Admin access required')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute('SELECT * FROM events WHERE date > ? ORDER BY date', (datetime.now(),))
    upcoming_events = c.fetchall()
    conn.close()
    return render_template('home.html', events=upcoming_events)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        
        conn = sqlite3.connect('tickets.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[4]
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        email = request.form['email']
        
        conn = sqlite3.connect('tickets.db')
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO users (username, password, email, created_at)
                        VALUES (?, ?, ?, ?)''', (username, password, email, datetime.now()))
            conn.commit()
            flash('Registration successful')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/user/profile')
@login_required
def user_profile():
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute('''SELECT tickets.*, events.name 
                 FROM tickets 
                 JOIN events ON tickets.event_id = events.id 
                 WHERE user_id = ?''', (session['user_id'],))
    tickets = c.fetchall()
    conn.close()
    return render_template('user_profile.html', tickets=tickets)

@app.route('/admin')
@login_required
@admin_required
def admin_portal():
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute('SELECT * FROM events ORDER BY date')
    events = c.fetchall()
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM tickets')
    total_tickets = c.fetchone()[0]
    conn.close()
    return render_template('admin_portal.html', 
                         events=events, 
                         total_users=total_users, 
                         total_tickets=total_tickets)

@app.route('/admin/add_event', methods=['GET', 'POST'])
@login_required
@admin_required
def add_event():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        venue = request.form['venue']
        total_rows = int(request.form['total_rows'])
        seats_per_row = int(request.form['seats_per_row'])
        total_seats = total_rows * seats_per_row
        price = float(request.form['price'])
        
        conn = sqlite3.connect('tickets.db')
        c = conn.cursor()
        c.execute('''INSERT INTO events 
                     (name, description, date, venue, total_rows, seats_per_row,
                      total_seats, available_seats, price, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (name, description, date, venue, total_rows, seats_per_row,
                      total_seats, total_seats, price, datetime.now()))
        conn.commit()
        conn.close()
        flash('Event added successfully')
        return redirect(url_for('admin_portal'))
    return render_template('add_event.html')

# Original show_seats function update
@app.route('/events/<int:event_id>')
def show_seats(event_id):
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM events WHERE id = ?', (event_id,))
    event = c.fetchone()
    
    if not event:
        flash('Event not found')
        return redirect(url_for('home'))
    
    c.execute('SELECT row_number, seat_column FROM tickets WHERE event_id = ?', (event_id,))
    taken_seats = set((row[0], row[1]) for row in c.fetchall())
    
    seating = []
    for row in range(1, event[5] + 1):
        seat_row = []
        for col in range(1, event[6] + 1):
            is_taken = (row, col) in taken_seats
            seat_row.append({'row': row, 'column': col, 'taken': is_taken})
        seating.append(seat_row)
    
    conn.close()
    return render_template('seats.html', event=event, seating=seating)

@app.route('/book_seat/<int:event_id>/<int:row>/<int:column>', methods=['POST'])
@login_required
def book_seat(event_id, row, column):
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    
    # Check if seat is available
    c.execute('''SELECT * FROM tickets 
                 WHERE event_id = ? AND row_number = ? AND seat_column = ?''',
                 (event_id, row, column))
    if c.fetchone():
        flash('Seat already taken')
        return redirect(url_for('show_seats', event_id=event_id))
    
    # Book the seat
    c.execute('''INSERT INTO tickets 
                 (event_id, user_id, row_number, seat_column, purchase_date, status)
                 VALUES (?, ?, ?, ?, ?, ?)''',
                 (event_id, session['user_id'], row, column, datetime.now(), 'active'))
    
    # Update available seats
    c.execute('''UPDATE events 
                 SET available_seats = available_seats - 1 
                 WHERE id = ?''', (event_id,))
    
    conn.commit()
    conn.close()
    flash('Seat booked successfully')
    return redirect(url_for('user_profile'))

if __name__ == '__main__':
    app.run(debug=True)