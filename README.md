# X12 278 to FHIR R4 ServiceRequest Converter

A Python-based converter that transforms X12 278 prior authorization transactions into HL7 FHIR R4 ServiceRequest resources, designed for healthcare payers and providers implementing CMS prior authorization automation.

## Business Problem

Prior authorization is one of the most operationally complex processes in healthcare — averaging 14 days per request with significant manual overhead across payer and provider systems. The CMS Interoperability Final Rule encourages automation via FHIR APIs. This converter bridges legacy X12 278 EDI transactions to modern FHIR R4 ServiceRequest resources, enabling real-time prior authorization workflows consistent with CMS mandates and the Da Vinci Prior Authorization Support (PAS) implementation guide.

## Features

- **278 Parser**: Extracts NM1, TRN, UM, HI, DTP, HSD segments from X12 prior authorization requests
- **ServiceRequest Mapping**: Maps 278 service details to FHIR R4 ServiceRequest resources
- **Patient Lookup**: Searches FHIR server by SSN to link existing Patient records
- **Practitioner Lookup**: Searches FHIR server by NPI to link requesting providers
- **Newborn Handling**: Auto-creates Patient records when 278 arrives before 834 enrollment processing
- **Duplicate Detection**: Searches by authorization number to prevent duplicate ServiceRequest creation
- **Edge Case Handling**: Gracefully handles missing data, defaults service dates, and validates inputs against FHIR R4 schema requirements

## FHIR R4 Mapping Logic
**X12 278 Segment**        **278 Field**                **FHIR R4 Field**
NM1*IL                 Patient SSN              subject.reference
NM1*1P                 Provider NPI             requester.reference
TRN*1                  Authorization number     identifier
UM                     Service type             codecode.coding.code
HI*ABK                 Diagnosis (ICD-10)       reasonCode
DTP*472                Service date             occurrenceDateTime
HSD*VS                 Units requested          quantity



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

## Edge Cases and Payer Workflow Handled

Patient Not Found — Newborn Scenario: When a 278 prior authorization arrives before the 834 enrollment transaction has been processed — a common occurrence in neonatal care — the converter auto-creates a minimal Patient record from NM1*IL demographic data and flags it for manual review. This reflects real-world payer enrollment timing gaps that EDI integration architects must account for.
Duplicate Authorization Requests: Searches by TRN authorization number before creating a ServiceRequest, reusing the existing record if found. This addresses a common EDI retransmission scenario in payer operations.
Missing Service Date (DTP*472): Defaults to 30 days from the current date and logs a warning for manual review, consistent with standard payer authorization processing timelines.
Missing Diagnosis (HI*ABK): Creates the ServiceRequest without a reasonCode, accommodating service types where diagnosis is not required for authorization.
Missing Practitioner: Creates the ServiceRequest without a requester reference when the provider NPI is not found in the FHIR server, supporting incomplete provider registry scenarios.

## Real World Scenarios

**Scenario 1** — Standard Prior Authorization: Patient requires elective surgery. Provider submits X12 278 requesting authorization. Converter creates FHIR ServiceRequest linked to existing Patient and Practitioner records.
**Scenario 2** — Newborn NICU Authorization: Newborn requires NICU care before insurance enrollment has been processed. Converter auto-creates a minimal Patient record and generates a ServiceRequest for neonatal care services, addressing a critical timing gap in payer enrollment workflows.
**Scenario 3** — Duplicate EDI Submission: Same 278 transaction retransmitted by the trading partner. Converter detects the existing ServiceRequest by authorization number and reuses it, preventing duplicate authorization processing.


## Standard Compliance

HL7 FHIR R4 specification
ANSI X12 278 transaction standard
CMS Interoperability and Patient Access Rule (CMS-0057-F)
Da Vinci Prior Authorization Support (PAS) Implementation Guide
ICD-10-CM diagnosis coding

## Related Projects

- [fhir-834-converter](https://github.com/vthotac/fhir-834-converter) - X12 834 enrollment to FHIR Coverage transformation

## About This Project
Developed by Venkatesh Thota as part of an HL7 FHIR R4 interoperability learning curriculum focused on payer-side healthcare data exchange. Reflects working knowledge of X12 EDI transaction standards, FHIR R4 resource modeling, and real-world payer authorization workflows applicable to enterprise healthcare IT integration programs.

