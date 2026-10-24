import os
from db_adapter import get_db

stage1_questions = [
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

def seed_stage1():
    with get_db() as c:
        # Delete old stage 1 sample questions so only these 25 official ones remain
        c.execute("DELETE FROM questions WHERE stage=1")
        c.executemany("""
            INSERT INTO questions(stage, topic, question, a, b, c, d, answer, points, seconds)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, stage1_questions)
        print(f"Successfully seeded {len(stage1_questions)} Stage 1 questions!")

if __name__ == "__main__":
    seed_stage1()
