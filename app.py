from flask import Flask, render_template, request, redirect, url_for, flash, session
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector import Error
import logging

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flash messages

# Database configuration
db_config = {
    'host': 'bloodbridge-db.czceaagk2hp5.us-east-1.rds.amazonaws.com',
    'user': 'admin',
    'password': 'password12345',
    'database': 'bloodbridge',
    'raise_on_warnings': True,
    'pool_size': 5,
    'pool_name': "mypool",
    'pool_reset_session': True
}

# Create a connection pool
cnxpool = MySQLConnectionPool(**db_config)

# Function to establish a database connection
def get_db_connection():
    try:
        conn = cnxpool.get_connection()
        return conn
    except Error as err:
        logging.error(f"Database connection failed: {err}")
        raise Exception("Database connection failed. Please try again later.")

@app.route("/test-db-connection")
def test_db_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")  # Test query to check connection
        db_name = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"Connected to the database: {db_name[0]}"
    except Error as err:
        return f"Error: {err}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        blood_type = request.form['blood_type']
        role = request.form['role']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user already exists
        cursor.execute("SELECT * FROM register WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            flash("Email already exists! Please log in.")
            return redirect(url_for('login', email=email))

        # Insert the new user into the database
        cursor.execute("INSERT INTO register (fullname, email, password, blood_type, role) VALUES (%s, %s, %s, %s, %s)", 
                      (fullname, email, password, blood_type, role))
        conn.commit()
        cursor.close()
        conn.close()

        user_data = {
            'fullname': fullname,
            'email': email,
            'blood_type': blood_type,
            'role': role
        }
        session['user'] = user_data
        flash("Registration successful! Please log in.")
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/confirm')
def confirm():
    user = session.get('user')
    return render_template('confirmation.html', user=user)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM register WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()
            
            if user:
                session['user'] = user
                
                if user['role'] == 'manager':
                    return redirect(url_for('inventory'))
                elif user['role'] == 'donor':
                    return redirect(url_for('donor_dashboard'))
                elif user['role'] == 'requestor':
                    return redirect(url_for('dashboard'))
            else:
                flash("Invalid login credentials!")
                return redirect(url_for('login'))

        except Exception as e:
            flash(f"Error: {str(e)}")
            return redirect(url_for('login'))
        finally:
            cursor.close()
            conn.close()

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))

    # Redirect based on role
    if user['role'] == 'manager':
        return redirect(url_for('inventory'))
    elif user['role'] == 'donor':
        return redirect(url_for('donor_dashboard'))
    
    # For requestors, show their requests
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.*, 
                d.fullname as donor_name,
                DATE_FORMAT(r.date, '%Y-%m-%d %H:%i') as formatted_date
            FROM request r
            LEFT JOIN register d ON r.donor_id = d.id
            WHERE r.requester_id = %s
            ORDER BY r.date DESC
        """, (user['id'],))
        requests = cursor.fetchall()
        return render_template("dashboard.html", user=user, requests=requests)

    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('login'))
    finally:
        cursor.close()
        conn.close()

@app.route("/req", methods=['GET', 'POST'])
def req():
    user = session.get('user')
    if not user or user['role'] != 'requestor':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            location = request.form['location']
            blood_type = request.form['blood_type']
            urgency = request.form['urgency']

            cursor.execute("""
                INSERT INTO request 
                (requester_id, location, blood_type, urgency, status, manager_approval) 
                VALUES (%s, %s, %s, %s, 'pending', 'pending')
            """, (user['id'], location, blood_type, urgency))
            
            conn.commit()
            flash("Blood request created successfully!")
            return redirect(url_for('dashboard'))

        # Get pending requests for status display
        cursor.execute("""
            SELECT r.*, 
                DATE_FORMAT(r.date, '%Y-%m-%d %H:%i') as formatted_date,
                CASE 
                    WHEN r.status = 'donated' THEN 'Donated'
                    WHEN r.status = 'rejected' THEN 'Rejected'
                    ELSE 'Pending'
                END as status_display
            FROM request r
            WHERE r.requester_id = %s
            ORDER BY r.date DESC
        """, (user['id'],))
        pending_requests = cursor.fetchall()

        return render_template("request.html", user=user, pending_requests=pending_requests)

    except Exception as e:
        conn.rollback()
        flash(f"Error creating request: {str(e)}")
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()
        conn.close()

def get_requester_data(requester_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM register WHERE id = %s", (requester_id,))
    requester_data = cursor.fetchone()
    cursor.close()
    conn.close()
    return requester_data

def get_request_data(request_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM request WHERE id = %s", (request_id,))
    request_data = cursor.fetchone()
    cursor.close()
    conn.close()
    return request_data

@app.route("/respond/<int:request_id>")
def respond(request_id):
    user = session.get('user')
    if not user or user['role'] != 'donor':
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get request details
        cursor.execute("""
            SELECT r.*, reg.fullname as requester_name, reg.email as requester_email
            FROM request r
            JOIN register reg ON r.requester_id = reg.id
            WHERE r.id = %s
        """, (request_id,))
        request_data = cursor.fetchone()
        
        if not request_data:
            flash("Request not found!")
            return redirect(url_for('donor_dashboard'))
            
        return render_template('respond.html', 
                             user=user,
                             request_data=request_data,
                             request_id=request_id,
                             requester_id=request_data['requester_id'])

    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('donor_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route("/donate-blood/<int:request_id>/<int:requester_id>", methods=["POST"])
def donate_blood(request_id, requester_id):
    user = session.get('user')
    if user is None:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE request SET status = 'donated' WHERE id = %s", (request_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Thank you for your donation!")
    return redirect(url_for('dashboard'))

@app.route("/inventory", methods=['GET', 'POST'])
def inventory():
    user = session.get('user')
    if not user or user['role'] != 'manager':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            blood_type = request.form['blood_type']
            stock_level = request.form['stock_level']
            
            cursor.execute("""
                INSERT INTO inventory (blood_type, stock_level) 
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE stock_level = %s
            """, (blood_type, stock_level, stock_level))
            
            conn.commit()
            flash("Inventory updated successfully!")

        # Get current inventory
        cursor.execute("SELECT * FROM inventory ORDER BY blood_type")
        inventory = cursor.fetchall()

        # Get all requests with requester information
        cursor.execute("""
            SELECT 
                r.*,
                reg.fullname as requester_name,
                DATE_FORMAT(r.date, '%Y-%m-%d %H:%i') as formatted_date
            FROM request r
            JOIN register reg ON r.requester_id = reg.id
            ORDER BY 
                CASE r.urgency
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                END,
                r.date DESC
        """)
        pending_requests = cursor.fetchall()

        return render_template("inventory.html", 
                            user=user, 
                            inventory=inventory, 
                            pending_requests=pending_requests)

    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}")
        return redirect(url_for('inventory'))
    finally:
        cursor.close()
        conn.close()

# New route for donor dashboard
@app.route("/donor_dashboard")
def donor_dashboard():
    user = session.get('user')
    if not user or user['role'] != 'donor':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get all pending requests matching donor's blood type
        cursor.execute("""
            SELECT r.*, 
                reg.fullname as requester_name,
                DATE_FORMAT(r.date, '%Y-%m-%d %H:%i') as formatted_date
            FROM request r
            JOIN register reg ON r.requester_id = reg.id
            WHERE r.blood_type = %s 
            AND r.status = 'pending'
            AND r.donor_id IS NULL
            ORDER BY 
                CASE r.urgency
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                END,
                r.date DESC
        """, (user['blood_type'],))
        requests = cursor.fetchall()

        # Get donor's responses/history
        cursor.execute("""
            SELECT r.*, 
                reg.fullname as requester_name,
                DATE_FORMAT(r.date, '%Y-%m-%d %H:%i') as formatted_date
            FROM request r
            JOIN register reg ON r.requester_id = reg.id
            WHERE r.donor_id = %s
            ORDER BY r.date DESC
        """, (user['id'],))
        donor_responses = cursor.fetchall()

        return render_template('donor_dashboard.html', 
                             user=user, 
                             requests=requests, 
                             donor_responses=donor_responses)

    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('login'))
    finally:
        cursor.close()
        conn.close()

@app.route("/confirm-donation/<int:request_id>", methods=['POST'])
def confirm_donation(request_id):
    user = session.get('user')
    if not user or user['role'] != 'requestor':
        return redirect(url_for('login'))

    action = request.form.get('action')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if action == 'accept':
        cursor.execute("""
            UPDATE request 
            SET confirmation_status = 'accepted', status = 'donated'
            WHERE id = %s AND requester_id = %s
        """, (request_id, user['id']))
    elif action == 'reject':
        cursor.execute("""
            UPDATE request 
            SET confirmation_status = 'rejected', donor_id = NULL
            WHERE id = %s AND requester_id = %s
        """, (request_id, user['id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash(f"Donation {action}ed successfully!")
    return redirect(url_for('dashboard'))

@app.route("/approve_request/<int:request_id>", methods=['POST'])
def approve_request(request_id):
    user = session.get('user')
    if not user or (user['role'] != 'donor' and user['role'] != 'manager'):
        return redirect(url_for('login'))

    action = request.form.get('action')
    if action not in ['accept', 'reject']:
        flash("Invalid action")
        return redirect(url_for('donor_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if action == 'accept':
            # Update request with donor/manager's acceptance
            cursor.execute("""
                UPDATE request 
                SET donor_id = %s,
                    status = 'donated',
                    manager_approval = CASE 
                        WHEN %s = 'manager' THEN 'approve'
                        ELSE manager_approval
                    END
                WHERE id = %s AND status = 'pending'
            """, (user['id'], user['role'], request_id))
        else:  # action == 'reject'
            # Mark request as rejected
            cursor.execute("""
                UPDATE request 
                SET status = 'rejected',
                    manager_approval = CASE 
                        WHEN %s = 'manager' THEN 'reject'
                        ELSE manager_approval
                    END
                WHERE id = %s AND status = 'pending'
            """, (user['role'], request_id))
        
        conn.commit()
        flash(f"Request {action}ed successfully!")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating request: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    
    return_route = 'inventory' if user['role'] == 'manager' else 'donor_dashboard'
    return redirect(url_for(return_route))

# Add this at the top of your file with other imports
import logging
logging.basicConfig(level=logging.ERROR)

# Add this function to test database connectivity
def test_database_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Database connection test failed: {e}")
        return False

# Add this before running the app
if __name__ == "__main__":
    if not test_database_connection():
        logging.error("Failed to connect to database. Check your configuration.")
        exit(1)
    app.run(debug=True, host="0.0.0.0", port=8000)

@app.route("/respond_to_request/<int:request_id>", methods=['POST'])
def respond_to_request(request_id):
    user = session.get('user')
    if not user or (user['role'] != 'donor' and user['role'] != 'manager'):
        return redirect(url_for('login'))

    action = request.form.get('action')
    if action not in ['accept', 'reject']:
        flash("Invalid action")
        return redirect(url_for('donor_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if action == 'accept':
            # Update request with donor/manager's acceptance
            cursor.execute("""
                UPDATE request 
                SET donor_id = %s,
                    status = 'donated',
                    manager_approval = CASE 
                        WHEN %s = 'manager' THEN 'approve'
                        ELSE manager_approval
                    END
                WHERE id = %s AND status = 'pending'
            """, (user['id'], user['role'], request_id))
        else:  # action == 'reject'
            # Mark request as rejected
            cursor.execute("""
                UPDATE request 
                SET status = 'rejected',
                    manager_approval = CASE 
                        WHEN %s = 'manager' THEN 'reject'
                        ELSE manager_approval
                    END
                WHERE id = %s AND status = 'pending'
            """, (user['role'], request_id))
        
        conn.commit()
        flash(f"Request {action}ed successfully!")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating request: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    
    return_route = 'inventory' if user['role'] == 'manager' else 'donor_dashboard'
    return redirect(url_for(return_route))

if __name__ == "__main__":
    if not test_database_connection():
        logging.error("Failed to connect to database. Check your configuration.")
        exit(1)
    app.run(debug=True, host="0.0.0.0", port=8000)
