import sqlite3
import os
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)
DB_FILE = '/Users/naven/library.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            available INTEGER NOT NULL,
            location TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if empty
    c.execute('SELECT COUNT(*) FROM books')
    if c.fetchone()[0] == 0:
        initial_books = [
            ("Engineering Physics", "H.K. Malik", 1, "Shelf A1 - Row 3"),
            ("Concepts of Physics", "H.C. Verma", 0, "Checked out"),
            ("Modern Physics", "Arthur Beiser", 1, "Shelf B2 - Row 1"),
            ("Calculus: Early Transcendentals", "James Stewart", 1, "Shelf C4 - Row 2")
        ]
        c.executemany('INSERT INTO books (title, author, available, location) VALUES (?, ?, ?, ?)', initial_books)
        c.execute('INSERT INTO history (action) VALUES (?)', ("Database initialized",))
        
    conn.commit()
    conn.close()

# Initialize on startup
init_db()

@app.route('/')
def index():
    return send_file('/Users/naven/libaray.html')

@app.route('/api/books', methods=['GET'])
def get_books():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM books')
    books = [dict(row) for row in c.fetchall()]
    for b in books:
        b['available'] = bool(b['available'])
    conn.close()
    return jsonify(books)

@app.route('/api/books', methods=['POST'])
def add_book():
    data = request.json
    title = data.get('title')
    author = data.get('author')
    location = data.get('location', 'Unassigned')
    
    if not title or not author:
        return jsonify({'error': 'Title and author are required'}), 400
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO books (title, author, available, location) VALUES (?, ?, 1, ?)', 
              (title, author, location))
    c.execute('INSERT INTO history (action) VALUES (?)', (f"Added new book '{title}'",))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': new_id}), 201

@app.route('/api/books/<int:book_id>/borrow', methods=['PUT'])
def borrow_book(book_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT title FROM books WHERE id = ?', (book_id,))
    row = c.fetchone()
    success = False
    if row:
        title = row[0]
        c.execute('UPDATE books SET available = 0, location = "Checked out" WHERE id = ?', (book_id,))
        success = c.rowcount > 0
        if success:
            c.execute('INSERT INTO history (action) VALUES (?)', (f"Borrowed '{title}'",))
    conn.commit()
    conn.close()
    return jsonify({'success': success})

@app.route('/api/books/<int:book_id>/toggle', methods=['PUT'])
def toggle_status(book_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT available, title FROM books WHERE id = ?', (book_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Book not found'}), 404
        
    current_status = row['available']
    title = row['title']
    new_status = 0 if current_status else 1
    new_location = "Returned to Shelf" if new_status == 1 else "Checked out"
    
    c.execute('UPDATE books SET available = ?, location = ? WHERE id = ?', (new_status, new_location, book_id))
    action_text = f"Marked '{title}' as Returned" if new_status == 1 else f"Marked '{title}' as Borrowed"
    c.execute('INSERT INTO history (action) VALUES (?)', (action_text,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'available': bool(new_status), 'location': new_location})

@app.route('/api/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT title FROM books WHERE id = ?', (book_id,))
    row = c.fetchone()
    success = False
    if row:
        title = row[0]
        c.execute('DELETE FROM books WHERE id = ?', (book_id,))
        success = c.rowcount > 0
        if success:
            c.execute('INSERT INTO history (action) VALUES (?)', (f"Deleted book '{title}'",))
    conn.commit()
    conn.close()
    return jsonify({'success': success})

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM history ORDER BY timestamp DESC LIMIT 50')
    history = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(history)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
