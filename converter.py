import requests
import json
from datetime import date
import sys

# HAPI FHIR server URL
FHIR_BASE_URL = "http://localhost:8080/fhir"

def parse_278_file(filename):
    """Parse 278 file and extract key segments"""
    with open(filename, 'r') as f:
        content = f.read()
    
    content = content.replace('\n', '').replace('\r', '')
    segments = content.strip().split('~')
    
    data = {
        'nm1_il': None,
        'nm1_1p': None,
        'trn': None,
        'um': None,
        'hi_abk': None,
        'dtp_472': None,
        'hsd': None
    }
    
    for segment in segments:
        if not segment:
            continue
            
        fields = segment.split('*')
        seg_id = fields[0]
        
        if seg_id == 'NM1' and len(fields) > 1:
            if fields[1] == 'IL':
                data['nm1_il'] = fields
            elif fields[1] == '1P':
                data['nm1_1p'] = fields
        elif seg_id == 'TRN':
            data['trn'] = fields
        elif seg_id == 'UM':
            data['um'] = fields
        elif seg_id == 'HI' and len(fields) > 1 and fields[1].startswith('ABK'):
            data['hi_abk'] = fields[1]
        elif seg_id == 'DTP' and len(fields) > 1 and fields[1] == '472':
            data['dtp_472'] = fields[3] if len(fields) > 3 else None
        elif seg_id == 'HSD':
            data['hsd'] = fields
    
    return data

def find_patient_by_ssn(ssn):
    """Search for Patient by SSN"""
    try:
        search_url = f"{FHIR_BASE_URL}/Patient?identifier=http://hl7.org/fhir/sid/us-ssn|{ssn}"
        response = requests.get(search_url)
        
        if response.status_code == 200:
            bundle = response.json()
            if bundle.get('total', 0) > 0:
                patient_id = bundle['entry'][0]['resource']['id']
                patient_name = bundle['entry'][0]['resource']['name'][0]
                display_name = f"{patient_name.get('given', [''])[0]} {patient_name.get('family', '')}"
                print(f"✅ Found Patient/{patient_id} - {display_name}")
                return patient_id, display_name
    except Exception as e:
        print(f"⚠️  Error searching for patient: {e}")
    
    return None, None

