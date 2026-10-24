import os, secrets, time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db_adapter import get_db, is_postgres

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")

RATE_LIMITS = {}

def is_rate_limited(key, max_calls=15, period=5):
    now = time.time()
    calls = RATE_LIMITS.get(key, [])
    calls = [t for t in calls if now - t < period]
    if len(calls) >= max_calls:
        RATE_LIMITS[key] = calls
        return True
    calls.append(now)
    RATE_LIMITS[key] = calls
    return False

def db():
    return get_db()

def init_db():
    with db() as c:
        if is_postgres():
            # PostgreSQL schema for Supabase
            c.executescript("""
            CREATE TABLE IF NOT EXISTS admins(
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin'
            );
            CREATE TABLE IF NOT EXISTS stages(
                stage_num INT PRIMARY KEY,
                name TEXT NOT NULL,
                requires_topic_choice INT NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS questions(
                id SERIAL PRIMARY KEY,
                stage INT NOT NULL DEFAULT 1,
                topic TEXT NOT NULL DEFAULT 'General',
                question TEXT NOT NULL,
                a TEXT NOT NULL, b TEXT NOT NULL, c TEXT NOT NULL, d TEXT NOT NULL,
                answer TEXT NOT NULL,
                points INT NOT NULL DEFAULT 10,
                seconds INT NOT NULL DEFAULT 25,
                active INT NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS participants(
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                team TEXT NOT NULL DEFAULT '',
                access_code TEXT NOT NULL,
                chosen_topic TEXT DEFAULT '',
                joined_at DOUBLE PRECISION NOT NULL
            );
            CREATE TABLE IF NOT EXISTS responses(
                id SERIAL PRIMARY KEY,
                participant_id INT NOT NULL,
                participant_name TEXT DEFAULT '',
                question_id INT NOT NULL,
                question_text TEXT DEFAULT '',
                choice TEXT NOT NULL,
                selected_text TEXT DEFAULT '',
                correct INT NOT NULL,
                points INT NOT NULL,
                answered_at DOUBLE PRECISION NOT NULL,
                UNIQUE(participant_id, question_id)
            );
            -- Safely add columns if table already exists in Supabase
            ALTER TABLE responses ADD COLUMN IF NOT EXISTS participant_name TEXT DEFAULT '';
            ALTER TABLE responses ADD COLUMN IF NOT EXISTS question_text TEXT DEFAULT '';
            ALTER TABLE responses ADD COLUMN IF NOT EXISTS selected_text TEXT DEFAULT '';
            CREATE TABLE IF NOT EXISTS security_logs(
                id SERIAL PRIMARY KEY,
                participant_id INT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL
            );
            """)
        else:
            # SQLite schema for local development
            c.executescript("""
            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin'
            );
            CREATE TABLE IF NOT EXISTS stages(
                stage_num INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                requires_topic_choice INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS questions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage INTEGER NOT NULL DEFAULT 1,
                topic TEXT NOT NULL DEFAULT 'General',
                question TEXT NOT NULL,
                a TEXT NOT NULL, b TEXT NOT NULL, c TEXT NOT NULL, d TEXT NOT NULL,
                answer TEXT NOT NULL CHECK(answer IN ('a','b','c','d')),
                points INTEGER NOT NULL DEFAULT 10,
                seconds INTEGER NOT NULL DEFAULT 25,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS participants(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                team TEXT NOT NULL DEFAULT '',
                access_code TEXT NOT NULL,
                chosen_topic TEXT DEFAULT '',
                joined_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS responses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER NOT NULL,
                participant_name TEXT DEFAULT '',
                question_id INTEGER NOT NULL,
                question_text TEXT DEFAULT '',
                choice TEXT NOT NULL,
                selected_text TEXT DEFAULT '',
                correct INTEGER NOT NULL,
                points INTEGER NOT NULL,
                answered_at REAL NOT NULL,
                UNIQUE(participant_id, question_id),
                FOREIGN KEY(participant_id) REFERENCES participants(id),
                FOREIGN KEY(question_id) REFERENCES questions(id)
            );
            CREATE TABLE IF NOT EXISTS security_logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY(participant_id) REFERENCES participants(id)
            );
            """)

        # Seed default 3 stages configuration
        for snum, sname, req in [(1, 'CS Fundamentals', 0), (2, 'Core Systems & Architecture', 0), (3, 'Specialization Domain', 1)]:
            c.execute("INSERT INTO stages(stage_num, name, requires_topic_choice) VALUES(?,?,?) ON CONFLICT(stage_num) DO NOTHING", (snum, sname, req))

        c.execute("INSERT INTO settings(key,value) VALUES('event_code','TECH2026') ON CONFLICT(key) DO NOTHING")

        # Ensure Stage 1 has all 25 official questions in the DB
        stage1_count_row = c.execute("SELECT COUNT(*) as n FROM questions WHERE stage=1").fetchone()
        stage1_count = stage1_count_row["n"] if isinstance(stage1_count_row, dict) else stage1_count_row[0]
        
        # If Stage 1 has old sample questions (count < 25), sync full 25 questions
        if stage1_count < 25:
            c.execute("DELETE FROM questions WHERE stage=1")
            stage1_official_questions = [
                # Python
                (1, "Python", "Which keyword is used to define a function in Python?", "function", "def", "fun", "define", "b", 10, 25),
                (1, "Python", "What will print(type([])) output?", "<class 'tuple'>", "<class 'dict'>", "<class 'list'>", "<class 'set'>", "c", 10, 25),
                (1, "Python", "Which of these data types is immutable in Python?", "list", "dict", "set", "tuple", "d", 10, 25),
                (1, "Python", "Which symbol is used for a single-line comment in Python?", "//", "#", "/*", "--", "b", 10, 25),
                (1, "Python", "What is the correct file extension for Python files?", ".pt", ".pyt", ".py", ".python", "c", 10, 25),
                # C++
                (1, "C++", "Which object is used to print output in C++?", "print", "cout", "echo", "printf()", "b", 10, 25),
                (1, "C++", "Who created C++?", "Dennis Ritchie", "James Gosling", "Guido van Rossum", "Bjarne Stroustrup", "d", 10, 25),
                (1, "C++", "Which of these is NOT a valid C++ data type?", "int", "float", "real", "char", "c", 10, 25),
                (1, "C++", "Which operator is used to access a member through a pointer in C++?", ".", "->", "::", "&", "b", 10, 25),
                (1, "C++", "What is the file extension of a C++ source file?", ".cpp", ".cp", ".c++x", ".cplus", "a", 10, 25),
                # Git & GitHub
                (1, "Git & GitHub", "Which command is used to copy a remote repository to your local machine?", "git copy", "git pull", "git clone", "git fetch", "c", 10, 25),
                (1, "Git & GitHub", "What is Git?", "A programming language", "A distributed version control system", "A web browser", "A database", "b", 10, 25),
                (1, "Git & GitHub", "What does git add . do?", "Commits all changes", "Deletes all files", "Pushes code to GitHub", "Stages all changes in the current directory", "d", 10, 25),
                (1, "Git & GitHub", "Which command creates a new branch and switches to it?", "git branch -d new", "git checkout -b new", "git merge new", "git switch -x new", "b", 10, 25),
                (1, "Git & GitHub", "GitHub is mainly used for:", "Hosting code repositories and collaboration", "Designing graphics", "Editing videos", "Sending emails", "a", 10, 25),
                # Web Development
                (1, "Web Development", "What does HTML stand for?", "HyperText Markup Language", "HighText Machine Language", "HyperTool Multi Language", "Home Text Markup Language", "a", 10, 25),
                (1, "Web Development", "Which technology is used to style web pages?", "HTML", "CSS", "SQL", "PHP", "b", 10, 25),
                (1, "Web Development", "Which HTML tag creates the largest heading?", "<h6>", "<head>", "<h1>", "<heading>", "c", 10, 25),
                (1, "Web Development", "Which JavaScript keyword declares a block-scoped variable?", "var", "let", "int", "dim", "b", 10, 25),
                (1, "Web Development", "What does the HTTP status code 404 mean?", "Server error", "Success", "Unauthorized", "Not Found", "d", 10, 25),
                # LinkedIn
                (1, "LinkedIn", "LinkedIn is mainly used for:", "Professional networking", "Online gaming", "Photo editing", "Music streaming", "a", 10, 25),
                (1, "LinkedIn", "Who is the co-founder of LinkedIn?", "Mark Zuckerberg", "Reid Hoffman", "Jack Dorsey", "Elon Musk", "b", 10, 25),
                (1, "LinkedIn", "Which pair of platforms is owned by Microsoft?", "Instagram and WhatsApp", "YouTube and Gmail", "LinkedIn and GitHub", "Twitter and Reddit", "c", 10, 25),
                # General Programming
                (1, "General Programming", "Which of the following is NOT a programming language?", "Rust", "Java", "Python", "Linux", "d", 10, 25),
                (1, "General Programming", "What does IDE stand for?", "Internal Debug Engine", "Integrated Development Environment", "Interactive Design Editor", "Internet Data Exchange", "b", 10, 25)
            ]
            c.executemany("INSERT INTO questions(stage, topic, question, a, b, c, d, answer, points, seconds) VALUES(?,?,?,?,?,?,?,?,?,?)", stage1_official_questions)

        # Ensure Stage 2 has all 10 official questions in the DB
        stage2_count_row = c.execute("SELECT COUNT(*) as n FROM questions WHERE stage=2").fetchone()
        stage2_count = stage2_count_row["n"] if isinstance(stage2_count_row, dict) else stage2_count_row[0]

        if stage2_count < 10:
            c.execute("DELETE FROM questions WHERE stage=2")
            stage2_official_questions = [
                # Git
                (2, "Git & GitHub", "Which Git command is used to combine commits and rewrite history by reapplying them on top of another branch?", "git merge", "git rebase", "git cherry", "git stash", "b", 15, 25),
                (2, "Git & GitHub", "What does git stash do?", "Deletes all uncommitted changes permanently", "Pushes changes to the remote repository", "Temporarily saves uncommitted changes and cleans the working directory", "Creates a new branch", "c", 15, 25),
                (2, "Git & GitHub", "In Git, what is the purpose of a .gitignore file?", "To delete files from the remote repository", "To tell Git which files or folders to not track", "To store commit history", "To list all contributors", "b", 15, 25),

                # C++
                (2, "C++", "In C++, which of these is true about a reference variable?", "It can be reassigned to refer to another variable", "It can be null", "It must be initialized at the time of declaration", "It is always stored on the heap", "c", 15, 25),
                (2, "C++", "What is the main purpose of the virtual keyword in C++?", "To declare a constant variable", "To enable runtime polymorphism", "To allocate memory dynamically", "To prevent inheritance", "b", 15, 25),

                # Web Development
                (2, "Web Development", "Which HTTP method is idempotent and typically used to completely replace a resource?", "POST", "PATCH", "PUT", "CONNECT", "c", 15, 25),
                (2, "Web Development", "What does the “box model” in CSS consist of?", "Content, padding, border, margin", "Header, body, footer, sidebar", "Flexbox, grid, float, position", "Width, height, color, font", "a", 15, 25),
                (2, "Web Development", "What is the difference between == and === in JavaScript?", "No difference", "== compares type and value, === compares only value", "== compares only value (with type conversion), === compares value and type", "=== is used only for strings", "c", 15, 25),

                # Python
                (2, "Python", "In Python, which of these is a mutable data type?", "tuple", "string", "frozenset", "dictionary", "d", 15, 25),
                (2, "Python", "Which of these is a key feature of Python’s “Global Interpreter Lock” (GIL)?", "It allows true parallel execution of multiple threads", "It lets only one thread execute Python bytecode at a time", "It locks global variables from being modified", "It prevents Python from using multiple files", "b", 15, 25)
            ]
            c.executemany("INSERT INTO questions(stage, topic, question, a, b, c, d, answer, points, seconds) VALUES(?,?,?,?,?,?,?,?,?,?)", stage2_official_questions)

        # Ensure Stage 3 has all 25 official topic-specific questions
        stage3_count_row = c.execute("SELECT COUNT(*) as n FROM questions WHERE stage=3").fetchone()
        stage3_count = stage3_count_row["n"] if isinstance(stage3_count_row, dict) else stage3_count_row[0]
        if stage3_count < 25:
            c.execute("DELETE FROM questions WHERE stage=3")
            stage3_official_questions = [
                # Topic 1: Web Development
                (3, "Web Development", "Why is HTTP called a stateless protocol?", "It cannot transfer images or files.", "Each request is processed independently without automatically remembering previous requests.", "It works only without a database.", "It allows only one request per user.", "b", 20, 30),
                (3, "Web Development", "A user logs in to a website and navigates to another page. How can the website recognize the user without asking for the password again?", "The browser automatically sends the password with every request.", "The website uses a session identifier, often stored in a cookie, to associate requests with the logged-in user.", "The HTML page permanently stores the user's identity.", "The IP address always uniquely identifies the logged-in user.", "b", 20, 30),
                (3, "Web Development", "What is the primary purpose of the DOM in web development?", "To store passwords securely on the server.", "To convert JavaScript into machine code.", "To represent a web page as a structured object tree that scripts can access and modify.", "To establish a network connection between two servers.", "c", 20, 30),
                (3, "Web Development", "A developer changes a CSS file, but the browser continues displaying the old design. Which explanation is most likely?", "CSS cannot be changed after a page loads.", "The browser may be using a cached version of the stylesheet.", "JavaScript has permanently disabled CSS.", "HTML does not support external stylesheets.", "b", 20, 30),
                (3, "Web Development", "Why should a web application validate user input on the server even if JavaScript already validates it in the browser?", "Browser validation is always slower.", "Server-side validation prevents users from bypassing checks by modifying or skipping client-side code.", "JavaScript cannot check input fields.", "Server validation is required only for images.", "b", 20, 30),

                # Topic 2: C++ Programming
                (3, "C++ Programming", "What is the output of this code? int x=10; int* p=&x; *p=20; cout<<x;", "10", "20", "Address of x", "Compilation error", "b", 20, 30),
                (3, "C++ Programming", "Two pointers point to the same integer variable. If one pointer changes the variable's value, what happens when the other pointer dereferences it?", "It sees the updated value because both point to the same memory location.", "It sees the original value because pointers copy values.", "It becomes null automatically.", "The program always crashes.", "a", 20, 30),
                (3, "C++ Programming", "What is the main risk of dereferencing a pointer after its dynamically allocated memory has been deleted?", "The pointer automatically allocates new memory.", "The pointer becomes a reference to a valid integer.", "The program may exhibit undefined behavior because the pointer is dangling.", "The compiler always detects and prevents it.", "c", 20, 30),
                (3, "C++ Programming", "What is the difference between passing an integer by value and passing it by reference to a function?", "Both always modify the original integer.", "Passing by value gives the function a copy; passing by reference allows it to modify the original variable.", "Passing by reference creates a new independent variable.", "Passing by value is possible only for pointers.", "b", 20, 30),
                (3, "C++ Programming", "What does a C++ constructor primarily do when an object is created?", "Deletes the object from memory.", "Initializes the object's state and establishes its initial invariants.", "Runs only when the program terminates.", "Converts every object into a pointer.", "b", 20, 30),

                # Topic 3: Python Programming
                (3, "Python Programming", "What is printed? a=[1,2]; b=a; b.append(3); print(a)", "[1, 2]", "[1, 2, 3]", "[3]", "Error", "b", 20, 30),
                (3, "Python Programming", "Why does a = a + [4] behave differently from a.append(4) when another variable b refers to the original list?", "The plus operator always modifies both variables.", "append creates a new list, while plus modifies the original list.", "The plus expression creates a new list and rebinds a, while append modifies the existing list object.", "Python variables cannot refer to the same list.", "c", 20, 30),
                (3, "Python Programming", "What is the output? print(bool([]), bool([0]))", "True True", "False False", "False True", "True False", "c", 20, 30),
                (3, "Python Programming", "What is the main benefit of using a dictionary to store student marks with unique roll numbers as keys?", "It automatically sorts marks in descending order.", "It can provide average constant-time key lookup, assuming a good hash distribution.", "It guarantees that every value is unique.", "It stores data only in alphabetical order.", "b", 20, 30),
                (3, "Python Programming", "A function changes the contents of a list passed to it, but the caller's list also changes. What best explains this?", "Python passes every argument by copying the entire object.", "The function and caller can refer to the same mutable list object.", "Lists are immutable.", "The function executes in the caller's memory only if it is recursive.", "b", 20, 30),

                # Topic 4: Data Structures & Algorithms (DSA)
                (3, "Data Structures & Algorithms (DSA)", "An unsorted array contains n elements. What is the worst-case time complexity of searching for a particular value?", "O(1)", "O(log n)", "O(n)", "O(n log n)", "c", 20, 30),
                (3, "Data Structures & Algorithms (DSA)", "Which data structure is most suitable for implementing an undo operation in a text editor, where the most recent action must be undone first?", "Queue", "Stack", "Binary search tree", "Graph", "b", 20, 30),
                (3, "Data Structures & Algorithms (DSA)", "A binary search is applied to a sorted array of 1,000 elements. Why is it generally faster than linear search for finding a value?", "It checks every element twice.", "It eliminates approximately half of the remaining search range at each step.", "It always starts from the last element.", "It converts the array into a linked list.", "b", 20, 30),
                (3, "Data Structures & Algorithms (DSA)", "A queue is used to manage print jobs. Why is a queue a natural choice?", "It processes the newest job first.", "It processes jobs in the order they arrive, following FIFO.", "It sorts jobs by file size automatically.", "It allows only one job to be stored.", "b", 20, 30),
                (3, "Data Structures & Algorithms (DSA)", "A hash table provides average O(1) lookup. What is a likely reason lookup may become O(n) in the worst case?", "The table contains integers.", "All keys are unique.", "Many keys collide into the same bucket and require additional searching.", "The table is accessed using a variable.", "c", 20, 30),

                # Topic 5: Computer Networks
                (3, "Computer Networks", "Why does a computer need both an IP address and a MAC address to communicate across networks?", "IP addresses identify applications, while MAC addresses identify passwords.", "IP addresses support logical addressing and routing between networks, while MAC addresses identify interfaces for local-link delivery.", "MAC addresses are used only for wireless networks.", "IP addresses work only within a single LAN.", "b", 20, 30),
                (3, "Computer Networks", "A laptop sends data to a server outside its local network. Which device's MAC address is typically used as the destination MAC in the first Ethernet frame?", "The remote server's MAC address, obtained directly from the internet.", "The laptop's own MAC address.", "The local router or default gateway's MAC address.", "The DNS server's MAC address in every case.", "c", 20, 30),
                (3, "Computer Networks", "What is the main purpose of DNS?", "To encrypt all web traffic.", "To translate domain names into IP addresses or other DNS records.", "To assign a MAC address to every device.", "To guarantee that websites are free of malware.", "b", 20, 30),
                (3, "Computer Networks", "What happens when a router forwards an IP packet from one network to another?", "The source and destination MAC addresses usually change for the next link, while the IP source and destination generally remain the same.", "The IP destination is always replaced by the router's IP address.", "The packet loses its IP addresses and uses only MAC addresses.", "The router changes the web page content.", "a", 20, 30),
                (3, "Computer Networks", "Why is TCP commonly used for transferring files when reliable delivery is important?", "It guarantees the fastest possible speed in every situation.", "It provides mechanisms such as acknowledgments, retransmissions, and ordered byte delivery.", "It does not use ports.", "It works only within a local network.", "b", 20, 30)
            ]
            c.executemany("INSERT INTO questions(stage, topic, question, a, b, c, d, answer, points, seconds) VALUES(?,?,?,?,?,?,?,?,?,?)", stage3_official_questions)

