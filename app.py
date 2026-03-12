import os
import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 # 100MB limit

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
# Create upload directories safely (Vercel is a Read-Only file system)
for media_type in ['videos', 'audio', 'images', 'text', 'pdfs']:
    try:
        os.makedirs(os.path.join(UPLOAD_FOLDER, media_type), exist_ok=True)
    except OSError:
        pass  # Ignore Read-Only filesystem errors on Vercel deployments
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
import ssl

def get_db_connection():
    try:
        host = os.getenv('DB_HOST', '127.0.0.1')
        
        # Cloud databases (like Aiven) strictly require SSL connections
        ssl_config = None
        if host not in ['localhost', '127.0.0.1']:
            ssl_config = {'ssl': {}}

        return pymysql.connect(
            host=host,
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'jansmrithi'),
            port=int(os.getenv('DB_PORT', 3306)),
            ssl=ssl_config,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        ), ""
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, str(e)

def login_required(func):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('register'))
        
    search_query = request.args.get('q', '').strip()
    conn, err = get_db_connection()
    if not conn:
        return f"Database not connected. Error: {err}", 500
        
    with conn.cursor() as cursor:
        if search_query:
            query = """
                SELECT c.*, u.username 
                FROM content c 
                JOIN users u ON c.user_id = u.user_id 
                WHERE c.state LIKE %s OR c.district LIKE %s 
                ORDER BY c.upload_date DESC
            """
            search_term = f"%{search_query}%"
            cursor.execute(query, (search_term, search_term))
        else:
            query = """
                SELECT c.*, u.username 
                FROM content c 
                JOIN users u ON c.user_id = u.user_id 
                ORDER BY c.upload_date DESC
            """
            cursor.execute(query)
        content_items = cursor.fetchall()
    conn.close()
    return render_template('index.html', content_items=content_items, search_query=search_query)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        conn, err = get_db_connection()
        if not conn:
            flash(f'Database error: {err}', 'error')
            return redirect(url_for('register'))

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, email, mobile_number, password) VALUES (%s, %s, %s, %s)",
                    (username, email, mobile_number, hashed_password)
                )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except pymysql.MySQLError as e:
            flash('Username or Email already exists.', 'error')
        finally:
            if conn:
                conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_identifier = request.form['username_email']
        password = request.form['password']
        
        conn, err = get_db_connection()
        if not conn:
            flash(f'Database error: {err}', 'error')
            return redirect(url_for('login'))

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s OR email = %s",
                (user_identifier, user_identifier)
            )
            user = cursor.fetchone()
            
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials, please try again.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/categories')
@login_required
def categories():
    cats = [
        {"name": "Folktales", "icon": "📖"},
        {"name": "Folk Music", "icon": "🎵"},
        {"name": "Folk Dances", "icon": "💃"},
        {"name": "Village Life", "icon": "🛖"},
        {"name": "Folk Science", "icon": "🔬"},
        {"name": "Dialects and Language", "icon": "🗣️"},
        {"name": "Folk Art", "icon": "🎨"},
        {"name": "Hand Skills", "icon": "🛠️"},
        {"name": "Sacred Places", "icon": "🛕"},
        {"name": "Food and Recipes", "icon": "🍲"},
        {"name": "Traditional Games and Sports", "icon": "🎯"},
        {"name": "Rituals and Ceremonies", "icon": "🕯️"},
        {"name": "Community Beliefs", "icon": "🧿"},
        {"name": "Agriculture", "icon": "🌾"},
        {"name": "Lost Practices", "icon": "🏺"},
        {"name": "Professions", "icon": "⚒️"}
    ]
    return render_template('categories.html', categories=cats)

@app.route('/media_type/<category_name>')
@login_required
def media_type(category_name):
    return render_template('media_type.html', category=category_name)

