import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime
import pyttsx3
import sqlite3
import webbrowser
import pyautogui
import time
import pandas as pd
import csv
import requests

engine = pyttsx3.init('sapi5')
engine.setProperty('rate', 150)

ATTENDANCE_IMAGES_PATH = 'attendance_images'
UNKNOWN_FACES_PATH = 'unknown_faces'
BACKEND_ATTENDANCE_URL = os.environ.get(
    'ATTENDANCE_API_URL',
    'http://localhost:8080/api/mark-attendance'
)

if not os.path.exists(ATTENDANCE_IMAGES_PATH): os.makedirs(ATTENDANCE_IMAGES_PATH)
if not os.path.exists(UNKNOWN_FACES_PATH): os.makedirs(UNKNOWN_FACES_PATH)

def get_student_details(roll_no):
    try:
        df = pd.read_csv(
            'Students.csv',
            dtype={'ROLL': str, 'PHONE': str, 'PARENT_PHONE': str}
        )
        s = df.loc[df['ROLL'].astype(str) == str(roll_no)]
        if s.empty:
            print(f"Student {roll_no} is missing from Students.csv; WhatsApp alerts skipped.")
            return None, None

        student = s.iloc[0]
        phone = student['PHONE']
        parent_phone = student['PARENT_PHONE']
        return (
            None if pd.isna(phone) else str(phone).strip(),
            None if pd.isna(parent_phone) else str(parent_phone).strip()
        )
    except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as error:
        print(f"Could not read student contact details: {error}")
        return None, None

def send_whatsapp(phone, msg):
    if phone:
        print("Sending WhatsApp Message...")
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}&text={msg}")
        time.sleep(12)
        pyautogui.keyDown('enter'); time.sleep(0.4); pyautogui.keyUp('enter')
        time.sleep(2)
        pyautogui.keyDown('enter'); time.sleep(0.4); pyautogui.keyUp('enter')
        print("Message Sent!")

def calculate_overall_attendance_percentage(roll_no):
    with sqlite3.connect('attendance.db') as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(DISTINCT date) FROM attendance')
        total_days = c.fetchone()[0]

        c.execute('SELECT COUNT(DISTINCT date) FROM attendance WHERE roll_no = ?', (roll_no,))
        attended = c.fetchone()[0]

    return (attended / total_days) * 100 if total_days else 0

def sync_attendance_with_backend(roll_no, name):
    try:
        response = requests.post(
            BACKEND_ATTENDANCE_URL,
            json={'student_id': str(roll_no), 'full_name': name},
            timeout=5
        )
        response.raise_for_status()
        print(f"Backend sync: {response.text}")
    except requests.RequestException as error:
        print(
            "WARNING: Attendance was saved locally, but backend sync failed. "
            f"Start the Spring backend and retry if needed. Details: {error}"
        )