ADMIN_EMAILS = {
    "adityaahamana18@gmail.com",
    "25cb1mr81@mitsgwl.ac.in"
}

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if "admin_email" not in session and "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapped

def setting(conn, key, default=""):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def set_setting(conn, key, value):
    conn.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def log_security_event(pid, event_type, details):
    try:
        with db() as c:
            c.execute("INSERT INTO security_logs(participant_id, event_type, details, created_at) VALUES(?,?,?,?)",
                      (pid, event_type, str(details)[:250], time.time()))
    except Exception as e:
        print("Security log error:", e)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/join", methods=["POST"])
def join():
    client_ip = request.remote_addr or "unknown"
    if is_rate_limited(f"join_{client_ip}", max_calls=8, period=10):
        flash("Too many attempts. Please slow down.", "error")
        return redirect(url_for("home"))

    name = request.form.get("name", "").strip()[:60]
    email = request.form.get("email", "").strip()[:100]
    photo_url = request.form.get("photo_url", "").strip()
    team = request.form.get("team", "").strip()[:60]
    code = request.form.get("code", "").strip().upper()
    
    with db() as c:
        expected = setting(c, "event_code", os.environ.get("TECHNERD_EVENT_CODE", "TECH2026")).upper()
        if not name or code != expected:
            flash("Enter your name and a valid event code.", "error")
            return redirect(url_for("home"))
        
        cur = c.execute("INSERT INTO participants(name,email,photo_url,team,access_code,joined_at) VALUES(?,?,?,?,?,?)",
                        (name, email, photo_url, team, secrets.token_urlsafe(12), time.time()))
        session["participant_id"] = cur.lastrowid
        session["participant_name"] = name
        session["participant_photo"] = photo_url
        c.execute("INSERT INTO security_logs(participant_id, event_type, details, created_at) VALUES(?,?,?,?)",
                  (session["participant_id"], "PARTICIPANT_JOINED", f"Name: {name}, Email: {email}, IP: {client_ip}", time.time()))

    return redirect(url_for("play"))

