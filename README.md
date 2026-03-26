# X12 278 to FHIR ServiceRequest Converter

A Python-based converter that transforms X12 278 prior authorization transactions into FHIR R4 ServiceRequest resources, designed for healthcare payers and providers implementing CMS prior authorization automation.

## Business Problem

Prior authorization is one of the most inefficient processes in healthcare - averaging 14 days per request with significant manual overhead. The CMS Interoperability Final Rule encourages automation via FHIR APIs. This converter bridges legacy X12 278 transactions to modern FHIR ServiceRequest resources, enabling real-time prior auth workflows.

## Features

- **278 Parser**: Extracts NM1, TRN, UM, HI, DTP, HSD segments from X12 prior auth requests
- **ServiceRequest Mapping**: Maps 278 service details to FHIR ServiceRequest resources
- **Patient Lookup**: Searches FHIR server by SSN to link existing Patient records
- **Practitioner Lookup**: Searches FHIR server by NPI to link requesting providers
- **Newborn Handling**: Auto-creates Patient records when 278 arrives before 834 enrollment
- **Duplicate Detection**: Searches by authorization number to prevent duplicate processing
- **Edge Case Handling**: Gracefully handles missing data, defaults service dates, validates inputs

## Architecture
```
X12 278 Prior Auth Request
    ↓
parse_278_file() → Extract UM, HI, DTP, NM1, TRN segments
    ↓
find_patient_by_ssn() → Search FHIR for existing Patient
    ↓ (if not found)
create_patient_from_278() → Auto-create minimal Patient record
    ↓
find_practitioner_by_npi() → Search FHIR for requesting provider
    ↓
find_existing_service_request() → Check for duplicate by auth number
    ↓
create_service_request() → Map to FHIR ServiceRequest
    ↓
HAPI FHIR Server → Stores ServiceRequest linked to Patient & Practitioner
```

## Mapping Logic

| X12 278 Segment | 278 Field | FHIR ServiceRequest Field |
|-----------------|-----------|---------------------------|
| NM1\*IL | Patient SSN | subject.reference (via search) |
| NM1\*1P | Provider NPI | requester.reference (via search) |
| TRN\*1 | Authorization number | identifier (auth system) |
| UM | Service type code | code.coding.code |
| HI\*ABK | Diagnosis (ICD-10) | reasonCode |
| DTP\*472 | Service date | occurrenceDateTime |
| HSD\*VS | Units requested | quantity |

## Edge Cases Handled

1. **Patient Not Found (Newborn Scenario)**: When 278 arrives before 834 enrollment (common for newborns), auto-creates minimal Patient record from NM1\*IL data and logs for review
2. **Duplicate Authorization Requests**: Searches by TRN authorization number before creating ServiceRequest, reuses existing if found
3. **Missing Service Date (DTP\*472)**: Defaults to 30 days from current date, logs warning for manual review
4. **Missing Diagnosis (HI\*ABK)**: Creates ServiceRequest without reasonCode (diagnosis optional for some service types)
5. **Missing Practitioner**: Creates ServiceRequest without requester if NPI not found in FHIR server
6. **Missing Authorization Number**: Creates ServiceRequest with only business ID (SR-XXXX format)

## Prerequisites

- Python 3.7+
- HAPI FHIR server running on localhost:8080
- Existing Patient and Practitioner resources (or will auto-create Patients)

## Installation
```bash
# Clone repository
git clone https://github.com/[YOUR_USERNAME]/fhir-278-prior-auth.git
cd fhir-278-prior-auth

# Install dependencies
pip3 install -r requirements.txt
```

## Usage
```bash
# Convert a 278 file
python3 converter.py sample_278.txt

# Convert newborn scenario
python3 converter.py sample_278_newborn.txt

# Expected output:
# 🚀 Starting 278 to FHIR Conversion...
# 📁 Input file: sample_278.txt
# 📄 Parsing 278 file...
# 📋 Creating ServiceRequest...
# ✅ Found Patient/1000 - John Doe
# ✅ Found Practitioner/1005 - Dr. Robert Jones
# ✅ Created ServiceRequest/1007 - SR-3002
# ✅ Conversion complete!
```

## Sample 278 File Format

The converter expects 278 files with segments on a single line separated by `~`:
```
ISA*00*...*~GS*HS*...*~ST*278*...*~NM1*IL*1*DOE*JOHN~TRN*1*AUTH-2025-001~UM*HS*I**1*SU~HI*ABK:M17.11~DTP*472*D8*20250420~...
```

## Real-World Scenarios

### Scenario 1: Standard Prior Auth
Patient John Doe needs knee surgery. Provider submits 278 requesting authorization.

**Input:** `sample_278.txt` (existing patient, existing provider)  
**Output:** ServiceRequest/1007 linked to Patient/1000 and Practitioner/1005

### Scenario 2: Newborn NICU Authorization
Baby Johnson born, hospital requests NICU authorization before insurance enrollment processed.

**Input:** `sample_278_newborn.txt` (patient doesn't exist yet)  
**Output:** Auto-creates Patient/1020 (PAT-1005), ServiceRequest/1021 for neonatal care

### Scenario 3: Duplicate Submission
Same 278 file processed twice (common in EDI retransmissions).

**Output:** Detects existing ServiceRequest by auth number, reuses instead of creating duplicate

## Business Identifier Scheme

The converter uses a professional ID scheme for portfolio/production readiness:

- **Patients**: PAT-1001, PAT-1002, PAT-1003...
- **Practitioners**: PRAC-2001, PRAC-2002...
- **ServiceRequests**: SR-3001, SR-3002, SR-3003...

Business IDs are searchable: `GET /fhir/ServiceRequest?identifier=http://hospital.example.org/service-requests|SR-3001`

## Technologies

- Python 3
- FHIR R4
- HAPI FHIR
- X12 EDI 278
- REST APIs

## Development Approach

This project was developed using modern AI-assisted development practices. AI tools were used for baseline code generation and documentation. All business logic, 278 segment parsing, edge case handling, and FHIR mapping rules were designed and validated against healthcare interoperability standards and real-world payer workflows.

## Related Projects

- [fhir-834-converter](https://github.com/vthotac/fhir-834-converter) - X12 834 enrollment to FHIR Coverage transformation

## License

MIT License - Feel free to use this for learning or adapt for your own projects.

## Author

Built as part of FHIR integration learning for healthcare payer/provider interoperability projects.
