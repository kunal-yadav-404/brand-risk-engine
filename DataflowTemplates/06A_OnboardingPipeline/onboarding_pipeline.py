# onboarding_pipeline.py
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json

class ParseOnboardingData(beam.DoFn):
    def process(self, element):
        try:
            data = json.loads(element)
            yield {
                'merchant_id': data.get('merchant_id'),
                'name': data.get('name'),
                'website': data.get('website'),
                'domain_age': data.get('domain_age', 0),
                'contact_info': json.dumps(data.get('contact_info', {})),
                'document_status': data.get('document_status', 'pending'),
                'verification_score': 0.0,
                'risk_score': 0.0,
                'explain_text': 'Initial processing'
            }
        except Exception as e:
            print(f"Error parsing: {e}")

def run_pipeline():
    pipeline_options = PipelineOptions([
        '--project=' + PROJECT_ID,
        '--region=' + REGION,
        '--runner=DataflowRunner',
        '--temp_location=gs://brand-risk-temp/temp',
        '--staging_location=gs://brand-risk-temp/staging'
    ])
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        (pipeline
         | 'Read from Pub/Sub' >> beam.io.ReadFromPubSub(
             subscription=f'projects/{PROJECT_ID}/subscriptions/onboarding-dataflow-sub')
         | 'Parse Data' >> beam.ParDo(ParseOnboardingData())
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             table=f'{PROJECT_ID}:brand_risk_engine.onboarding',
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))

if __name__ == '__main__':
    run_pipeline()