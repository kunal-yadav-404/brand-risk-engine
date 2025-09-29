from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# --- Configuration ---
FILE_NAME = "test-business-license.pdf"
MERCHANT_NAME = "Enhanced Test Merchant" # Matches the name in your pubsub message
LICENSE_NUMBER = "BL-5501-E-2024"
ISSUE_DATE = "2024-08-15"
VALID_UNTIL = "2025-08-14"

def create_mock_business_license():
    """Generates a mock business license PDF for testing."""
    
    print(f"Generating mock business license: {FILE_NAME}")
    
    doc = SimpleDocTemplate(FILE_NAME, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    Story = []

    # Title Style
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=24, spaceAfter=24, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='HeaderCenter', alignment=TA_CENTER, fontSize=16, spaceAfter=16, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='KeyDetail', fontSize=12, spaceAfter=12))

    # Document Title
    ptext = '<font size="24"><b>CITY OF VIRTUALIA BUSINESS LICENSE</b></font>'
    Story.append(Paragraph(ptext, styles['TitleCenter']))
    
    # Header
    ptext = '<font size="16"><b>Official Document for Merchant Onboarding</b></font>'
    Story.append(Paragraph(ptext, styles['HeaderCenter']))
    Story.append(Spacer(1, 24))

    # License Details
    details = [
        ("<b>License Holder:</b>", MERCHANT_NAME),
        ("<b>License Number:</b>", LICENSE_NUMBER),
        ("<b>Business Address:</b>", "123 Test Street, Suite 400, Virtualia, TX 77001"),
        ("<b>Issued Date:</b>", ISSUE_DATE),
        ("<b>Expiration Date:</b>", VALID_UNTIL),
    ]

    for label, value in details:
        ptext = f"{label} {value}"
        Story.append(Paragraph(ptext, styles['KeyDetail']))
        Story.append(Spacer(1, 6))

    # Certification/Fine Print
    Story.append(Spacer(1, 24))
    ptext = ('This certifies that the above-named entity is authorized to conduct business '
             'under the laws of Virtualia until the expiration date. '
             'This license is non-transferable and subject to annual review.')
    Story.append(Paragraph(ptext, styles['Normal']))

    # Signature Placeholder
    Story.append(Spacer(1, 48))
    ptext = '________________________'
    Story.append(Paragraph(ptext, styles['KeyDetail']))
    ptext = 'Authorized Seal and Signature'
    Story.append(Paragraph(ptext, styles['KeyDetail']))


    doc.build(Story)
    print(f"Successfully created {FILE_NAME}")

if __name__ == '__main__':
    create_mock_business_license()