@app.route("/logout")
def logout():
    session.pop("participant_id", None)
    session.pop("participant_name", None)
    session.pop("participant_photo", None)
    return redirect(url_for("home"))

@app.route("/play")
def play():
    pid = session.get("participant_id")
    if not pid:
        return redirect(url_for("home"))
    with db() as c:
        p = c.execute("SELECT id FROM participants WHERE id=?", (pid,)).fetchone()
        if not p:
            session.pop("participant_id", None)
            flash("Quiz has been reset by the organizer. Please join again.", "error")
            return redirect(url_for("home"))
    return render_template("play.html")

@app.route("/api/security-log", methods=["POST"])
def security_log_endpoint():
    pid = session.get("participant_id")
    if not pid:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    event_type = data.get("event", "UNKNOWN_EVENT")
    details = data.get("details", "")

    log_security_event(pid, event_type, details)
    return jsonify({"ok": True})

# Participant selects their custom topic for special stage
@app.route("/api/choose-topic", methods=["POST"])
def choose_topic():
    pid = session.get("participant_id")
    if not pid:
        return jsonify({"error": "Unauthorized"}), 401

    topic = (request.json or {}).get("topic", "").strip()
    if not topic:
        return jsonify({"error": "Please select a valid topic."}), 400

    with db() as c:
        c.execute("UPDATE participants SET chosen_topic=? WHERE id=?", (topic, pid))
        log_security_event(pid, "CHOSE_SPECIAL_TOPIC", f"Topic: {topic}")

    return jsonify({"ok": True, "topic": topic})

