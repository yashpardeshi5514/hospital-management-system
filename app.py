from flask import Flask, request, jsonify, send_from_directory
from ai_chat import (
    extract_patient_structured,
    extract_staff_structured,
    extract_appointment_structured
)
import re, os
OPENAI_AVAILABLE = False
from db import get_connection
import mysql.connector, os

app = Flask(__name__, static_folder='static', static_url_path='')

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')


# ---------- DB Helper ----------
def run_query(query, params=None, fetch=False):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            return rows
        conn.commit()
        cursor.close(); conn.close()
        return True
    except mysql.connector.Error as err:
        return str(err)


# ---------- Chat API ----------
@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json() or {}
    msg = data.get('message', '').lower().strip()

    if not msg:
        return jsonify({'type': 'error', 'message': 'Empty message'}), 400

    # ---- Natural conversational update patterns ----
    # Handle phrases like: "update the age of patient_id 1 to 45" or "change patient 2 contact to +91..."
    def _normalize_field_name(name):
        n = name.lower().strip()
        synonyms = {
            'phone': 'contact', 'phone number': 'contact', 'mobile': 'contact',
            'contact number': 'contact', 'doc': 'doctor_assigned', 'doctor': 'doctor_assigned',
            'assigned doctor': 'doctor_assigned', 'admitted date': 'admitted_date', 'discharge date': 'discharge_date',
            'age': 'age', 'name': 'name', 'disease': 'disease', 'gender': 'gender', 'role': 'role'
        }
        n = re.sub(r"[^a-z0-9 _]", '', n)
        return synonyms.get(n, n.replace(' ', '_'))

    # two common patterns: field before role/id, or role/id before field
    p1 = re.compile(r"(?:update|change|set)\s+(?:the\s+)?(?P<field>[a-zA-Z _]+?)\s+(?:of\s+)?(?P<role>patient|staff)(?:_?id)?\s*(?:id\s*)?(?:#|:)?\s*(?P<id>\d+)\s*(?:to|=|as|become)?\s*(?P<value>.+)", re.I)
    p2 = re.compile(r"(?:update|change|set)\s+(?P<role>patient|staff)(?:_?id)?\s*(?:id\s*)?(?:#|:)?\s*(?P<id>\d+)\s*(?:set\s+)?(?P<field>[a-zA-Z _]+?)\s*(?:to|=|as|become)?\s*(?P<value>.+)", re.I)

    # Helper: extract field->value pairs from a sentence (handles 'and' / commas)
    def _extract_field_value_pairs(text):
        parts = re.split(r"\band\b|,|;", text)
        pairs = {}
        for p in parts:
            p = p.strip()
            # look for patterns like 'age to 45', 'set age to 45', 'contact +91...'
            m = re.search(r"(?:set|change|update)?\s*(?P<field>[a-zA-Z ]{2,30}?)\s*(?:to|=|as)?\s*(?P<value>.+)$", p, re.I)
            if m:
                f = m.group('field').strip()
                v = m.group('value').strip()
                if f and v:
                    pairs[_normalize_field_name(f)] = v
        return pairs

    # Helper: try to find a name mentioned in text (possessive or following keywords)
    def _find_name_in_msg(text):
        # possessive: "john doe's"
        m = re.search(r"([a-z]+(?:\s+[a-z]+){0,2})'s", text, re.I)
        if m:
            return m.group(1).strip()
        # 'for john doe' or 'of john doe' or 'named john doe'
        m = re.search(r"(?:for|of|named|called|about)\s+([a-z][a-z\s]{1,80})", text, re.I)
        if m:
            return m.group(1).strip()
        # 'change john doe' pattern
        m = re.search(r"(?:change|update|set)\s+([a-z][a-z\s]{1,80})\s+(?:'s|\b)", text, re.I)
        if m:
            return m.group(1).strip()
        return None

    def _resolve_name_to_id(role, name):
        # Try exact or LIKE match; return id if unique, else None
        if not name: return None
        if role == 'patient':
            rows = run_query("SELECT * FROM patients WHERE name LIKE %s", (f"%{name}%",), fetch=True)
            if isinstance(rows, list) and len(rows) == 1:
                return rows[0].get('patient_id')
        else:
            rows = run_query("SELECT * FROM staff WHERE name LIKE %s", (f"%{name}%",), fetch=True)
            if isinstance(rows, list) and len(rows) == 1:
                return rows[0].get('staff_id')
        return None

    # Multi-field natural updates and name-based resolution
    if any(w in msg for w in ('update', 'change', 'set')):
        # Attempt to determine role and id
        pid = _extract_id_for_role(msg, 'patient')
        sid = _extract_id_for_role(msg, 'staff')
        role = None; rec_id = None
        if pid:
            role = 'patient'; rec_id = pid
        elif sid:
            role = 'staff'; rec_id = sid
        else:
            name = _find_name_in_msg(msg)
            if name:
                # prefer patient
                r = _resolve_name_to_id('patient', name)
                if r: role = 'patient'; rec_id = r
                else:
                    r2 = _resolve_name_to_id('staff', name)
                    if r2: role = 'staff'; rec_id = r2
        if role and rec_id:
            candidates = _extract_field_value_pairs(msg)
            if candidates:
                if role == 'patient':
                    allowed = {'name','age','gender','contact','disease','doctor_assigned','admitted_date','discharge_date'}
                    table = 'patients'; idcol = 'patient_id'
                else:
                    allowed = {'name','role','contact'}
                    table = 'staff'; idcol = 'staff_id'
                updates = {k:v for k,v in candidates.items() if k in allowed}
                if updates:
                    set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
                    params = list(updates.values()) + [rec_id]
                    q = f"UPDATE {table} SET {set_clause} WHERE {idcol} = %s"
                    r = run_query(q, tuple(params))
                    if isinstance(r, str):
                        return jsonify({'type':'error','message':r}), 500
                    return jsonify({'type':'success','message':f"{role.capitalize()} {rec_id} updated ({len(updates)} fields)."})

    for m in (p1.search(msg), p2.search(msg)):
        if m:
            role = m.group('role').lower()
            rec_id = int(m.group('id'))
            raw_field = (m.groupdict().get('field') or '').strip()
            raw_value = (m.groupdict().get('value') or '').strip()
            if not raw_field or not raw_value:
                break
            field = _normalize_field_name(raw_field)
            # trim trailing punctuation
            raw_value = raw_value.rstrip('.;')
            # allowed columns per role
            allowed_patient = {'name','age','gender','contact','disease','doctor_assigned','admitted_date','discharge_date'}
            allowed_staff = {'name','role','contact'}
            allowed = allowed_patient if role == 'patient' else allowed_staff
            if field not in allowed:
                # not a recognized field for this role, skip to normal handlers
                break
            # convert value types
            val = raw_value
            if field == 'age':
                # extract first integer
                iv = re.search(r"(\d{1,3})", val)
                if iv:
                    val = int(iv.group(1))
                else:
                    # invalid age
                    return jsonify({'type':'text','message':'Could not parse numeric age from your message.'})

            # Build query
            if role == 'patient':
                q = f"UPDATE patients SET {field} = %s WHERE patient_id = %s"
                params = (val, rec_id)
            else:
                q = f"UPDATE staff SET {field} = %s WHERE staff_id = %s"
                params = (val, rec_id)
            res = run_query(q, params)
            if isinstance(res, str):
                return jsonify({'type':'error','message':res}), 500
            return jsonify({'type':'success','message':f'{role.capitalize()} {rec_id} updated: {field} -> {val}.'})

    # If OpenAI key is available, try to parse/answer more complex natural language like ChatGPT
    if os.getenv('OPENAI_API_KEY'):
        try:
            import openai, json
            openai.api_key = os.getenv('OPENAI_API_KEY')

            def _call_openai_parsing(user_text):
                # Instruct model to return JSON only with a fixed schema
                system = (
                    "You are a strict JSON-only parser for a hospital chatbot. "
                    "When given a user message, output valid JSON with one of the following structures (no extra text):\n"
                    "1) {\"action\": \"show\", \"target\": \"patient\"|\"staff\", \"id\": <int>|null, \"name\": <string>|null }\n"
                    "2) {\"action\": \"update\", \"target\": \"patient\"|\"staff\", \"id\": <int>|null, \"fields\": {<field>: <value>, ...} }\n"
                    "3) {\"action\": \"add\", \"target\": \"patient\"|\"staff\", \"fields\": {<field>: <value>, ...} }\n"
                    "4) {\"action\": \"text\", \"response\": <string> }\n"
                    "Only output JSON. If the user asks for an update but no id is provided, try to extract a name and set id to null. Do not include any explanatory text.")

                resp = openai.ChatCompletion.create(
                    model='gpt-3.5-turbo',
                    messages=[
                        {"role":"system","content":system},
                        {"role":"user","content": user_text}
                    ],
                    max_tokens=300,
                    temperature=0.0
                )
                out = resp.choices[0].message.content.strip()
                # Attempt to extract JSON block
                try:
                    return json.loads(out)
                except Exception:
                    # Try to find first {...}
                    m = re.search(r"\{[\s\S]*\}", out)
                    if m:
                        try:
                            return json.loads(m.group(0))
                        except Exception:
                            return None
                    return None

            parsed = _call_openai_parsing(msg)
            if parsed and isinstance(parsed, dict):
                action = parsed.get('action')
                if action == 'show' and parsed.get('target') in ('patient','staff'):
                    if parsed.get('id'):
                        if parsed['target']=='patient':
                            rows = run_query("SELECT * FROM patients WHERE patient_id = %s", (int(parsed['id']),), fetch=True)
                        else:
                            rows = run_query("SELECT * FROM staff WHERE staff_id = %s", (int(parsed['id']),), fetch=True)
                        if isinstance(rows, str):
                            return jsonify({'type':'error','message':rows}),500
                        if not rows:
                            return jsonify({'type':'text','message':'No record found.'})
                        r = rows[0]
                        # Ask OpenAI to create a friendly summary if desired
                        if os.getenv('OPENAI_API_KEY'):
                            try:
                                prompt = f"Produce a concise, factual summary for this record: {r}"
                                resp2 = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[{"role":"user","content":prompt}], max_tokens=200, temperature=0.3)
                                summary = resp2.choices[0].message.content.strip()
                                return jsonify({'type':'text','message':summary})
                            except Exception:
                                pass
                        parts = [f"{k}: {v if v is not None else 'N/A'}" for k,v in r.items()]
                        return jsonify({'type':'text','message':'\n'.join(parts)})

                if action == 'update' and parsed.get('target') in ('patient','staff'):
                    rid = parsed.get('id')
                    fields = parsed.get('fields') or {}
                    if not rid:
                        # If no id, ask user to specify id
                        return jsonify({'type':'text','message':'Please specify the record id to update (e.g., patient_id 1).'})
                    allowed_patient = {'name','age','gender','contact','disease','doctor_assigned','admitted_date','discharge_date'}
                    allowed_staff = {'name','role','contact'}
                    allowed = allowed_patient if parsed['target']=='patient' else allowed_staff
                    updates = {k:v for k,v in fields.items() if _normalize_field_name(k) in allowed}
                    if not updates:
                        return jsonify({'type':'text','message':'No valid fields detected to update.'})
                    # normalize keys
                    updates_norm = { _normalize_field_name(k): v for k,v in updates.items() }
                    set_clause = ', '.join([f"{k} = %s" for k in updates_norm.keys()])
                    params = list(updates_norm.values()) + [int(rid)]
                    if parsed['target']=='patient':
                        q = f"UPDATE patients SET {set_clause} WHERE patient_id = %s"
                    else:
                        q = f"UPDATE staff SET {set_clause} WHERE staff_id = %s"
                    resu = run_query(q, tuple(params))
                    if isinstance(resu, str):
                        return jsonify({'type':'error','message':resu}),500
                    return jsonify({'type':'success','message':f"{parsed['target'].capitalize()} {rid} updated ({len(updates_norm)} fields)."})

                if action == 'add' and parsed.get('target') in ('patient','staff'):
                    fields = parsed.get('fields') or {}
                    if parsed.get('target')=='patient':
                        q = """INSERT INTO patients (name, age, gender, contact, disease, doctor_assigned) VALUES (%s,%s,%s,%s,%s,%s)"""
                        vals = (fields.get('name'), fields.get('age'), fields.get('gender'), fields.get('contact'), fields.get('disease'), fields.get('doctor_assigned'))
                        run_query(q, vals)
                        return jsonify({'type':'success','message':'Patient added.'})
                    else:
                        q = "INSERT INTO staff (name, role, contact) VALUES (%s,%s,%s)"
                        vals = (fields.get('name'), fields.get('role'), fields.get('contact'))
                        run_query(q, vals)
                        return jsonify({'type':'success','message':'Staff added.'})

                if action == 'text' and parsed.get('response'):
                    return jsonify({'type':'text','message': parsed.get('response')})

        except Exception:
            # If any error occurs with OpenAI parsing, ignore and continue to default handlers
            pass

    # --- Add patient ---
    if 'add patient' in msg:
        parsed = extract_patient_structured(msg)
        if not parsed.get('name'):
            return jsonify({'type': 'error', 'message': 'Please include name, age, gender, disease, and doctor.'}), 400
        q = """INSERT INTO patients (name, age, gender, contact, disease, doctor_assigned)
               VALUES (%s, %s, %s, %s, %s, %s)"""
        run_query(q, (parsed['name'], parsed['age'], parsed['gender'], parsed['contact'],
                      parsed['disease'], parsed['doctor_assigned']))
        return jsonify({'type': 'success', 'message': f"Patient '{parsed['name']}' added successfully."})

    # --- Add staff ---
    if 'add staff' in msg:
        parsed = extract_staff_structured(msg)
        if not parsed.get('name'):
            return jsonify({'type': 'error', 'message': 'Please include name, role, and contact.'}), 400
        q = "INSERT INTO staff (name, role, contact) VALUES (%s, %s, %s)"
        run_query(q, (parsed['name'], parsed['role'], parsed['contact']))
        return jsonify({'type': 'success', 'message': f"Staff '{parsed['name']}' added successfully."})

    # --- Schedule appointment ---
    if 'schedule appointment' in msg:
        parsed = extract_appointment_structured(msg)
        if not all([parsed.get('patient_id'), parsed.get('staff_id'), parsed.get('date'), parsed.get('time')]):
            return jsonify({'type': 'error', 'message': 'Provide patient_id, staff_id, date, and time.'}), 400
        q = """INSERT INTO appointments (patient_id, staff_id, appointment_date, appointment_time)
               VALUES (%s, %s, %s, %s)"""
        run_query(q, (parsed['patient_id'], parsed['staff_id'], parsed['date'], parsed['time']))
        return jsonify({'type': 'success', 'message': 'Appointment scheduled successfully.'})

    # --- Show patients ---
    if 'show patients' in msg:
        rows = run_query("SELECT * FROM patients ORDER BY patient_id DESC", fetch=True)
        if isinstance(rows, str):
            return jsonify({'type': 'error', 'message': rows}), 500
        rows = rows or []
        safe_rows = [{k: (str(v) if not isinstance(v, (int, float, str, type(None))) else v) for k, v in r.items()} for r in rows]
        return jsonify({'type': 'table', 'data': safe_rows})

    # --- Show staff ---
    if 'show staff' in msg:
        rows = run_query("SELECT * FROM staff ORDER BY staff_id DESC", fetch=True)
        if isinstance(rows, str):
            return jsonify({'type': 'error', 'message': rows}), 500
        rows = rows or []
        safe_rows = [{k: (str(v) if not isinstance(v, (int, float, str, type(None))) else v) for k, v in r.items()} for r in rows]
        return jsonify({'type': 'table', 'data': safe_rows})

    # --- Show appointments ---
    if 'show appointments' in msg:
        rows = run_query("""
            SELECT a.appointment_id, p.name AS patient_name, s.name AS staff_name,
                   a.appointment_date, a.appointment_time
            FROM appointments a
            LEFT JOIN patients p ON a.patient_id = p.patient_id
            LEFT JOIN staff s ON a.staff_id = s.staff_id
            ORDER BY a.appointment_id DESC
        """, fetch=True)
        if isinstance(rows, str):
            return jsonify({'type': 'error', 'message': rows}), 500
        rows = rows or []
        safe_rows = [{k: (str(v) if not isinstance(v, (int, float, str, type(None))) else v) for k, v in r.items()} for r in rows]
        return jsonify({'type': 'table', 'data': safe_rows})

    # --- Natural language record lookup (ChatGPT-like answers) ---
    # Examples that will be handled: "tell me about John Doe", "who is patient 5", "info on staff Dr Smith"
    def _extract_name_after_keywords(text):
        m = re.search(r"(?:tell me about|who is|info on|information about|details for|details of)\s+([a-zA-Z.\- ]{2,80})", text)
        if m:
            return m.group(1).strip()
        return None

    def _extract_id_for_role(text, role):
        # look for 'patient 5' or 'patient id 5' or 'staff 3'
        m = re.search(rf"{role}[^0-9\n\r]*(?:id\s*)?(?:#|:)?\s*(\d+)", text)
        if m:
            return int(m.group(1))
        return None

    # try patient id first
    # Explicit patterns like 'patient_id 1' or 'patient 1' should return full records
    pid = _extract_id_for_role(msg, 'patient')
    if pid:
        rows = run_query("SELECT * FROM patients WHERE patient_id = %s", (pid,), fetch=True)
        if isinstance(rows, str):
            return jsonify({'type': 'error', 'message': rows}), 500
        if not rows:
            return jsonify({'type': 'text', 'message': f'No patient found with id {pid}.'})
        row = rows[0]
        # Format all available fields into a clear multiline text response
        parts = []
        for k, v in row.items():
            parts.append(f"{k}: {v if v is not None else 'N/A'}")
        text = "\n".join(parts)
        return jsonify({'type': 'text', 'message': text})

    # try staff id
    sid = _extract_id_for_role(msg, 'staff')
    if sid:
        rows = run_query("SELECT * FROM staff WHERE staff_id = %s", (sid,), fetch=True)
        if isinstance(rows, str):
            return jsonify({'type': 'error', 'message': rows}), 500
        if not rows:
            return jsonify({'type': 'text', 'message': f'No staff found with id {sid}.'})
        row = rows[0]
        parts = []
        for k, v in row.items():
            parts.append(f"{k}: {v if v is not None else 'N/A'}")
        text = "\n".join(parts)
        return jsonify({'type': 'text', 'message': text})

    # try name queries (generic)
    name = _extract_name_after_keywords(msg)
    if name:
        # search patients first
        rows = run_query("SELECT * FROM patients WHERE name LIKE %s", (f"%{name}%",), fetch=True)
        if isinstance(rows, str):
            return jsonify({'type': 'error', 'message': rows}), 500
        if rows and len(rows) == 1:
            r = rows[0]
            text = f"Patient {r.get('name')} (ID: {r.get('patient_id')}) is {r.get('age')}-year-old {r.get('gender')}. Contact: {r.get('contact') or 'N/A'}. Diagnosis: {r.get('disease') or 'N/A'}. Assigned doctor: {r.get('doctor_assigned') or 'N/A'}."
            # Optionally, enhance phrasing with OpenAI if an API key is provided
            if os.getenv('OPENAI_API_KEY'):
                try:
                    import openai
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    prompt = f"Convert this patient record into a clear, friendly paragraph for a doctor or staff member:\n{str(r)}"
                    resp = openai.Completion.create(engine='text-davinci-003', prompt=prompt, max_tokens=180, temperature=0.3)
                    nice = resp.choices[0].text.strip()
                    if nice:
                        text = nice
                except Exception:
                    # If openai isn't installed or the call fails, silently continue with the basic text
                    pass
            return jsonify({'type': 'text', 'message': text})
        if rows and len(rows) > 1:
            safe_rows = [{k: (str(v) if not isinstance(v, (int, float, str, type(None))) else v) for k, v in r.items()} for r in rows]
            return jsonify({'type': 'table', 'data': safe_rows})

        # search staff
        rows = run_query("SELECT * FROM staff WHERE name LIKE %s", (f"%{name}%",), fetch=True)
        if isinstance(rows, str):
            return jsonify({'type': 'error', 'message': rows}), 500
        if rows and len(rows) == 1:
            r = rows[0]
            text = f"Staff {r.get('name')} (ID: {r.get('staff_id')}) is a {r.get('role') or 'N/A'}. Contact: {r.get('contact') or 'N/A'}."
            return jsonify({'type': 'text', 'message': text})
        if rows and len(rows) > 1:
            safe_rows = [{k: (str(v) if not isinstance(v, (int, float, str, type(None))) else v) for k, v in r.items()} for r in rows]
            return jsonify({'type': 'table', 'data': safe_rows})

    return jsonify({'type': 'text', 'message': 'Use: add/show patient/staff or schedule appointment.'})

    # --- Conversational updates ---
    # Examples: "update patient 1 set age 30 contact +911234567" or "update staff 2 role Nurse contact +..."
    def _parse_field_pairs(text):
        # parse pairs like 'age 30', 'contact +9111', 'role Nurse', 'name John Doe'
        tokens = text.split()
        pairs = {}
        i = 0
        while i < len(tokens):
            key = tokens[i]
            # if token looks like 'patient' or 'staff' or 'update' skip
            if key.lower() in ('update', 'patient', 'staff', 'set', 'id'):
                i += 1; continue
            # value may be multiple tokens until next token that looks like a key (letters only) or end
            j = i + 1
            vals = []
            while j < len(tokens) and not re.match(r'^[a-zA-Z_]+$', tokens[j]):
                vals.append(tokens[j]); j += 1
            if not vals and j < len(tokens):
                # take single-word value
                vals.append(tokens[j]); j += 1
            pairs[key.lower()] = ' '.join(vals).strip()
            i = j
        return pairs

    # update patient
    if msg.startswith('update patient') or re.search(r'update patient\s+\d+', msg):
        pid = _extract_id_for_role(msg, 'patient')
        if not pid:
            return jsonify({'type': 'text', 'message': 'Please specify the patient id to update (e.g., "update patient 1 ...").'})
        fields = _parse_field_pairs(msg)
        allowed = {'name','age','gender','contact','disease','doctor_assigned'}
        updates = {k: v for k, v in fields.items() if k in allowed and v}
        if not updates:
            return jsonify({'type': 'text', 'message': 'No valid fields to update. Allowed: ' + ', '.join(sorted(allowed))})
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        params = list(updates.values()) + [pid]
        q = f"UPDATE patients SET {set_clause} WHERE patient_id = %s"
        res = run_query(q, tuple(params))
        if isinstance(res, str):
            return jsonify({'type': 'error', 'message': res}), 500
        return jsonify({'type': 'success', 'message': f'Patient {pid} updated ({len(updates)} fields).'} )

    # update staff
    if msg.startswith('update staff') or re.search(r'update staff\s+\d+', msg):
        sid = _extract_id_for_role(msg, 'staff')
        if not sid:
            return jsonify({'type': 'text', 'message': 'Please specify the staff id to update (e.g., "update staff 2 role Nurse").'})
        fields = _parse_field_pairs(msg)
        allowed = {'name','role','contact'}
        updates = {k: v for k, v in fields.items() if k in allowed and v}
        if not updates:
            return jsonify({'type': 'text', 'message': 'No valid fields to update. Allowed: ' + ', '.join(sorted(allowed))})
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        params = list(updates.values()) + [sid]
        q = f"UPDATE staff SET {set_clause} WHERE staff_id = %s"
        res = run_query(q, tuple(params))
        if isinstance(res, str):
            return jsonify({'type': 'error', 'message': res}), 500
        return jsonify({'type': 'success', 'message': f'Staff {sid} updated ({len(updates)} fields).'} )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