def init_db():
    conn = sqlite3.connect('attendance.db')
    conn.cursor().execute('CREATE TABLE IF NOT EXISTS attendance (roll_no TEXT, name TEXT, subject TEXT, time TEXT, date TEXT, status TEXT, image_path TEXT)')
    conn.commit(); conn.close()
    if not os.path.isfile('Attendance.csv') or os.path.getsize('Attendance.csv') == 0:
        with open('Attendance.csv', 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(
                ['ROLL', 'NAME', 'SUBJECT', 'TIME', 'DATE', 'STATUS', 'PERCENTAGE']
            )

def speak(text):
    print(f"AI: {text}")
    engine.say(text)
    engine.runAndWait()

def markAttendance(roll_no, name, img_frame, faceLoc):
    now = datetime.now()
    current_day = now.strftime('%A')
    date_s = now.strftime('%d-%m-%Y')
    time_s = now.strftime('%H:%M:%S')

    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM attendance WHERE roll_no = ? AND date = ?', (roll_no, date_s))
    
    if c.fetchone() is None:
        path = os.path.join(ATTENDANCE_IMAGES_PATH, f"{roll_no}_{date_s}.jpg")
        y1, x2, y2, x1 = faceLoc
        cv2.imwrite(path, img_frame[y1:y2, x1:x2])
        
        c.execute('INSERT INTO attendance VALUES (?,?,?,?,?,?,?)', (roll_no, name, "General", time_s, date_s, "PRESENT", path))
        conn.commit()
        
        perc = calculate_overall_attendance_percentage(roll_no)
        with open('Attendance.csv', 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(
                [roll_no, name, 'General', time_s, date_s, 'PRESENT', f'{perc:.2f}%']
            )

        sync_attendance_with_backend(roll_no, name)
        
        s_phone, p_phone = get_student_details(roll_no)
        msg = f"Attendance Alert:\nName: {name}\nDate: {date_s}\nTime: {time_s}\nStatus: Present\nOverall Attendance: {perc:.2f}%"
        
        speak(f"Verified. Welcome {name}.")
        send_whatsapp(s_phone, msg)
        
        if current_day == "Friday" and perc < 75:
            p_msg = (f"Weekly Alert! {name}'s attendance is {perc:.2f}% (Below 75%).\n"
                     f"Aapke bacche ki attendance 75% se kam hai.\n"
                     f"Tuhade bache di attendance 75% ton ghat hai.")
            send_whatsapp(p_phone, p_msg)
    else:
        speak(f"{name}, your attendance is already marked for today.")
        
    conn.close()

def capture_unknown_face(img_frame):
    now = datetime.now()
    dateString = now.strftime('%d-%m-%Y')
    timeString = now.strftime('%H:%M:%S')
    unique_filename = f"unknown_{dateString}_{timeString.replace(':', '-')}.jpg"
    captured_img_full_path = os.path.join(UNKNOWN_FACES_PATH, unique_filename)
    cv2.imwrite(captured_img_full_path, img_frame)

def get_ear(eye):
    v1 = np.linalg.norm(np.array(eye[1]) - np.array(eye[5]))
    v2 = np.linalg.norm(np.array(eye[2]) - np.array(eye[4]))
    h = np.linalg.norm(np.array(eye[0]) - np.array(eye[3]))
    return (v1 + v2) / (2.0 * h)

init_db()

path = 'images'
images = []
classNames = []
for cl in os.listdir(path):
    img = cv2.imread(f'{path}/{cl}')
    if img is not None: 
        images.append(img)
        classNames.append(os.path.splitext(cl)[0])

def findEncodings(images):
    return [face_recognition.face_encodings(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))[0] for img in images]

encodeListKnown = findEncodings(images)
print('System Ready!')

print("Camera on kar raha hoon...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

if not cap.isOpened():
    print("Index 0 fail. Index 1 try kar raha hoon...")
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("🚨 CRITICAL ERROR: Laptop ka camera open nahi ho raha! (Hardware switch check kar)")
    os._exit(0)

print("Camera Khul Gaya! Demo ready hai...")

blink_counter = 0

while True:
    success, img = cap.read()
    if not success or img is None:
        print("🚨 ERROR: Camera connect ho gaya par screen black aa rahi hai!")
        break

    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
    
    facesCurFrame = face_recognition.face_locations(imgS)
    encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)
    face_landmarks_list = face_recognition.face_landmarks(imgS, facesCurFrame)
    
    should_exit = False

    for encodeFace, faceLoc, face_landmarks in zip(encodesCurFrame, facesCurFrame, face_landmarks_list):
        matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
        faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
        
        if len(faceDis) > 0:
            matchIndex = np.argmin(faceDis)
            
            left_eye = face_landmarks['left_eye']
            right_eye = face_landmarks['right_eye']
            ear = (get_ear(left_eye) + get_ear(right_eye)) / 2.0

            if ear < 0.28: 
                blink_counter += 1
                cv2.putText(img, "BLINK DETECTED!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
            
            if matches[matchIndex] and faceDis[matchIndex] < 0.60:
                matched_string = classNames[matchIndex].upper()
                if '_' in matched_string:
                    roll_no, name = matched_string.split('_', 1)
                else:
                    roll_no = "N/A"
                    name = matched_string
                box_color = (0, 255, 0)
            else:
                roll_no = "UNKNOWN"
                name = "PERSON"
                box_color = (0, 0, 255)

            cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2)
            text_y = y1 - 10 if y1 > 20 else y1 + 25 
            cv2.putText(img, f"{name} | BLINKS: {blink_counter}/2", (x1, text_y), cv2.FONT_HERSHEY_COMPLEX, 0.6, (255, 255, 255), 1)

            if blink_counter >= 2:
                if name != "PERSON":
                    markAttendance(roll_no, name, img, (y1, x2, y2, x1))
                    try:
                        os.startfile('Attendance.csv')
                    except Exception as e:
                        pass
                else:
                    capture_unknown_face(img)
                    speak("Unknown person verified")
                
                should_exit = True  
                break 
    
    cv2.rectangle(img, (0, 0), (img.shape[1], 40), (0, 0, 0), cv2.FILLED)
    cv2.putText(img, "SMART ATTENDANCE SYSTEM", (int(img.shape[1]/2) - 170, 28), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

    if should_exit:
        break  

    cv2.imshow('Attendance System', img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

cap.release()
cv2.destroyAllWindows()