# Acknowledge entry into new stage (intermission dismissal)
@app.route("/api/start-stage", methods=["POST"])
def start_stage():
    pid = session.get("participant_id")
    if not pid:
        return jsonify({"error": "Unauthorized"}), 401
    s_num = (request.json or {}).get("stage")
    if s_num:
        session[f"stage_{s_num}_started_{pid}"] = True
    return jsonify({"ok": True})

# Dynamic Multi-Stage Quiz Progression API
@app.route("/api/quiz")
def quiz_state():
    pid = session.get("participant_id")
    if not pid:
        return jsonify({"error": "Join the quiz first."}), 401

    if is_rate_limited(f"quiz_{pid}", max_calls=25, period=5):
        return jsonify({"error": "Rate limit exceeded. Please wait a moment."}), 429

    with db() as c:
        p = c.execute("SELECT id, chosen_topic FROM participants WHERE id=?", (pid,)).fetchone()
        if not p:
            session.pop("participant_id", None)
            return jsonify({"status": "reset", "error": "Quiz reset by organizer. Please rejoin."}), 401

        chosen_topic = p["chosen_topic"] or ""
        
        # Already answered questions by this participant
        answered_ids = {row["question_id"] for row in c.execute("SELECT question_id FROM responses WHERE participant_id=?", (pid,)).fetchall()}
        
        # Current score calculation
        score_row = c.execute("SELECT COALESCE(SUM(points), 0) total_score, COUNT(id) answered_count FROM responses WHERE participant_id=?", (pid,)).fetchone()
        current_score = score_row["total_score"]
        answered_count = score_row["answered_count"]

        # Fetch configured stages in order
        stages = c.execute("SELECT stage_num, name, requires_topic_choice FROM stages ORDER BY stage_num ASC").fetchall()
        
        if not stages:
            return jsonify({"status": "empty", "message": "No stages configured yet."})

        # Process each stage dynamically
        for stage_idx, stage in enumerate(stages):
            s_num = stage["stage_num"]
            s_name = stage["name"]
            req_topic = bool(stage["requires_topic_choice"])

            # Check if this stage requires topic selection and user hasn't chosen one yet
            if req_topic:
                available_topics = [r["topic"] for r in c.execute("SELECT DISTINCT topic FROM questions WHERE stage=? AND active=1", (s_num,)).fetchall() if r["topic"]]
                if not chosen_topic or chosen_topic not in available_topics:
                    return jsonify({
                        "status": "topic_selection",
                        "stage": s_num,
                        "stage_title": f"STAGE {s_num}: {s_name.upper()}",
                        "available_topics": available_topics if available_topics else ["General"],
                        "current_score": current_score,
                        "message": f"Welcome to Stage {s_num}! Choose your specialization topic to begin."
                    })
                stage_qs = c.execute("SELECT * FROM questions WHERE stage=? AND topic=? AND active=1 ORDER BY id ASC", (s_num, chosen_topic)).fetchall()
            else:
                stage_qs = c.execute("SELECT * FROM questions WHERE stage=? AND active=1 ORDER BY id ASC", (s_num,)).fetchall()

            # Check if stage has questions and user is just entering this stage
            unanswered_qs = [q for q in stage_qs if q["id"] not in answered_ids]

            # If user has not acknowledged entering this stage (e.g. Stage 2, Stage 3 intermission)
            stage_ack_key = f"stage_{s_num}_started_{pid}"
            if s_num > 1 and len(unanswered_qs) == len(stage_qs) and not session.get(stage_ack_key):
                prev_stage_name = stages[stage_idx - 1]["name"] if stage_idx > 0 else f"Stage {s_num - 1}"
                return jsonify({
                    "status": "stage_intro",
                    "stage": s_num,
                    "stage_title": f"STAGE 0{s_num}: {s_name.upper()}",
                    "stage_name": s_name,
                    "prev_stage_name": prev_stage_name,
                    "question_count": len(stage_qs),
                    "current_score": current_score,
                    "message": f"Great job completing {prev_stage_name}! Ready for Stage {s_num}?"
                })

            # Find unanswered question in this stage
            for idx, q in enumerate(stage_qs):
                if q["id"] not in answered_ids:
                    session[f"q_delivered_{q['id']}"] = time.time()
                    return jsonify({
                        "status": "in_progress",
                        "stage": s_num,
                        "total_stages": len(stages),
                        "stage_title": f"STAGE {s_num}: {s_name.upper()}",
                        "topic": q["topic"],
                        "stage_index": idx + 1,
                        "stage_total": len(stage_qs),
                        "current_score": current_score,
                        "question": {
                            "id": q["id"], "question": q["question"],
                            "a": q["a"], "b": q["b"], "c": q["c"], "d": q["d"],
                            "points": q["points"], "seconds": q["seconds"]
                        }
                    })

        # All configured stages completed!
        return jsonify({
            "status": "completed",
            "current_score": current_score,
            "answered_count": answered_count,
            "chosen_topic": chosen_topic,
            "message": "All quiz stages completed successfully!"
        })

