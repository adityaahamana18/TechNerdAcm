import os
from db_adapter import get_db

# Official 25 Questions across 5 Topics for Stage 3 (Specialization Domain)
# 5 Questions per topic, 20 points each, 30 seconds timer
stage3_questions = [
    # Topic 1: Web Development
    (
        3,
        "Web Development",
        "Why is HTTP called a stateless protocol?",
        "It cannot transfer images or files.",
        "Each request is processed independently without automatically remembering previous requests.",
        "It works only without a database.",
        "It allows only one request per user.",
        "b",
        20,
        30
    ),
    (
        3,
        "Web Development",
        "A user logs in to a website and navigates to another page. How can the website recognize the user without asking for the password again?",
        "The browser automatically sends the password with every request.",
        "The website uses a session identifier, often stored in a cookie, to associate requests with the logged-in user.",
        "The HTML page permanently stores the user's identity.",
        "The IP address always uniquely identifies the logged-in user.",
        "b",
        20,
        30
    ),
    (
        3,
        "Web Development",
        "What is the primary purpose of the DOM in web development?",
        "To store passwords securely on the server.",
        "To convert JavaScript into machine code.",
        "To represent a web page as a structured object tree that scripts can access and modify.",
        "To establish a network connection between two servers.",
        "c",
        20,
        30
    ),
    (
        3,
        "Web Development",
        "A developer changes a CSS file, but the browser continues displaying the old design. Which explanation is most likely?",
        "CSS cannot be changed after a page loads.",
        "The browser may be using a cached version of the stylesheet.",
        "JavaScript has permanently disabled CSS.",
        "HTML does not support external stylesheets.",
        "b",
        20,
        30
    ),
    (
        3,
        "Web Development",
        "Why should a web application validate user input on the server even if JavaScript already validates it in the browser?",
        "Browser validation is always slower.",
        "Server-side validation prevents users from bypassing checks by modifying or skipping client-side code.",
        "JavaScript cannot check input fields.",
        "Server validation is required only for images.",
        "b",
        20,
        30
    ),

    # Topic 2: C++ Programming
    (
        3,
        "C++ Programming",
        "What is the output of this code? int x=10; int* p=&x; *p=20; cout<<x;",
        "10",
        "20",
        "Address of x",
        "Compilation error",
        "b",
        20,
        30
    ),
    (
        3,
        "C++ Programming",
        "Two pointers point to the same integer variable. If one pointer changes the variable's value, what happens when the other pointer dereferences it?",
        "It sees the updated value because both point to the same memory location.",
        "It sees the original value because pointers copy values.",
        "It becomes null automatically.",
        "The program always crashes.",
        "a",
        20,
        30
    ),
    (
        3,
        "C++ Programming",
        "What is the main risk of dereferencing a pointer after its dynamically allocated memory has been deleted?",
        "The pointer automatically allocates new memory.",
        "The pointer becomes a reference to a valid integer.",
        "The program may exhibit undefined behavior because the pointer is dangling.",
        "The compiler always detects and prevents it.",
        "c",
        20,
        30
    ),
    (
        3,
        "C++ Programming",
        "What is the difference between passing an integer by value and passing it by reference to a function?",
        "Both always modify the original integer.",
        "Passing by value gives the function a copy; passing by reference allows it to modify the original variable.",
        "Passing by reference creates a new independent variable.",
        "Passing by value is possible only for pointers.",
        "b",
        20,
        30
    ),
    (
        3,
        "C++ Programming",
        "What does a C++ constructor primarily do when an object is created?",
        "Deletes the object from memory.",
        "Initializes the object's state and establishes its initial invariants.",
        "Runs only when the program terminates.",
        "Converts every object into a pointer.",
        "b",
        20,
        30
    ),

    # Topic 3: Python Programming
    (
        3,
        "Python Programming",
        "What is printed? a=[1,2]; b=a; b.append(3); print(a)",
        "[1, 2]",
        "[1, 2, 3]",
        "[3]",
        "Error",
        "b",
        20,
        30
    ),
    (
        3,
        "Python Programming",
        "Why does a = a + [4] behave differently from a.append(4) when another variable b refers to the original list?",
        "The plus operator always modifies both variables.",
        "append creates a new list, while plus modifies the original list.",
        "The plus expression creates a new list and rebinds a, while append modifies the existing list object.",
        "Python variables cannot refer to the same list.",
        "c",
        20,
        30
    ),
    (
        3,
        "Python Programming",
        "What is the output? print(bool([]), bool([0]))",
        "True True",
        "False False",
        "False True",
        "True False",
        "c",
        20,
        30
    ),
    (
        3,
        "Python Programming",
        "What is the main benefit of using a dictionary to store student marks with unique roll numbers as keys?",
        "It automatically sorts marks in descending order.",
        "It can provide average constant-time key lookup, assuming a good hash distribution.",
        "It guarantees that every value is unique.",
        "It stores data only in alphabetical order.",
        "b",
        20,
        30
    ),
    (
        3,
        "Python Programming",
        "A function changes the contents of a list passed to it, but the caller's list also changes. What best explains this?",
        "Python passes every argument by copying the entire object.",
        "The function and caller can refer to the same mutable list object.",
        "Lists are immutable.",
        "The function executes in the caller's memory only if it is recursive.",
        "b",
        20,
        30
    ),

    # Topic 4: Data Structures & Algorithms (DSA)
    (
        3,
        "Data Structures & Algorithms (DSA)",
        "An unsorted array contains n elements. What is the worst-case time complexity of searching for a particular value?",
        "O(1)",
        "O(log n)",
        "O(n)",
        "O(n log n)",
        "c",
        20,
        30
    ),
    (
        3,
        "Data Structures & Algorithms (DSA)",
        "Which data structure is most suitable for implementing an undo operation in a text editor, where the most recent action must be undone first?",
        "Queue",
        "Stack",
        "Binary search tree",
        "Graph",
        "b",
        20,
        30
    ),
    (
        3,
        "Data Structures & Algorithms (DSA)",
        "A binary search is applied to a sorted array of 1,000 elements. Why is it generally faster than linear search for finding a value?",
        "It checks every element twice.",
        "It eliminates approximately half of the remaining search range at each step.",
        "It always starts from the last element.",
        "It converts the array into a linked list.",
        "b",
        20,
        30
    ),
    (
        3,
        "Data Structures & Algorithms (DSA)",
        "A queue is used to manage print jobs. Why is a queue a natural choice?",
        "It processes the newest job first.",
        "It processes jobs in the order they arrive, following FIFO.",
        "It sorts jobs by file size automatically.",
        "It allows only one job to be stored.",
        "b",
        20,
        30
    ),
    (
        3,
        "Data Structures & Algorithms (DSA)",
        "A hash table provides average O(1) lookup. What is a likely reason lookup may become O(n) in the worst case?",
        "The table contains integers.",
        "All keys are unique.",
        "Many keys collide into the same bucket and require additional searching.",
        "The table is accessed using a variable.",
        "c",
        20,
        30
    ),

    # Topic 5: Computer Networks
    (
        3,
        "Computer Networks",
        "Why does a computer need both an IP address and a MAC address to communicate across networks?",
        "IP addresses identify applications, while MAC addresses identify passwords.",
        "IP addresses support logical addressing and routing between networks, while MAC addresses identify interfaces for local-link delivery.",
        "MAC addresses are used only for wireless networks.",
        "IP addresses work only within a single LAN.",
        "b",
        20,
        30
    ),
    (
        3,
        "Computer Networks",
        "A laptop sends data to a server outside its local network. Which device's MAC address is typically used as the destination MAC in the first Ethernet frame?",
        "The remote server's MAC address, obtained directly from the internet.",
        "The laptop's own MAC address.",
        "The local router or default gateway's MAC address.",
        "The DNS server's MAC address in every case.",
        "c",
        20,
        30
    ),
    (
        3,
        "Computer Networks",
        "What is the main purpose of DNS?",
        "To encrypt all web traffic.",
        "To translate domain names into IP addresses or other DNS records.",
        "To assign a MAC address to every device.",
        "To guarantee that websites are free of malware.",
        "b",
        20,
        30
    ),
    (
        3,
        "Computer Networks",
        "What happens when a router forwards an IP packet from one network to another?",
        "The source and destination MAC addresses usually change for the next link, while the IP source and destination generally remain the same.",
        "The IP destination is always replaced by the router's IP address.",
        "The packet loses its IP addresses and uses only MAC addresses.",
        "The router changes the web page content.",
        "a",
        20,
        30
    ),
    (
        3,
        "Computer Networks",
        "Why is TCP commonly used for transferring files when reliable delivery is important?",
        "It guarantees the fastest possible speed in every situation.",
        "It provides mechanisms such as acknowledgments, retransmissions, and ordered byte delivery.",
        "It does not use ports.",
        "It works only within a local network.",
        "b",
        20,
        30
    )
]

def seed_stage3():
    with get_db() as c:
        # Delete old sample questions for stage 3
        c.execute("DELETE FROM questions WHERE stage=3")
        c.executemany("""
            INSERT INTO questions(stage, topic, question, a, b, c, d, answer, points, seconds)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, stage3_questions)
        print(f"Successfully seeded {len(stage3_questions)} Stage 3 questions across 5 topics!")

if __name__ == "__main__":
    seed_stage3()

