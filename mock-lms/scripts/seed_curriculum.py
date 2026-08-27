"""Seed real curriculum/syllabus content into Mock LMS's own DB.

Ported from the FLM Learning Materials Portal prototype's mock data
(fpt-learning-materials-(flm-portal)/src/data/mock*.ts) into real rows —
this is the one-time load; app/curriculum_api.py then serves it from the DB,
nothing is hardcoded client-side any more. See app/models.py's Syllabus /
CurriculumProgram / PrerequisiteNode docstrings for why JSON columns.

Only CSI106 and SWE202c have full syllabus detail (materials/CLOs/sessions/
questions/assessments) — that's genuinely how much detail the source
content had, not something trimmed here. Every other subject in the
curriculum tree / prerequisite graph still gets a real row without a
Syllabus detail row; the frontend's syllabus search only lists subjects
that actually have one, rather than linking to a page that 404s.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import Base, ENGINE, SessionLocal  # noqa: E402
from app.models import CurriculumProgram, PrerequisiteNode, Syllabus  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "docs" / "planning" / "v2" / "data" / "courses_BIT_SE_K20D_K21A.json"

# The catalog (courses_BIT_SE_K20D_K21A.json) has no category field -- these
# are a one-time manual classification against FPT's actual Software
# Engineering curriculum structure (not auto-guessed), used for both the
# curriculum-framework badges and the prerequisite-graph nodes below. Combo/
# elective-slot codes (SE_COM*, PHE_COM*, PEN) are deliberately absent here,
# same exclusion as seed_courses.py's DISCOVERABLE_34 -- see that file's
# docstring for why.
SUBJECT_CATEGORY = {
    # Exactly the 36 codes seed_courses.py actually seeds a PlatformCourse
    # row for (DISCOVERABLE_34 + SSA101 + CSI106) -- deliberately NOT every
    # code the catalog mentions. The catalog also lists EXE101, SWT301,
    # SE_GRA_ELE etc. (real subjects in the program) that have no
    # data/clean docx and no chunks_*.json at all, so including them here
    # would put a curriculum-tree node in front of a syllabus link that can
    # only ever 404 -- same "don't link to a dead end" rule seed_courses.py
    # and seed_curriculum.py's own docstrings already apply elsewhere.
    "CSI106": "Foundation", "PRF192": "Foundation", "MAE101": "Foundation", "CEA201": "Foundation",
    "MAD101": "Foundation", "MAS291": "Foundation", "MLN111": "Foundation", "MLN122": "Foundation",
    "MLN131": "Foundation", "HCM202": "Foundation", "VNR202": "Foundation", "ITE302c": "Foundation",
    "PRO192": "Core", "OSG202": "Core", "NWC204": "Core", "WED201c": "Core", "DBI202": "Core",
    "LAB211": "Core", "SWE202c": "Core", "IOT102": "Core", "CSD201": "Core", "PRJ301": "Core",
    "SWR302": "Core",
    "PMG201c": "Specialized", "SWD392": "Specialized", "PRM393": "Specialized",
    "SWP391": "Specialized", "WDU203c": "Specialized", "OJT202": "Specialized",
    "OTP101": "Soft Skills", "SSA101": "Soft Skills", "JPD113": "Soft Skills", "JPD123": "Soft Skills",
    "SSG105": "Soft Skills", "ENW493c": "Soft Skills", "EXE201": "Soft Skills",
}
_COMBO_CODE_RE = re.compile(r"[*_]COM|^PEN$")
_CODE_TOKEN_RE = re.compile(r"[A-Z]{2,4}\d{2,3}[A-Za-z]?")


def _load_catalog() -> list[dict]:
    """Real official catalog (48 subjects, includes a genuine PreRequisite
    field for every one) -- see the module docstring: this replaces what
    used to be a hand-typed subject list with real semester/prerequisite
    data, filtered down to the subjects EduSync actually has course/syllabus
    rows for (same exclusion as seed_courses.py)."""
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    subjects = []
    for s in raw["subjects"]:
        code = s["Subject Code"]
        if _COMBO_CODE_RE.search(code) or code not in SUBJECT_CATEGORY:
            continue
        subjects.append(
            {
                "code": code,
                "name": s["Subject Name"].split("_")[0].strip(),
                "semester": int(s.get("Semester") or 0),
                "credits": int(s.get("NoCredit") or 0),
                "category": SUBJECT_CATEGORY[code],
                "prerequisite_raw": (s.get("PreRequisite") or "").strip(),
            }
        )
    return subjects


def _parse_prereq_codes(raw: str, known_codes: set[str]) -> list[str]:
    """Catalog prerequisite text is free-form ("Pass PRF192", "DBI202,
    PRO192", "SWE102 or SWE201c or SWE202c") rather than a code list --
    extracting every code-shaped token and keeping only ones that are
    actually seeded subjects handles "or"/"and"/"Pass " phrasing and old
    deprecated codes (e.g. SWE102, not offered any more) in one pass instead
    of a fragile string-split per phrasing variant."""
    if not raw or raw.strip().lower() in {"none", "n/a", "không"}:
        return []
    return sorted({m for m in _CODE_TOKEN_RE.findall(raw) if m in known_codes})

CSI106_SESSION_TOPICS = [
    "Orientation & Introduction to Computing Landscape",
    "Data Representation: Binary, Octal, Hexadecimal & Number Conversions",
    "Signed Integers: Sign-Magnitude, 1s Complement, 2s Complement Arithmetic",
    "Floating-Point Representation: IEEE 754 Standard & Precision Pitfalls",
    "Character Encodings: ASCII, Extended ASCII, Unicode UTF-8 & UTF-16",
    "Image, Audio & Video Digitalization: Sampling, Quantization, Compression",
    "Logic Gates & Boolean Algebra: AND, OR, NOT, XOR Truth Tables",
    "Combinational Circuits: Adders, Multiplexers, Decoders & Arithmetic Logic Units (ALU)",
    "Sequential Circuits: Flip-Flops, Registers, Synchronous Clocks & Memory Elements",
    "Von Neumann Architecture: Registers, Bus Architecture, Control Unit & ALU",
    "Machine Instruction Cycle: Fetch, Decode, Execute, Store & Clock Rates",
    "Assembly Language Foundations: Opcodes, Addressing Modes & Machine Code Mapping",
    "Memory Hierarchy: L1/L2/L3 Caches, SRAM, DRAM, Non-volatile Flash & ROM",
    "Cache Performance: Cache Hits, Misses, Direct Mapped vs Associative Mapping",
    "Secondary Storage & I/O Systems: Magnetic Disks, Solid State Drives (SSD), DMA Controllers",
    "Operating System Roles: Kernel vs User Space, System Calls, POSIX API",
    "Process Management: Process States, PCB, Context Switching, Forking",
    "CPU Scheduling Algorithms: FCFS, SJF, Round Robin, Multi-level Feedback Queues",
    "Process Synchronization: Race Conditions, Critical Section Problem, Mutex Locks & Semaphores",
    "Deadlocks: Coffman Conditions, Deadlock Prevention, Avoidance (Banker Algo) & Recovery",
    "Memory Management: Fixed Partitioning, Paging, Page Tables, Translation Lookaside Buffer (TLB)",
    "Virtual Memory & Page Replacement: Demand Paging, FIFO, LRU, Optimal Replacement",
    "File System Concepts: Inodes, FAT, NTFS, Ext4, Directory Hierarchies & Metadata",
    "Disk Scheduling: FCFS, SSTF, SCAN, C-SCAN Algorithms & RAID Levels (0, 1, 5, 10)",
    "Computer Networking Intro: LAN, WAN, Network Topologies & Internet Backbone",
    "OSI 7-Layer Model vs TCP/IP 4-Layer Architecture Comparison",
    "Physical & Data Link Layers: Framing, MAC Addresses, CSMA/CD, Ethernet Switches",
    "Network Layer: IPv4 vs IPv6 Addressing, Subnetting, CIDR, ARP Protocol",
    "Routing Principles: Distance Vector (RIP), Link State (OSPF), Autonomous Systems (BGP)",
    "Transport Layer: UDP vs TCP, 3-Way Handshake, Flow Control (Sliding Window), Congestion Control",
    "Application Layer: HTTP/1.1 vs HTTP/2, DNS Resolution Hierarchy, DHCP, SMTP/IMAP",
    "Network Security: Firewalls, NAT, TLS/SSL Handshake, VPN Tunneling",
    "Database Systems Intro: DBMS Architecture, Flat Files vs Relational Models",
    "Relational Data Model: Relations, Attributes, Primary Keys, Foreign Keys, Integrity Constraints",
    "Entity-Relationship Modeling: Entities, Relationships, Cardinality, ER-to-Relational Mapping",
    "Relational Algebra: Select, Project, Join, Union, Difference Operations",
    "SQL Basics: DDL (CREATE, ALTER, DROP) & DML (INSERT, UPDATE, DELETE)",
    "SQL Queries: SELECT, WHERE, GROUP BY, HAVING, ORDER BY, Aggregations",
    "SQL Advanced: INNER JOIN, LEFT/RIGHT OUTER JOIN, Subqueries & Views",
    "Database Normalization: 1NF, 2NF, 3NF, BCNF, Redundancy Elimination",
    "Algorithm Foundations: Problem Solving Strategies, Pseudocode & Flowcharts",
    "Algorithm Complexity: Asymptotic Notation, Worst-case, Best-case, Average-case Big-O",
    "Linear Search vs Binary Search: Analysis, Prerequisites & Divide-and-Conquer Paradigm",
    "Elementary Sorting: Bubble Sort, Selection Sort, Insertion Sort Mechanics",
    "Advanced Sorting: Merge Sort (Recursion Tree Analysis) & Quick Sort (Partitioning Strategies)",
    "Linear Data Structures: Arrays vs Linked Lists (Singly, Doubly Linked Memory Layout)",
    "Abstract Data Types: Stack (LIFO) & Queue (FIFO) Implementations & Applications",
    "Tree Structures: Binary Trees, Binary Search Trees (BST), Tree Traversals (Pre, In, Post-order)",
    "Graph Representations: Adjacency Matrix vs Adjacency List, BFS vs DFS Traversals",
    "Programming Paradigms: Imperative, Procedural, Object-Oriented, Functional Overview",
    "Control Structures & Modular Functions: Parameter Passing by Value vs by Reference",
    "Exception Handling & Defensive Programming: Try-Catch-Finally, Unit Testing Concepts",
    "Software Engineering Lifecycle: Requirements, Design, Implementation, Testing, Deployment",
    "Development Methodologies: Waterfall vs Agile (Scrum, Sprints, Daily Standup, Retrospective)",
    "Software Quality Assurance: Black-box vs White-box Testing, Code Reviews, CI/CD Pipelines",
    "Cybersecurity Fundamentals: CIA Triad (Confidentiality, Integrity, Availability), Threats & Vulnerabilities",
    "Cryptography: Symmetric Ciphers (AES, DES) vs Asymmetric Ciphers (RSA, ECC), Digital Signatures",
    "Artificial Intelligence & Machine Learning: Supervised, Unsupervised, Reinforcement Learning",
    "Ethics, Intellectual Property, Privacy Laws (GDPR) & ACM/IEEE Professional Code of Conduct",
    "Final Course Review, Comprehensive Project Presentation & Final Exam Preparation",
]


def _csi106_sessions() -> list[dict]:
    sessions = []
    for idx in range(60):
        s_num = idx + 1
        clo_idx = min(13, (idx * 13) // 60 + 1)
        is_online = s_num % 3 != 0
        sessions.append(
            {
                "sessionNo": s_num,
                "topic": CSI106_SESSION_TOPICS[idx] if idx < len(CSI106_SESSION_TOPICS) else f"Session {s_num}: Advanced Computing Principles",
                "type": ("Offline,Online" if s_num % 6 == 0 else "Online") if is_online else "Offline",
                "lo": f"LO{clo_idx}",
                "itu": ["I", "T", "U", "U"][idx % 4],
                "studentMaterials": f"Brookshear Ch. {idx // 5 + 1}, Course Slides #{s_num}",
                "sDownload": f"https://flm.fpt.edu.vn/materials/CSI106/Session_{s_num}_Handout.pdf",
                "studentTasks": (
                    f"- Read assigned textbook chapter & review Session {s_num} interactive slides\n"
                    "- Complete practical quiz & laboratory programming tasks on Coursera / Lab Portal\n"
                    "- Participate in slot discussion forum and prepare constructive question answer."
                ),
                "urls": f"https://flm.fpt.edu.vn/courses/CSI106/sessions/{s_num}",
            }
        )
    return sessions


CSI106_QUESTIONS = [
    "What is the fundamental difference between hardware architecture and software abstraction?",
    "Why do modern computers rely on the binary base-2 system instead of decimal base-10?",
    "How does 2s complement arithmetic eliminate the dual representation of zero present in 1s complement?",
    "Explain why 0.1 + 0.2 does not precisely equal 0.3 in IEEE 754 floating-point standards.",
    "How does UTF-8 maintain backward compatibility with 7-bit ASCII while supporting global characters?",
    "What is the Nyquist-Shannon sampling theorem and how does it determine audio digitization rates?",
    "Demonstrate how an XOR gate can be constructed solely from NAND gates.",
    "Why is a Full Adder necessary over a Half Adder when chaining multi-bit arithmetic?",
    "What distinguishes a flip-flop circuit from a simple logic gate in terms of clock state memory?",
    "What is the Von Neumann bottleneck and how do modern multi-core caches alleviate it?",
    "Trace what happens to the Program Counter (PC) and Instruction Register (IR) during an instruction fetch.",
    "Why are compiled high-level languages faster than interpreted languages in CPU execution cycles?",
    "Explain the principle of Locality of Reference (Spatial and Temporal Locality) in memory caching.",
    "What are the trade-offs between Direct Mapped Cache and Fully Associative Cache in terms of hardware cost and miss rates?",
    "How does Direct Memory Access (DMA) free up the CPU during heavy disk I/O operations?",
    "What hardware mechanism enforces the distinction between Kernel Mode (Ring 0) and User Mode (Ring 3)?",
    "What critical information is preserved inside a Process Control Block (PCB) during a context switch?",
    "Why is Shortest Job First (SJF) optimal for average waiting time, and why is it difficult to implement in real OS kernels?",
    "Describe how a race condition occurs between two threads incrementing a shared global variable.",
    "State the four necessary conditions for deadlock to occur according to Coffmans theorem.",
    "Explain the role of the Translation Lookaside Buffer (TLB) in speeding up virtual-to-physical address translation.",
    "What is Beladys Anomaly and which page replacement algorithms are immune to it?",
    "How does an Inode structure in UNIX-like file systems reference large files exceeding direct blocks?",
    "Compare RAID 1 (Mirroring) and RAID 5 (Striping with Parity) in terms of read speed, write penalty, and storage efficiency.",
    "Explain packet switching vs circuit switching: why did the Internet adopt packet switching?",
    "Which OSI layer is responsible for end-to-end reliability, and how does it differ from hop-by-hop reliability?",
    "How does an Ethernet switch learn MAC addresses dynamically and prevent broadcast storms?",
    "Calculate the valid host range and broadcast address for subnet 192.168.10.0/27.",
    "How does the Dijkstra shortest-path algorithm function inside OSPF Link-State routing protocol?",
    "Why does TCP require a 3-way handshake (SYN, SYN-ACK, ACK) before transmitting payload data?",
    "Explain how recursive DNS resolution works from the Root Servers down to Authoritative Nameservers.",
    "Describe the key exchange process in TLS/SSL handshake and how asymmetric encryption establishes symmetric session keys.",
    "Why do relational databases enforce ACID properties (Atomicity, Consistency, Isolation, Durability)?",
    "What is the purpose of foreign key referential integrity in relational schemas?",
    "Translate a Many-to-Many entity relationship into relational tables using a junction/bridge table.",
    "What is the difference between WHERE and HAVING clauses in an SQL aggregation query?",
    "Explain why database tables should typically achieve Third Normal Form (3NF).",
    "Compare the time complexity of Quick Sort in average case O(N log N) vs worst case O(N^2).",
    "How does a Hash Table achieve O(1) average lookup time and what are two strategies for collision resolution?",
    "What are the differences between Agile Scrum sprints and traditional Waterfall milestones in project risk management?",
    "How does the IEEE/ACM Code of Ethics guide engineers when pressured to release untested or privacy-violating software?",
]


def _csi106_syllabus() -> dict:
    return {
        "subject_code": "CSI106",
        "syllabus_id": 14224,
        "syllabus_name": "Introduction to Computer Science_Nhập môn Khoa học Máy tính",
        "course_name_english": "Introduction to Computer Science",
        "learning_teaching_method": "Blended, Online, Active learning, Inquiry-based Teaching",
        "no_credit": 3,
        "degree_level": "Bachelor",
        "time_allocation": "Study hour (150h) = 60h online + 30h offline + 2h PE + 2h TE + 56h self-study",
        "pre_requisite": "None (Prerequisite for SWE202c, PRN211, CSD201)",
        "description": (
            "CSI106 provides foundational concepts of computing systems, binary logic, computer "
            "architecture, algorithms, data structures, networks, operating systems, and basic "
            "programming concepts.\n\nAt the end of this course, we expect learners to be able to:\n"
            "1.) Understand fundamental architecture of computers and digital logic representation.\n"
            "2.) Explain how high-level software interacts with hardware and operating system kernels.\n"
            "3.) Apply algorithm thinking and modular problem solving using modern programming syntax.\n"
            "4.) Adhere to ethical standards, cybersecurity hygiene, and software engineering principles."
        ),
        "student_tasks": (
            "Students must complete all weekly video modules, pass 4 online lab milestones, "
            "participate in offline discussion sessions, and pass final theoretical and practical exams."
        ),
        "tools": "Python 3.11+, VS Code, Terminal / Bash simulator, Wireshark demo",
        "scoring_scale": 10,
        "decision_no": "444/QĐ-ĐHFPT",
        "approved_date": "04/23/2026",
        "is_active": True,
        "is_approved": True,
        "materials": [
            {"no": 1, "description": "Computer Science: An Overview (13th Edition)", "author": "Glenn Brookshear, Dennis Brylow", "publisher": "Pearson Education", "publishedDate": "2019", "edition": "13th", "isbn": "978-0134875460", "isMain": True, "isHardCopy": True, "isOnline": True, "note": "Main textbook for 60 sessions and theory exams"},
            {"no": 2, "description": "Foundations of Computer Science (4th Edition)", "author": "Behrouz A. Forouzan, Firouz Mosharraf", "publisher": "Cengage Learning", "publishedDate": "2018", "edition": "4th", "isbn": "978-1473751040", "isMain": False, "isHardCopy": True, "isOnline": True, "note": "Reference material for digital logic and networking"},
            {"no": 3, "description": "FPT University CSI106 Interactive Lab Workbook & Guide", "author": "FPT University Software Engineering Dept", "publisher": "FPT Education Publishing", "publishedDate": "2025", "edition": "2025.2", "isbn": "N/A", "isMain": True, "isHardCopy": False, "isOnline": True, "note": "Hands-on practice exercises & Constructive Question bank"},
            {"no": 4, "description": "Introduction to Computation and Programming Using Python", "author": "John V. Guttag", "publisher": "MIT Press", "publishedDate": "2021", "edition": "3rd", "isbn": "978-0262542364", "isMain": False, "isHardCopy": False, "isOnline": True, "note": "Supplemental programming paradigms"},
        ],
        "clos": [
            {"no": 1, "cloName": "CLO1", "details": "Describe how data (integers, floats, text, multimedia) is encoded in binary logic."},
            {"no": 2, "cloName": "CLO2", "details": "Analyze Von Neumann architecture, CPU execution cycles, cache hierarchy and storage memory."},
            {"no": 3, "cloName": "CLO3", "details": "Explain process scheduling, virtual memory, file systems, and concurrency in operating systems."},
            {"no": 4, "cloName": "CLO4", "details": "Explain OSI and TCP/IP network layers, routing principles, DNS, and IP packet transmission."},
            {"no": 5, "cloName": "CLO5", "details": "Understand core database concepts: relational tables, normalization, and basic SQL query execution."},
            {"no": 6, "cloName": "CLO6", "details": "Formulate pseudocode and flowchart algorithms for sorting, searching, and recursion."},
            {"no": 7, "cloName": "CLO7", "details": "Calculate asymptotic complexity (Big-O notation) for standard computational algorithms."},
            {"no": 8, "cloName": "CLO8", "details": "Implement modular script logic using functions, conditionals, loops, and structured data."},
            {"no": 9, "cloName": "CLO9", "details": "Recognize security vulnerabilities (phishing, malware, buffer overflow) and basic cryptography (RSA, AES)."},
            {"no": 10, "cloName": "CLO10", "details": "Identify software engineering lifecycle phases (Agile, Waterfall) and quality assurance testing."},
            {"no": 11, "cloName": "CLO11", "details": "Assess artificial intelligence foundations: machine learning versus heuristic search algorithms."},
            {"no": 12, "cloName": "CLO12", "details": "Demonstrate collaborative teamwork and structured code presentation in technical reports."},
            {"no": 13, "cloName": "CLO13", "details": "Uphold academic honesty and professional ethics according to IEEE/ACM codes of conduct."},
        ],
        "sessions": _csi106_sessions(),
        "questions": [
            {"no": i + 1, "sessionNo": i + 1, "question": q}
            for i, q in enumerate(CSI106_QUESTIONS)
        ],
        "assessments": [
            {"no": 1, "category": "Lab Progress", "type": "Progress Assessment", "part": 1, "weight": 15.0, "completionCriteria": "Score >= 5.0/10", "duration": "Ongoing (Weeks 1-8)", "clo": "CLO1, CLO6, CLO8", "questionType": "Practical coding & labs", "noQuestion": 4, "knowledgeAndSkill": "Binary conversions, logic simulations, Python basic algorithm scripts.", "gradingGuide": "Automated test suite + Lecturer verification", "note": "Submitted on Lab Portal weekly"},
            {"no": 2, "category": "Assignment", "type": "Individual Milestone", "part": 1, "weight": 15.0, "completionCriteria": "Score >= 5.0/10", "duration": "120 min", "clo": "CLO2, CLO4, CLO5, CLO10", "questionType": "Case study report & SQL script", "noQuestion": 2, "knowledgeAndSkill": "Network subnetting design, relational database schema and normalization.", "gradingGuide": "Standard Grading Rubric v2.1", "note": "Deadline: End of Week 5 (Synchable from Cursus/Mock LMS)"},
            {"no": 3, "category": "Practical Exam (PE)", "type": "Practical Final Exam", "part": 1, "weight": 30.0, "completionCriteria": "Score >= 4.0/10 (Mandatory threshold)", "duration": "90 min", "clo": "CLO6, CLO7, CLO8", "questionType": "Live Computer programming", "noQuestion": 3, "knowledgeAndSkill": "Implement searching, sorting, and file I/O algorithms under proctored IDE.", "gradingGuide": "Exam Board Automated Evaluation", "note": "Strict anti-cheat proctored session"},
            {"no": 4, "category": "Theory Exam (FE)", "type": "Final Theory Exam", "part": 1, "weight": 40.0, "completionCriteria": "Score >= 4.0/10 (Mandatory threshold)", "duration": "60 min", "clo": "CLO1, CLO2, CLO3, CLO4, CLO9, CLO11, CLO13", "questionType": "Multiple Choice Computer Gradable", "noQuestion": 50, "knowledgeAndSkill": "All studied theoretical modules, operating systems, security and computer ethics.", "gradingGuide": "Central Exam Board Grading Machine", "note": "Customized from Constructive Questions and Question Bank"},
        ],
    }


def _swe201c_syllabus() -> dict:
    coursera_sessions = [
        ("Specialization Introduction\nSoftware Development Processes and Methodologies:\n- Software development processes: Part 1\nOffline 1: Introduction to the online course SWE202c", "Offline,Online", "LO1", "https://www.coursera.org/learn/software-processes"),
        ("- Software Development Processes : Part 2", "Online", "LO1", "https://www.coursera.org/learn/software-processes"),
        ("- Software Development Models: Traditional Models", "Online", "LO1", "https://www.coursera.org/learn/software-processes"),
        ("- Software Development Models: Agile and Lean", "Online", "LO1", "https://www.coursera.org/learn/software-processes"),
        ("Agile Software Development:\n- Agile Fundamentals\n- Requirements and Planning", "Online", "LO2", "https://www.coursera.org/learn/agile-software-development"),
        ("- Scrum\n- XP and Course Wrap-up", "Online", "LO2", "https://www.coursera.org/learn/agile-software-development"),
        ("Lean Software Development:\n- Lean Fundamentals\n- Kanban, Value Steam Mapping and Kaizen", "Online", "LO4", "https://www.coursera.org/learn/lean-software-development"),
        ("- Lean Startup\n- Design Thinking", "Online", "LO3", "https://www.coursera.org/learn/lean-software-development"),
        ("Engineering Practices for Building Quality Software:\n- Introduction to Quality Software\n- Quality in Design", "Online", "LO4", "https://www.coursera.org/learn/engineering-practices-secure-software-quality"),
        ("- Quality in Architecture", "Online", "LO4", "https://www.coursera.org/learn/engineering-practices-secure-software-quality"),
        ("- Quality in Implementation", "Online", "LO4", "https://www.coursera.org/learn/engineering-practices-secure-software-quality"),
        ("- Quality in Testing and Deployment\nOffline 2: Review Software Development Lifecycle Specialization", "Offline,Online", "LO4", "https://www.coursera.org/specializations/software-development-lifecycle"),
    ]
    sessions = [
        {
            "sessionNo": i + 1,
            "topic": topic,
            "type": type_,
            "lo": lo,
            "studentTasks": (
                "- Watch all videos, read all materials in the MOOC\n"
                "- Finish quizzes, self-assessment, assignments and take part in discussion boards (if needed)"
                + ("\nAll students should participate in offline slot (if any question)" if i == 0 else "")
                + ("\nDeadline of Coursera completion: End of Friday of the week.\nAll students should participate in review slot (if any question)" if i == 11 else "")
            ),
            "urls": url,
        }
        for i, (topic, type_, lo, url) in enumerate(coursera_sessions)
    ]
    return {
        "subject_code": "SWE202c",
        "syllabus_id": 13769,
        "syllabus_name": "Introduction to Software Engineering_Nhập môn kỹ thuật phần mềm",
        "course_name_english": "Introduction to Software Engineering",
        "learning_teaching_method": "Blended, Online, Active learning, Inquiry-based Teaching",
        "no_credit": 3,
        "degree_level": "Bachelor",
        "time_allocation": "Study hour (150h) = 62h online + 3h offline + 1h TE + 2h PE + 82 h self-study",
        "pre_requisite": "PRO192 (not applied to the BIT_AI; BIT_IC; BIT_AS and BA programs)",
        "description": (
            "SWE202c is for people who are new to software engineering. It's also for those who have "
            "already developed software, but wish to gain a deeper understanding of the underlying "
            "context and theory of software development practices.\n\nAt the end of this course, we "
            "expect learners to be able to:\n"
            "1.) Build high-quality and secure software using SDLC methodologies such as agile, lean, "
            "and traditional/waterfall.\n"
            "2.) Analyze a software development team's SDLC methodology and make recommendations for "
            "improvements.\n"
            "3.) Compare and contrast software development methodologies with respect to environmental, "
            "organizational, and product constraints."
        ),
        "student_tasks": "Student must get the certification of Software Development Lifecycle specialization from Coursera to be accepted to the final examination",
        "tools": "Coursera platform, Jira/Trello, Git/GitHub, PlantUML",
        "scoring_scale": 10,
        "decision_no": "444/QĐ-ĐHFPT",
        "approved_date": "4/23/2026",
        "is_active": True,
        "is_approved": True,
        "materials": [
            {"no": 1, "description": "https://learner.coursera.help/hc/en-us/articles/208280036-Coursera-Code-of-Conduct", "author": "Coursera", "publisher": "Coursera", "publishedDate": "", "edition": "", "isbn": "", "isMain": False, "isHardCopy": False, "isOnline": True, "note": ""},
            {"no": 2, "description": "https://www.coursera.org/learn/software-processes", "author": "Coursera", "publisher": "Coursera", "publishedDate": "", "edition": "", "isbn": "", "isMain": True, "isHardCopy": False, "isOnline": True, "note": "MOOC 01: Software Development Processes and Methodologies"},
            {"no": 3, "description": "https://www.coursera.org/learn/agile-software-development", "author": "Coursera", "publisher": "Coursera", "publishedDate": "", "edition": "", "isbn": "", "isMain": True, "isHardCopy": False, "isOnline": True, "note": "MOOC 02: Agile Software Development"},
            {"no": 4, "description": "https://www.coursera.org/learn/lean-software-development", "author": "Coursera", "publisher": "Coursera", "publishedDate": "", "edition": "", "isbn": "", "isMain": True, "isHardCopy": False, "isOnline": True, "note": "MOOC 03: Lean Software Development"},
            {"no": 5, "description": "https://www.coursera.org/learn/engineering-practices-secure-software-quality", "author": "Coursera", "publisher": "Coursera", "publishedDate": "", "edition": "", "isbn": "", "isMain": True, "isHardCopy": False, "isOnline": True, "note": "MOOC 04: Engineering Practices for Building Quality Software"},
            {"no": 6, "description": "https://www.coursera.org/specializations/software-development-lifecycle", "author": "Coursera", "publisher": "Coursera", "publishedDate": "", "edition": "", "isbn": "", "isMain": True, "isHardCopy": False, "isOnline": True, "note": "SPEC: Software Development Lifecycle"},
        ],
        "clos": [
            {"no": 1, "cloName": "CLO1", "details": "Compare and contrast software development methodologies with respect to environmental, organizational, and product constraints."},
            {"no": 2, "cloName": "CLO2", "details": "Demonstrate the ability to participate effectively in agile practices/process for software development."},
            {"no": 3, "cloName": "CLO3", "details": "Apply lean techniques / methods to software development"},
            {"no": 4, "cloName": "CLO4", "details": "Comfortably and effectively participate in various techniques and processes for building secure and high quality software."},
        ],
        "sessions": sessions,
        "questions": [],
        "assessments": [
            {"no": 1, "category": "PE", "type": "Final exam", "part": 1, "weight": 40.0, "completionCriteria": "4", "duration": "120'", "clo": "", "questionType": "", "knowledgeAndSkill": "All studied courses.", "gradingGuide": "by Exam Board", "note": "Customized from the exercises of this specialization."},
            {"no": 2, "category": "TE", "type": "Final exam", "part": 1, "weight": 60.0, "completionCriteria": "4", "duration": "60'", "clo": "", "questionType": "Computer gradable", "noQuestion": 50, "knowledgeAndSkill": "All studied courses. Each module of course contributes 2-3 questions.", "gradingGuide": "by Exam Board", "note": "Customized from the quizzes of this specialization."},
        ],
    }


SUBJECT = lambda code, name, credits, semester, category, prerequisite, syllabus_id: {  # noqa: E731
    "code": code, "name": name, "credits": credits, "semester": semester,
    "category": category, "prerequisite": prerequisite, "syllabusId": syllabus_id, "isActive": True,
}

CURRICULUM_PROGRAMS = [
    {
        "code": "BIT_SE_K20D_K21A",
        "name": "Software Engineering (Kỹ thuật Phần mềm)",
        "faculty": "Faculty of Information Technology",
        "decision_no": "1318/QĐ-ĐHFPT",
        "effective_year": "2025-2029",
        "total_credits": 146,
        "description": "Chương trình đào tạo Kỹ sư Kỹ thuật phần mềm chuẩn ABET & CDIO, cung cấp kiến thức nền tảng khoa học máy tính, quy trình phát triển Agile/DevOps, kiến trúc hệ thống phân tán và đồ án tốt nghiệp thực chiến doanh nghiệp (OJT).",
        "semesters": [
            {"semesterNo": 1, "title": "Học kỳ 1 (Preparation & Foundations)", "subjects": [
                SUBJECT("CSI106", "Introduction to Computer Science", 3, 1, "Foundation", "None", 14224),
                SUBJECT("PRF192", "Programming Fundamentals with C", 3, 1, "Foundation", "None", 1012),
                SUBJECT("MAE101", "Mathematics for Engineering", 3, 1, "Foundation", "None", 1005),
                SUBJECT("CEA201", "Computer Organization and Architecture", 3, 1, "Foundation", "None", 1008),
                SUBJECT("ENW493c", "Academic English Writing", 3, 1, "Soft Skills", "None", 1002),
            ]},
            {"semesterNo": 2, "title": "Học kỳ 2 (Core Programming & Data Structures)", "subjects": [
                SUBJECT("PRO192", "Object-Oriented Programming (Java)", 3, 2, "Core", "PRF192", 1045),
                SUBJECT("MAD101", "Discrete Mathematics", 3, 2, "Foundation", "MAE101", 1018),
                SUBJECT("OSG202", "Operating Systems", 3, 2, "Core", "CSI106", 1033),
                SUBJECT("NWC204", "Computer Networking (CCNA1)", 3, 2, "Core", "CSI106", 1029),
                SUBJECT("SSG105", "Communication and In-Group Skills", 3, 2, "Soft Skills", "None", 1007),
            ]},
            {"semesterNo": 3, "title": "Học kỳ 3 (Algorithms, Databases & Web Foundations)", "subjects": [
                SUBJECT("CSD201", "Data Structures and Algorithms with Java", 3, 3, "Core", "PRO192", 1102),
                SUBJECT("DBI202", "Database Systems & SQL Design", 3, 3, "Core", "CSI106", 1115),
                SUBJECT("MAS291", "Statistics and Probability", 3, 3, "Foundation", "MAE101", 1108),
                SUBJECT("WED201c", "Web Design (HTML5, CSS3, Responsive)", 3, 3, "Core", "PRF192", 1120),
                SUBJECT("IOT102", "Internet of Things Fundamentals", 3, 3, "Core", "CEA201", 1124),
            ]},
            {"semesterNo": 4, "title": "Học kỳ 4 (Software Engineering & Enterprise Web/Mobile)", "subjects": [
                SUBJECT("SWE202c", "Introduction to Software Engineering", 3, 4, "Core", "CSI106, PRO192", 13769),
                SUBJECT("PRN211", "Basic Cross-Platform App with .NET/C#", 3, 4, "Specialized", "PRO192, DBI202", 1205),
                SUBJECT("PRJ301", "Java Web Application Development (JSP/Servlet/Spring)", 3, 4, "Specialized", "PRO192, DBI202", 1210),
                SUBJECT("JPD113", "Elementary Japanese 1-A1.1", 3, 4, "Soft Skills", "None", 1230),
            ]},
            {"semesterNo": 5, "title": "Học kỳ 5 (Project Management & Full-Stack Development)", "subjects": [
                SUBJECT("SWP391", "Software Development Project (Agile/Scrum)", 3, 5, "Specialized", "SWE202c, PRN211 / PRJ301", 1301),
                SUBJECT("SWR302", "Software Requirement Engineering", 3, 5, "Specialized", "SWE202c", 1305),
                SUBJECT("SWT301", "Software Testing & Automation (Selenium, JUnit)", 3, 5, "Specialized", "SWE202c", 1308),
                SUBJECT("PRN221", "Advanced Cross-Platform .NET (Blazor, WebAPI, Microservices)", 3, 5, "Specialized", "PRN211", 1312),
                SUBJECT("JPD123", "Elementary Japanese 1-A1.2", 3, 5, "Soft Skills", "JPD113", 1330),
            ]},
            {"semesterNo": 6, "title": "Học kỳ 6 (On-the-Job Training / Doanh nghiệp thực tập)", "subjects": [
                SUBJECT("OJT202", "On the Job Training (4-Month Fulltime Internship at IT Enterprise)", 10, 6, "Specialized", "SWP391 (Passed 72+ credits)", 1400),
            ]},
            {"semesterNo": 7, "title": "Học kỳ 7 (Software Architecture & Cloud Native)", "subjects": [
                SUBJECT("SWD392", "Software Architecture and Design Patterns", 3, 7, "Specialized", "SWP391, OJT202", 1502),
                SUBJECT("PRM393", "Mobile Programming (React Native / Flutter / Android)", 3, 7, "Specialized", "PRN211 / PRJ301", 1510),
                SUBJECT("WDM201", "Cloud Computing & DevOps (AWS/GCP, Docker, K8s)", 3, 7, "Specialized", "NWC204, OSG202", 1515),
                SUBJECT("MLN111", "Marxist-Leninist Philosophy", 3, 7, "Foundation", "None", 1520),
            ]},
            {"semesterNo": 8, "title": "Học kỳ 8 (Advanced Electives & Pre-Graduation)", "subjects": [
                SUBJECT("SWX301", "Enterprise Application Security & Secure Coding", 3, 8, "Specialized", "SWD392", 1601),
                SUBJECT("AIL302m", "Applied AI & LLM Engineering for SE", 3, 8, "Elective", "MAS291, PRO192", 1608),
                SUBJECT("PMG201c", "Project Management & Risk Assessment", 3, 8, "Core", "SWP391", 1612),
                SUBJECT("VNR202", "Vietnamese Revolutionary Path & Ho Chi Minh Ideology", 3, 8, "Foundation", "MLN111", 1620),
            ]},
            {"semesterNo": 9, "title": "Học kỳ 9 (Graduation Capstone Project / Khóa luận)", "subjects": [
                SUBJECT("SEP490", "Software Engineering Graduation Capstone Project (16 Weeks)", 10, 9, "Capstone", "Passed all Semesters 1-8 (120+ credits)", 1999),
            ]},
        ],
    },
    {
        "code": "BIT_IA_K20D",
        "name": "Information Assurance (An toàn Thông tin)",
        "faculty": "Faculty of Information Technology",
        "decision_no": "1319/QĐ-ĐHFPT",
        "effective_year": "2025-2029",
        "total_credits": 146,
        "description": "Chương trình Kỹ sư An toàn thông tin, bảo mật mạng, kiểm thử xâm nhập (Penetration Testing), mật mã học và bảo mật đám mây.",
        "semesters": [
            {"semesterNo": 1, "title": "Học kỳ 1 (Preparation & Foundations)", "subjects": [
                SUBJECT("CSI106", "Introduction to Computer Science", 3, 1, "Foundation", "None", 14224),
                SUBJECT("PRF192", "Programming Fundamentals with C", 3, 1, "Foundation", "None", 1012),
                SUBJECT("MAE101", "Mathematics for Engineering", 3, 1, "Foundation", "None", 1005),
                SUBJECT("CEA201", "Computer Organization and Architecture", 3, 1, "Foundation", "None", 1008),
            ]},
        ],
    },
    {
        "code": "BIT_AI_K20D",
        "name": "Artificial Intelligence (Trí tuệ Nhân tạo)",
        "faculty": "Faculty of Information Technology",
        "decision_no": "1320/QĐ-ĐHFPT",
        "effective_year": "2025-2029",
        "total_credits": 146,
        "description": "Chương trình đào tạo Kỹ sư AI & Khoa học dữ liệu, Machine Learning, Deep Learning, Computer Vision và Generative AI.",
        "semesters": [
            {"semesterNo": 1, "title": "Học kỳ 1 (Preparation & Foundations)", "subjects": [
                SUBJECT("CSI106", "Introduction to Computer Science", 3, 1, "Foundation", "None", 14224),
                SUBJECT("PRF192", "Programming Fundamentals with C", 3, 1, "Foundation", "None", 1012),
                SUBJECT("MAE101", "Mathematics for Engineering", 3, 1, "Foundation", "None", 1005),
            ]},
        ],
    },
]

def _build_prerequisite_nodes() -> list[dict]:
    """Generated from the real catalog (see _load_catalog/_parse_prereq_codes
    above) instead of hand-typed -- this is what took the prerequisite-map
    flow from 11 hand-typed nodes (6 of them pointing at wrong/nonexistent
    codes -- see this file's rename history) to every one of the 36 subjects
    EduSync actually has course data for, each with its REAL prerequisite
    text parsed rather than guessed. isPrerequisiteOf is the computed
    inverse of every other node's `prerequisites`, so it can never drift out
    of sync with them the way two independently hand-typed lists did before.

    Six SE-major-specific subjects from the old hand-typed list (PRN211,
    PRN221, SWX301, WDM201, AIL302m, SEP490) are NOT regenerated here: none
    of them has a `data/clean` docx, a parsed chunks file, or a seeded
    PlatformCourse row (verified directly, not assumed) -- keeping them
    would add graph nodes whose "view full syllabus" link 404s, the exact
    thing this file's own docstrings elsewhere say to avoid.
    """
    known_codes = set(SUBJECT_CATEGORY)
    subjects = {s["code"]: s for s in _load_catalog()}

    prereqs_by_code = {
        code: _parse_prereq_codes(s["prerequisite_raw"], known_codes) for code, s in subjects.items()
    }
    is_prereq_of: dict[str, list[str]] = {code: [] for code in subjects}
    for code, prereqs in prereqs_by_code.items():
        for p in prereqs:
            is_prereq_of[p].append(code)

    return [
        {
            "code": code,
            "name": s["name"],
            "semester": s["semester"],
            "credits": s["credits"],
            "category": s["category"],
            "prerequisites": prereqs_by_code[code],
            "isPrerequisiteOf": sorted(is_prereq_of[code]),
        }
        for code, s in subjects.items()
    ]


def main() -> None:
    Base.metadata.create_all(bind=ENGINE)
    prerequisite_nodes = _build_prerequisite_nodes()
    db = SessionLocal()
    try:
        # One-time cleanup: earlier runs of this script (before the
        # SWE201c -> SWE202c code-mismatch fix) seeded a Syllabus row under
        # the wrong, nonexistent code -- the upsert loop below only ever
        # touches "SWE202c" now, so the stale "SWE201c" row would otherwise
        # sit in the table forever alongside the corrected one.
        stale_row = db.get(Syllabus, "SWE201c")
        if stale_row is not None:
            db.delete(stale_row)

        for data in (_csi106_syllabus(), _swe201c_syllabus()):
            row = db.get(Syllabus, data["subject_code"])
            if row is None:
                row = Syllabus(subject_code=data["subject_code"])
                db.add(row)
            for key, value in data.items():
                setattr(row, key, value)

        for prog in CURRICULUM_PROGRAMS:
            row = db.get(CurriculumProgram, prog["code"])
            if row is None:
                row = CurriculumProgram(code=prog["code"])
                db.add(row)
            row.name = prog["name"]
            row.faculty = prog["faculty"]
            row.decision_no = prog["decision_no"]
            row.effective_year = prog["effective_year"]
            row.total_credits = prog["total_credits"]
            row.description = prog["description"]
            row.semesters = prog["semesters"]

        # PrerequisiteNode is now fully generated from the catalog (see
        # _build_prerequisite_nodes), not hand-typed -- unlike the
        # syllabi/CurriculumProgram loops above, stale rows from OLD wrong
        # codes (NWC203c, SWE201c, PRN211, OJT401, PRM392, SEP490, etc. --
        # this file's earlier hand-typed/mistyped codes, seeded by previous
        # runs of this same script before the rename fixes) are never
        # revisited by an upsert loop keyed on the NEW code list, so they'd
        # sit in the table forever. Delete anything not in the fresh set
        # first so the table is an exact mirror of _build_prerequisite_nodes,
        # not an ever-growing union of every code this file has ever used.
        valid_codes = {node["code"] for node in prerequisite_nodes}
        for stale in db.query(PrerequisiteNode).filter(PrerequisiteNode.code.notin_(valid_codes)).all():
            db.delete(stale)

        for node in prerequisite_nodes:
            row = db.get(PrerequisiteNode, node["code"])
            if row is None:
                row = PrerequisiteNode(code=node["code"])
                db.add(row)
            row.name = node["name"]
            row.semester = node["semester"]
            row.credits = node["credits"]
            row.category = node["category"]
            row.prerequisites = node["prerequisites"]
            row.is_prerequisite_of = node["isPrerequisiteOf"]

        db.commit()
        print(
            f"Seeded {2} syllabi, {len(CURRICULUM_PROGRAMS)} curriculum programs, "
            f"{len(prerequisite_nodes)} prerequisite nodes."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