@app.route("/api/answer", methods=["POST"])
def answer():
    pid = session.get("participant_id")
    if not pid:
        return jsonify({"error": "Join the quiz first."}), 401

    if is_rate_limited(f"ans_{pid}", max_calls=6, period=3):
        return jsonify({"error": "Submission rate limit exceeded. Please wait a moment."}), 429

    data = request.json or {}
    qid = data.get("question_id")
    choice = str(data.get("choice", "")).lower()

    if choice not in ("a", "b", "c", "d", "timeout"):
        log_security_event(pid, "INVALID_CHOICE_PAYLOAD", f"Question: {qid}, Choice: {choice}")
        return jsonify({"error": "Invalid option."}), 400

    now = time.time()

    with db() as c:
        q = c.execute("SELECT * FROM questions WHERE id=? AND active=1", (qid,)).fetchone()
        if not q:
            return jsonify({"error": "Question not found."}), 404

        delivered_at = session.get(f"q_delivered_{qid}")
        if delivered_at:
            elapsed = now - delivered_at
            if elapsed > (q["seconds"] + 6) and choice != "timeout":
                choice = "timeout"
                log_security_event(pid, "LATE_SUBMISSION", f"QID: {qid}, Elapsed: {elapsed:.1f}s, Max allowed: {q['seconds']}s")
            elif elapsed < 0.3 and choice != "timeout":
                log_security_event(pid, "ABNORMAL_FAST_SUBMIT", f"QID: {qid}, Elapsed: {elapsed:.2f}s")

        correct = int(choice == q["answer"])
        points = q["points"] if correct else 0

        # Retrieve text of question and chosen option for direct readability in DB
        p_name = session.get("participant_name") or "Participant"
        q_text = q["question"]
        chosen_text = q[choice] if choice in ("a", "b", "c", "d") else "Timeout / Skipped"

        try:
            c.execute("""INSERT INTO responses(participant_id, participant_name, question_id, question_text, choice, selected_text, correct, points, answered_at)
                         VALUES(?,?,?,?,?,?,?,?,?)""",
                      (pid, p_name, qid, q_text, choice, chosen_text, correct, points, now))
        except Exception as e:
            log_security_event(pid, "DUPLICATE_OR_SUBMIT_ERROR", f"QID: {qid}, Err: {str(e)[:100]}")
            return jsonify({"error": "Answer already submitted or invalid."}), 409

    return jsonify({"ok": True, "correct": bool(correct), "points": points})

