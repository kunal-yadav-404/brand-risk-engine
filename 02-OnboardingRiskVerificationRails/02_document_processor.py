# document_processor.py
from google.cloud import documentai
from google.cloud import storage
import json

class DocumentProcessor:
    def __init__(self, project_id, processor_id, location="us"):
        self.project_id = project_id
        self.processor_id = processor_id
        self.location = location
        self.client = documentai.DocumentProcessorServiceClient()
        
    def process_document(self, gcs_uri, merchant_id):
        """Process uploaded business documents"""
        
        # Document AI request
        name = self.client.processor_path(self.project_id, self.location, self.processor_id)
        
        # For GCS files
        gcs_document = documentai.GcsDocument(gcs_uri=gcs_uri)
        document = documentai.Document(gcs_document=gcs_document)
        
        request = documentai.ProcessRequest(name=name, document=document)
        result = self.client.process_document(request=request)
        
        # Extract key fields
        extracted_data = self._extract_business_fields(result.document)
        
        # Validate against merchant application
        validation_score = self._validate_document_consistency(extracted_data, merchant_id)
        
        return {
            "merchant_id": merchant_id,
            "extracted_fields": extracted_data,
            "validation_score": validation_score,
            "anomalies": self._detect_anomalies(extracted_data)
        }
    
    def _extract_business_fields(self, document):
        """Extract business registration fields"""
        fields = {}
        
        for page in document.pages:
            for form_field in page.form_fields:
                field_name = form_field.field_name.text_anchor.content
                field_value = form_field.field_value.text_anchor.content
                
                # Map to standardized fields
                if "business name" in field_name.lower():
                    fields["business_name"] = field_value
                elif "registration" in field_name.lower():
                    fields["registration_number"] = field_value
                elif "address" in field_name.lower():
                    fields["business_address"] = field_value
                elif "tax" in field_name.lower():
                    fields["tax_id"] = field_value
                    
        return fields
    
    def _validate_document_consistency(self, extracted_data, merchant_id):
        """Check document data against application"""
        # Query merchant application data
        from google.cloud import bigquery
        
        client = bigquery.Client()
        query = f"""
        SELECT name, contact_info
        FROM `brand_risk_engine.onboarding`
        WHERE merchant_id = '{merchant_id}'
        """
        
        results = client.query(query).to_dataframe()
        if results.empty:
            return 0.0
            
        app_data = results.iloc[0]
        
        # Basic name matching
        name_match = 0.0
        if extracted_data.get("business_name"):
            name_similarity = self._calculate_similarity(
                extracted_data["business_name"], 
                app_data["name"]
            )
            name_match = name_similarity
            
        return name_match
    
    def _detect_anomalies(self, extracted_data):
        """Detect document anomalies"""
        anomalies = []
        
        # Check for missing critical fields
        required_fields = ["business_name", "registration_number"]
        for field in required_fields:
            if not extracted_data.get(field):
                anomalies.append(f"Missing {field}")
                
        # Check for suspicious patterns
        if extracted_data.get("registration_number"):
            reg_num = extracted_data["registration_number"]
            if len(reg_num) < 5 or reg_num.isalpha():
                anomalies.append("Suspicious registration number format")
                
        return anomalies
    
    def _calculate_similarity(self, text1, text2):
        """Simple text similarity"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()