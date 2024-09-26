# Import module
import sqlite3

# Connecting to sqlite
conn = sqlite3.connect('test.db')

# Creating a cursor object using the cursor() method
cursor = conn.cursor()

# Creating table with an additional IMAGE column
table = """CREATE TABLE IF NOT EXISTS STUDENT(
    SUBJECT VARCHAR(255), 
    CHAPTER VARCHAR(255), 
    DIFFICULTY VARCHAR(255),
    IMAGE BLOB,
    opt1 VARCHAR(255),
    opt2 VARCHAR(255),
    opt3 VARCHAR(255),
    opt4 VARCHAR(255),
    ans VARCHAR(255)
    );"""
cursor.execute(table)

# Function to convert image to binary data
def convert_to_binary_data(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        blob_data = file.read()
    return blob_data

# Insert student data with image
def insert_student(sub, chap, diff, image_path,ans):
    # Convert image to binary data
    image = convert_to_binary_data(image_path)
    # Insert data into the database
    cursor.execute("INSERT INTO STUDENT (SUBJECT, CHAPTER, DIFFICULTY, IMAGE,opt1,opt2,opt3,opt4,ans) VALUES (?, ?, ?, ?,?,?,?,?,?)", 
                   (sub, chap, diff, image,'A','B','C','D',ans))
    conn.commit()

# Inserting records with image paths (update image paths accordingly)
insert_student('Physics', 'Optics', 'Easy', 'photos/R.jpg','A')
insert_student('Physics', 'Optics', 'Easy', 'photos/R.jpg','B')
insert_student('Physics', 'Optics', 'Easy', 'photos/R.jpg','C')
insert_student('Physics', 'Optics', 'Easy', 'photos/R.jpg','D')
insert_student('Math', 'Calculus', 'Medium', 'photos/OIP (2).jpg','ACD')
insert_student('Math', 'Calculus', 'Medium', 'photos/OIP (2).jpg','ACD')
insert_student('Math', 'Calculus', 'Medium', 'photos/OIP (2).jpg','ACD')

# Display data inserted with image details
print("Data Inserted in the table with image details: ")
data = cursor.execute("SELECT SUBJECT, CHAPTER, DIFFICULTY, IMAGE,opt1,opt2,opt3,opt4,ans FROM STUDENT")
for row in data:
    name, student_class, section, image,opt1,opt2,opt3,opt4,ans = row
    print(f"Name: {name}, Class: {student_class}, Section: {section}, Image Size: {len(image)} bytes,opt1: {opt1},opt2: {opt2},opt3: {opt3},opt4: {opt4},ans: {ans}")






# Commit your changes in the database
conn.commit()

# Closing the connection
conn.close()