@app.route("/api/leaderboard")
@admin_required
def leaderboard():
    with db() as c:
        rows = c.execute("""
            SELECT p.id, p.name, p.email, p.team, p.chosen_topic,
                   COALESCE(SUM(r.points), 0) score,
                   COALESCE(SUM(r.correct), 0) correct,
                   COUNT(r.id) answered,
                   MIN(r.answered_at) first_answered,
                   MAX(r.answered_at) last_answered
            FROM participants p 
            LEFT JOIN responses r ON r.participant_id = p.id
            GROUP BY p.id 
            ORDER BY score DESC, correct DESC, last_answered ASC
            LIMIT 200
        """).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/admin/security-logs")
@admin_required
def security_logs_api():
    with db() as c:
        rows = c.execute("""
            SELECT l.id, l.event_type, l.details, l.created_at, p.name, p.email 
            FROM security_logs l 
            LEFT JOIN participants p ON p.id = l.participant_id 
            ORDER BY l.id DESC 
            LIMIT 100
        """).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/admin")
def admin_home():
    if "admin_email" not in session and "admin_id" not in session:
        return redirect(url_for("admin_login"))
    return redirect(url_for("dashboard"))

@app.route("/admin/login")
def admin_login():
    if session.get("admin_email") in ADMIN_EMAILS:
        return redirect(url_for("dashboard"))
    return render_template("admin_login.html")

