from flask import Flask
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    
    # Users table with authentication
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  is_admin BOOLEAN DEFAULT FALSE,
                  created_at DATETIME NOT NULL)''')
    
    # Events table
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  description TEXT,
                  date DATETIME NOT NULL,
                  venue TEXT NOT NULL,
                  total_seats INTEGER NOT NULL,
                  available_seats INTEGER NOT NULL,
                  price DECIMAL(10,2) NOT NULL,
                  created_at DATETIME NOT NULL)''')
    
    # Tickets table with relationships
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_id INTEGER NOT NULL,
                  user_id INTEGER NOT NULL,
                  seat_number INTEGER NOT NULL,
                  purchase_date DATETIME NOT NULL,
                  status TEXT CHECK(status IN ('active', 'cancelled', 'used')) NOT NULL,
                  FOREIGN KEY (event_id) REFERENCES events (id),
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()

init_db()

if __name__ == '__main__':
    app.run(debug=True)