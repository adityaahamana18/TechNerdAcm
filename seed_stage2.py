import os
from db_adapter import get_db

stage2_questions = [
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

def seed_stage2():
    with get_db() as c:
        # Delete old stage 2 sample questions
        c.execute("DELETE FROM questions WHERE stage=2")
        c.executemany("""
            INSERT INTO questions(stage, topic, question, a, b, c, d, answer, points, seconds)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, stage2_questions)
        print(f"Successfully seeded {len(stage2_questions)} Stage 2 questions!")

if __name__ == "__main__":
    seed_stage2()