@app.route("/admin/google-login", methods=["POST"])
def admin_google_login():
    email = request.form.get("email", "").strip().lower()
    name = request.form.get("name", "").strip() or "Admin"
    
    if email in ADMIN_EMAILS:
        session["admin_id"] = 1
        session["admin_email"] = email
        session["admin_username"] = name
        flash(f"Welcome, {name}! Admin access granted.", "success")
        return redirect(url_for("dashboard"))
    else:
        flash(f"Access Denied: '{email}' is not authorized to access the Admin Panel.", "error")
        return redirect(url_for("admin_login"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_email", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
@admin_required
def dashboard():
    with db() as c:
        stages = [dict(r) for r in c.execute("SELECT * FROM stages ORDER BY stage_num ASC").fetchall()]
        questions = [dict(r) for r in c.execute("SELECT * FROM questions ORDER BY stage ASC, topic ASC, id ASC").fetchall()]
        participants = c.execute("SELECT COUNT(*) n FROM participants").fetchone()["n"]
        total_responses = c.execute("SELECT COUNT(*) n FROM responses").fetchone()["n"]
        total_alerts = c.execute("SELECT COUNT(*) n FROM security_logs WHERE event_type != 'PARTICIPANT_JOINED'").fetchone()["n"]
        event_code = setting(c, "event_code", "TECH2026")
    return render_template("admin.html", 
                           stages=stages,
                           questions=questions, 
                           participants=participants, 
                           total_responses=total_responses,
                           total_alerts=total_alerts,
                           event_code=event_code)

# Stage Management Routes (Add Stage, Edit Stage, Delete Stage)
@app.route("/admin/stage", methods=["POST"])
@admin_required
def add_or_update_stage():
    stage_num = int(request.form.get("stage_num", "1"))
    name = request.form.get("name", "").strip()
    requires_topic_choice = 1 if request.form.get("requires_topic_choice") else 0
    if name:
        with db() as c:
            c.execute("INSERT INTO stages(stage_num, name, requires_topic_choice) VALUES(?,?,?) ON CONFLICT(stage_num) DO UPDATE SET name=excluded.name, requires_topic_choice=excluded.requires_topic_choice",
                      (stage_num, name, requires_topic_choice))
        flash(f"Stage {stage_num} ('{name}') saved successfully.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/stage/<int:snum>/delete", methods=["POST"])
@admin_required
def delete_stage(snum):
    with db() as c:
        c.execute("DELETE FROM stages WHERE stage_num=?", (snum,))
        c.execute("DELETE FROM questions WHERE stage=?", (snum,))
    flash(f"Stage {snum} and its associated questions deleted.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/settings/event-code", methods=["POST"])
@admin_required
def update_event_code():
    code = request.form.get("event_code", "").strip().upper()
    if code:
        with db() as c:
            set_setting(c, "event_code", code)
        flash(f"Event code updated to {code}", "success")
    else:
        flash("Event code cannot be empty.", "error")
    return redirect(url_for("dashboard"))

@app.route("/admin/question", methods=["POST"])
@admin_required
def add_question():
    stage = int(request.form.get("stage", "1"))
    topic = request.form.get("topic", "General").strip() or "General"
    q = request.form.get("question","").strip()
    opts = [request.form.get(k,"").strip() for k in ("a","b","c","d")]
    answer = request.form.get("answer","").lower()
    try:
        points = max(0, min(1000, int(request.form.get("points","10"))))
        seconds = max(5, min(300, int(request.form.get("seconds","25"))))
    except ValueError:
        points, seconds = 10, 25
    if q and all(opts) and answer in ("a","b","c","d"):
        with db() as c:
            c.execute("INSERT INTO questions(stage,topic,question,a,b,c,d,answer,points,seconds) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (stage,topic,q,*opts,answer,points,seconds))
        flash(f"Question added to Stage {stage} ({topic}).", "success")
    else:
        flash("Fill all question fields and select the correct answer.", "error")
    return redirect(url_for("dashboard"))

@app.route("/admin/question/<int:qid>/edit", methods=["POST"])
@admin_required
def edit_question(qid):
    stage = int(request.form.get("stage", "1"))
    topic = request.form.get("topic", "General").strip() or "General"
    q = request.form.get("question","").strip()
    opts = [request.form.get(k,"").strip() for k in ("a","b","c","d")]
    answer = request.form.get("answer","").lower()
    try:
        points = max(0, min(1000, int(request.form.get("points","10"))))
        seconds = max(5, min(300, int(request.form.get("seconds","25"))))
    except ValueError:
        points, seconds = 10, 25
    if q and all(opts) and answer in ("a","b","c","d"):
        with db() as c:
            c.execute("UPDATE questions SET stage=?, topic=?, question=?, a=?, b=?, c=?, d=?, answer=?, points=?, seconds=? WHERE id=?",
                      (stage, topic, q, *opts, answer, points, seconds, qid))
        flash("Question updated successfully.", "success")
    else:
        flash("Fill all question fields and select the correct answer.", "error")
    return redirect(url_for("dashboard"))

@app.route("/admin/question/<int:qid>/delete", methods=["POST"])
@admin_required
def delete_question(qid):
    with db() as c:
        c.execute("DELETE FROM responses WHERE question_id=?", (qid,))
        c.execute("DELETE FROM questions WHERE id=?", (qid,))
    flash("Question deleted.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/reset-scores", methods=["POST"])
@admin_required
def reset_scores():
    with db() as c:
        c.execute("DELETE FROM responses")
        c.execute("DELETE FROM security_logs")
        c.execute("DELETE FROM participants")
    flash("Complete reset successful: All participants, scores, and security logs have been wiped clean.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/participants")
@admin_required
def admin_participants():
    with db() as c:
        rows = c.execute("""
            SELECT p.name,p.email,p.team,p.chosen_topic,p.joined_at,COALESCE(SUM(r.points),0) score,
            COUNT(r.id) answered FROM participants p LEFT JOIN responses r ON r.participant_id=p.id
            GROUP BY p.id ORDER BY score DESC
        """).fetchall()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
else:
    # Auto-initialize database schema when running under production gunicorn
    try:
        init_db()
    except Exception as e:
        print(">>> [INIT_DB ERROR on Gunicorn startup]:", e)