def create_patient_from_278(nm1_il, next_patient_id):
    """Create Patient from NM1*IL segment if not found"""
    
    family_name = nm1_il[3] if len(nm1_il) > 3 else "UNKNOWN"
    given_name = nm1_il[4] if len(nm1_il) > 4 else "UNKNOWN"
    ssn_raw = nm1_il[9] if len(nm1_il) > 9 else None
    
    # Format SSN
    if ssn_raw and len(ssn_raw) == 9:
        ssn = f"{ssn_raw[0:3]}-{ssn_raw[3:5]}-{ssn_raw[5:9]}"
    else:
        ssn = ssn_raw
    
    patient = {
        "resourceType": "Patient",
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": f"PAT-{next_patient_id}"
        }],
        "name": [{
            "use": "official",
            "family": family_name,
            "given": [given_name]
        }]
    }
    
    if ssn:
        patient["identifier"].append({
            "system": "http://hl7.org/fhir/sid/us-ssn",
            "value": ssn
        })
    
    try:
        response = requests.post(f"{FHIR_BASE_URL}/Patient", json=patient)
        
        if response.status_code in [200, 201]:
            patient_resource = response.json()
            patient_id = patient_resource['id']
            print(f"✅ Created Patient/{patient_id} - PAT-{next_patient_id} ({given_name} {family_name})")
            return patient_id, f"{given_name} {family_name}"
        else:
            print(f"❌ Failed to create Patient: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"❌ Error creating Patient: {e}")
        return None, None

def find_practitioner_by_npi(npi):
    """Search for Practitioner by NPI"""
    try:
        search_url = f"{FHIR_BASE_URL}/Practitioner?identifier=http://hl7.org/fhir/sid/us-npi|{npi}"
        response = requests.get(search_url)
        
        if response.status_code == 200:
            bundle = response.json()
            if bundle.get('total', 0) > 0:
                prac_id = bundle['entry'][0]['resource']['id']
                prac_name = bundle['entry'][0]['resource']['name'][0]
                display_name = f"Dr. {prac_name.get('given', [''])[0]} {prac_name.get('family', '')}"
                print(f"✅ Found Practitioner/{prac_id} - {display_name}")
                return prac_id, display_name
    except Exception as e:
        print(f"⚠️  Error searching for practitioner: {e}")
    
    return None, None

def find_existing_service_request(auth_number):
    """Check if ServiceRequest with this auth number already exists"""
    try:
        search_url = f"{FHIR_BASE_URL}/ServiceRequest?identifier=http://payer.example.org/auth-numbers|{auth_number}"
        response = requests.get(search_url)
        
        if response.status_code == 200:
            bundle = response.json()
            if bundle.get('total', 0) > 0:
                sr_id = bundle['entry'][0]['resource']['id']
                print(f"ℹ️  Found existing ServiceRequest/{sr_id} with auth number {auth_number}")
                return sr_id
    except Exception as e:
        print(f"⚠️  Error searching for existing ServiceRequest: {e}")
    
    return None

def create_service_request(data, next_sr_id, next_patient_id):
    """Create FHIR ServiceRequest from 278 data with edge case handling"""
    
    # VALIDATION
    if not data['nm1_il']:
        print("❌ CRITICAL: NM1*IL (Patient) segment missing")
        return None
    
    if not data['um']:
        print("❌ CRITICAL: UM (Service) segment missing")
        return None
    
    # Extract and format patient SSN
    nm1_il = data['nm1_il']
    patient_ssn_raw = nm1_il[9] if len(nm1_il) > 9 else None
    
    if patient_ssn_raw and len(patient_ssn_raw) == 9:
        patient_ssn = f"{patient_ssn_raw[0:3]}-{patient_ssn_raw[3:5]}-{patient_ssn_raw[5:9]}"
    else:
        patient_ssn = patient_ssn_raw
    
    if not patient_ssn:
        print("❌ CRITICAL: Patient SSN missing")
        return None
    
    # EDGE CASE: Check for duplicate by auth number
    auth_number = None
    if data['trn']:
        auth_number = data['trn'][2] if len(data['trn']) > 2 else None
        
        if auth_number:
            existing_sr_id = find_existing_service_request(auth_number)
            if existing_sr_id:
                print(f"⚠️  DUPLICATE: ServiceRequest with auth {auth_number} already exists")
                print(f"   Using existing ServiceRequest/{existing_sr_id}")
                return existing_sr_id
    else:
        print("⚠️  WARNING: No TRN (authorization number) in 278")
    
    # EDGE CASE: Find or create Patient
    patient_id, patient_display = find_patient_by_ssn(patient_ssn)
    
    if not patient_id:
        print(f"⚠️  Patient with SSN {patient_ssn} not found - creating from 278 data")
        patient_id, patient_display = create_patient_from_278(nm1_il, next_patient_id)
        
        if not patient_id:
            print("❌ CRITICAL: Could not find or create Patient")
            return None
    
    # Find Practitioner (optional)
    practitioner_id = None
    practitioner_display = None
    
    if data['nm1_1p']:
        nm1_1p = data['nm1_1p']
        provider_npi = nm1_1p[9] if len(nm1_1p) > 9 else None
        
        if provider_npi:
            practitioner_id, practitioner_display = find_practitioner_by_npi(provider_npi)
            if not practitioner_id:
                print(f"⚠️  WARNING: Practitioner with NPI {provider_npi} not found")
    
    # Extract service date
    service_date = None
    if data['dtp_472'] and len(data['dtp_472']) == 8:
        service_date = f"{data['dtp_472'][0:4]}-{data['dtp_472'][4:6]}-{data['dtp_472'][6:8]}"
    else:
        print("⚠️  WARNING: Service date (DTP*472) missing - using 30 days from today")
        from datetime import timedelta
        service_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Extract diagnosis
    diagnosis_code = None
    if data['hi_abk']:
        diagnosis_code = data['hi_abk'].split(':')[1] if ':' in data['hi_abk'] else None
    else:
        print("⚠️  WARNING: No diagnosis code (HI*ABK) in 278")
    
    # Build ServiceRequest
    service_request = {
        "resourceType": "ServiceRequest",
        "identifier": [{
            "system": "http://hospital.example.org/service-requests",
            "value": f"SR-{next_sr_id}"
        }],
        "status": "active",
        "intent": "order",
        "category": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "387713003",
                "display": "Surgical procedure"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://www.ama-assn.org/go/cpt",
                "code": "27447",
                "display": "Total knee arthroplasty"
            }]
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
            "display": patient_display
        },
        "occurrenceDateTime": service_date,
        "authoredOn": date.today().strftime("%Y-%m-%d")
    }
    
    # Add auth number if present
    if auth_number:
        service_request["identifier"].append({
            "system": "http://payer.example.org/auth-numbers",
            "value": auth_number
        })
    
    # Add diagnosis if present
    if diagnosis_code:
        service_request["reasonCode"] = [{
            "coding": [{
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": diagnosis_code,
                "display": "Osteoarthritis"
            }]
        }]
    
    # Add requester if found
    if practitioner_id:
        service_request["requester"] = {
            "reference": f"Practitioner/{practitioner_id}",
            "display": practitioner_display
        }
    
    # POST to HAPI FHIR
    try:
        response = requests.post(f"{FHIR_BASE_URL}/ServiceRequest", json=service_request)
        
        if response.status_code in [200, 201]:
            sr_resource = response.json()
            sr_id = sr_resource['id']
            print(f"✅ Created ServiceRequest/{sr_id} - SR-{next_sr_id}")
            return sr_id
        else:
            print(f"❌ Failed to create ServiceRequest: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Error creating ServiceRequest: {e}")
        return None

def main():
    # Get filename from command line argument
    if len(sys.argv) < 2:
        print("❌ ERROR: Missing 278 file argument")
        print()
        print("Usage: python3 converter.py <278_file>")
        print()
        print("Examples:")
        print("  python3 converter.py sample_278.txt")
        print("  python3 converter.py sample_278_newborn.txt")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    print("🚀 Starting 278 to FHIR Conversion (with Edge Case Handling)...")
    print(f"📁 Input file: {filename}")
    print()
    
    # Check if file exists
    import os
    if not os.path.exists(filename):
        print(f"❌ ERROR: File '{filename}' not found")
        sys.exit(1)
    
    print("📄 Parsing 278 file...")
    data = parse_278_file(filename)
    print()
   

    print("📋 Creating ServiceRequest...")
    # Next IDs: SR-3003, PAT-1005
    sr_id = create_service_request(data, next_sr_id="3003", next_patient_id="1005")
    
    if sr_id:
        print()
        print("✅ Conversion complete!")
        print(f"   ServiceRequest ID: {sr_id}")
        print()
        print(f"🔍 View in browser: http://localhost:8080/fhir/ServiceRequest/{sr_id}")
    else:
        print()
        print("❌ Conversion failed")

if __name__ == "__main__":
    main()