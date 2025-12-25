import re

def extract_patient_structured(text):
    data = {'patient_id': None, 'name': None, 'age': None, 'gender': None,
            'contact': None, 'disease': None, 'doctor_assigned': None}
    m_name = re.search(r'name\s*[:\-]?\s*([A-Za-z ]{2,50})', text)
    if m_name: data['name'] = m_name.group(1).strip()
    m_age = re.search(r'age\s*[:\-]?\s*(\d{1,3})', text)
    if m_age: data['age'] = int(m_age.group(1))
    m_gender = re.search(r'gender\s*[:\-]?\s*(male|female|other)', text, re.I)
    if m_gender: data['gender'] = m_gender.group(1).capitalize()
    m_contact = re.search(r'contact\s*[:\-]?\s*(\+?\d[\d\s-]{6,})', text)
    if m_contact: data['contact'] = re.sub(r'\s+', '', m_contact.group(1))
    m_disease = re.search(r'disease\s*[:\-]?\s*([A-Za-z0-9 ,.-]{2,100})', text)
    if m_disease: data['disease'] = m_disease.group(1).strip()
    m_doc = re.search(r'doctor\s*[:\-]?\s*([A-Za-z .]{2,100})', text)
    if m_doc: data['doctor_assigned'] = m_doc.group(1).strip()
    return data

def extract_staff_structured(text):
    data = {'staff_id': None, 'name': None, 'role': None, 'contact': None}
    m_name = re.search(r'name\s*[:\-]?\s*([A-Za-z ]{2,50})', text)
    if m_name: data['name'] = m_name.group(1).strip()
    m_role = re.search(r'role\s*[:\-]?\s*([A-Za-z ]{2,50})', text)
    if m_role: data['role'] = m_role.group(1).strip()
    m_contact = re.search(r'contact\s*[:\-]?\s*(\+?\d[\d\s-]{6,})', text)
    if m_contact: data['contact'] = re.sub(r'\s+', '', m_contact.group(1))
    return data

def extract_appointment_structured(text):
    data = {'patient_id': None, 'staff_id': None, 'date': None, 'time': None}
    m_pid = re.search(r'patient_id\s*[:\-]?\s*(\d+)', text)
    if m_pid: data['patient_id'] = int(m_pid.group(1))
    m_sid = re.search(r'staff_id\s*[:\-]?\s*(\d+)', text)
    if m_sid: data['staff_id'] = int(m_sid.group(1))
    m_date = re.search(r'date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})', text)
    if m_date: data['date'] = m_date.group(1)
    m_time = re.search(r'time\s*[:\-]?\s*(\d{1,2}:\d{2})', text)
    if m_time: data['time'] = m_time.group(1)
    return data