@app.route('/upload/<category>/<mtype>', methods=['GET', 'POST'])
@login_required
def upload(category, mtype):
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        state = request.form.get('state')
        district = request.form.get('district')
        language = request.form.get('language')
        
        upload_content = request.form.get('upload_content') # Text case if typed directly
        file = request.files.get('file')
        
        file_path = ''
        
        try:
            if mtype.lower() == 'text' and not file and upload_content:
                # creating a text file
                filename = secure_filename(title[:10]) + ".txt"
                path = os.path.join(app.config['UPLOAD_FOLDER'], 'text', filename)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(upload_content)
                file_path = f"uploads/text/{filename}"
            elif file and file.filename != '':
                filename = secure_filename(file.filename)
                folder_map = {
                    'video': 'videos', 'audio': 'audio', 'image': 'images',
                    'text': 'text', 'pdf': 'pdfs'
                }
                sub_folder = folder_map.get(mtype.lower(), 'text')
                path = os.path.join(app.config['UPLOAD_FOLDER'], sub_folder, filename)
                file.save(path)
                file_path = f"uploads/{sub_folder}/{filename}"
        except OSError:
            flash('Error: You cannot upload files to Vercel (it has a Read-Only file system). Please switch to PythonAnywhere or Render to unlock uploads!', 'error')
            return render_template('upload.html', category=category, mtype=mtype)
        
        if not file_path:
            flash('Please provide the valid file or text.', 'error')
            return render_template('upload.html', category=category, mtype=mtype)
            
        conn, err = get_db_connection()
        if not conn:
            flash(f'Database error: {err}', 'error')
            return redirect(url_for('home'))

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO content (user_id, title, description, category, media_type, file_path, state, district, language)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (session['user_id'], title, description, category, mtype, file_path, state, district, language))
            # Increase user uploads count
            cursor.execute("UPDATE users SET uploads_count = uploads_count + 1 WHERE user_id = %s", (session['user_id'],))
        conn.commit()
        conn.close()
        
        flash('Content uploaded successfully', 'success')
        return redirect(url_for('home'))
        
    return render_template('upload.html', category=category, mtype=mtype)

@app.route('/profile')
@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id=None):
    if user_id is None:
        user_id = session['user_id']
        
    conn, err = get_db_connection()
    if not conn:
        return f"Database error: {err}", 500

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            abort(404)
            
        cursor.execute("""
            SELECT c.*, u.username 
            FROM content c 
            JOIN users u ON c.user_id = u.user_id 
            WHERE c.user_id = %s 
            ORDER BY c.upload_date DESC
        """, (user_id,))
        contents = cursor.fetchall()
        
        # Check if current user follows this profile user
        is_following = False
        if session['user_id'] != user_id:
            cursor.execute("SELECT * FROM follow WHERE follower_user_id = %s AND following_user_id = %s", 
                           (session['user_id'], user_id))
            is_following = bool(cursor.fetchone())
            
    conn.close()
    
    return render_template('profile.html', user=user, contents=contents, is_following=is_following)

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    if session['user_id'] == user_id:
        return redirect(url_for('profile', user_id=user_id))
        
    conn, err = get_db_connection()
    if not conn:
        return f"Database error: {err}", 500

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM follow WHERE follower_user_id = %s AND following_user_id = %s",
                       (session['user_id'], user_id))
        already_following = cursor.fetchone()
        
        if already_following:
            # Unfollow
            cursor.execute("DELETE FROM follow WHERE follower_user_id = %s AND following_user_id = %s",
                           (session['user_id'], user_id))
            cursor.execute("UPDATE users SET following_count = following_count - 1 WHERE user_id = %s", (session['user_id'],))
            cursor.execute("UPDATE users SET followers_count = followers_count - 1 WHERE user_id = %s", (user_id,))
        else:
            # Follow
            cursor.execute("INSERT INTO follow (follower_user_id, following_user_id) VALUES (%s, %s)",
                           (session['user_id'], user_id))
            cursor.execute("UPDATE users SET following_count = following_count + 1 WHERE user_id = %s", (session['user_id'],))
            cursor.execute("UPDATE users SET followers_count = followers_count + 1 WHERE user_id = %s", (user_id,))
            
    conn.commit()
    conn.close()
    return redirect(url_for('profile', user_id=user_id))

@app.route('/delete/<int:content_id>', methods=['POST'])
@login_required
def delete(content_id):
    conn, err = get_db_connection()
    if not conn:
        return f"Database error: {err}", 500

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM content WHERE content_id = %s", (content_id,))
        content = cursor.fetchone()
        
        if content and content['user_id'] == session['user_id']:
            # Safe delete
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], content['file_path'].replace('uploads/', '')))
            except OSError:
                pass
            cursor.execute("DELETE FROM content WHERE content_id = %s", (content_id,))
            cursor.execute("UPDATE users SET uploads_count = uploads_count - 1 WHERE user_id = %s", (session['user_id'],))
            conn.commit()
            flash("Content deleted.", "success")
        else:
            flash("You do not have permission to delete this.", "error")
            
    conn.close()
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run()
