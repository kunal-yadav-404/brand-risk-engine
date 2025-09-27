import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
import logging
import sys

# --- HARDCODED CONFIGURATION START ---
# Defining these variables directly as requested.
# For production use, it is generally recommended to pass these via command-line options.
PROJECT_ID = "brand-risk-engine-1758962489"
REGION = "us-central1"
# Note: ZONE is usually derived from the REGION by Dataflow and is not required here.
# --- HARDCODED CONFIGURATION END ---

# Configure logging for better visibility during local runs and on Dataflow logs
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class ParseOnboardingData(beam.DoFn):
    """
    Parses incoming JSON messages from Pub/Sub and prepares them for BigQuery.
    Note: The 'contact_info' field is JSON in BigQuery, so we serialize the Python 
    dict back into a JSON string before writing.
    """
    def process(self, element):
        try:
            # Decode the message body (Pub/Sub sends bytes, Beam reads them as bytes)
            # The .decode('utf-8') assumes the Pub/Sub message body is a UTF-8 string.
            json_string = element.decode('utf-8')
            data = json.loads(json_string)
            
            # Prepare the row structure for BigQuery
            yield {
                'merchant_id': data.get('merchant_id'),
                'name': data.get('name'),
                'website': data.get('website'),
                'domain_age': data.get('domain_age', 0),
                # Serialize the contact_info dict back to a JSON string for the BigQuery JSON column
                'contact_info': json.dumps(data.get('contact_info', {})),
                'document_status': data.get('document_status', 'pending'),
                'verification_score': 0.0,
                'risk_score': 0.0,
                'explain_text': 'Initial processing',
                # BigQuery will automatically handle created_at/updated_at defaults
            }
        except Exception as e:
            logging.error(f"Error parsing element: {element}. Error: {e}")
            # Dropping the unparsable element, but you might want to write it to a dead-letter queue (DLQ)
            # using a side-output for robust production pipelines.


def run_pipeline():
    """Builds and runs the Apache Beam pipeline using hardcoded configurations."""
    
    # The list now uses the defined constants PROJECT_ID and REGION
    pipeline_options = PipelineOptions([
        '--project=' + PROJECT_ID,
        '--region=' + REGION,
        '--runner=DataflowRunner',
        '--temp_location=gs://brand-risk-temp/temp',
        '--staging_location=gs://brand-risk-temp/staging',
        # Crucially, add streaming flag when using DataflowRunner with Pub/Sub
        '--streaming'
    ])
    
    # Define the BigQuery table and Pub/Sub subscription paths using the constant PROJECT_ID
    BQ_TABLE_SPEC = f'{PROJECT_ID}:brand_risk_engine.onboarding'
    PUB_SUB_SUBSCRIPTION = f'projects/{PROJECT_ID}/subscriptions/onboarding-dataflow-sub'

    logging.info(f"Writing to BigQuery table: {BQ_TABLE_SPEC}")
    logging.info(f"Reading from Pub/Sub subscription: {PUB_SUB_SUBSCRIPTION}")
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        (pipeline
         | 'Read from Pub/Sub' >> beam.io.ReadFromPubSub(subscription=PUB_SUB_SUBSCRIPTION)
         | 'Parse Data' >> beam.ParDo(ParseOnboardingData())
         # RESOLVES GroupByKey ERROR: Window the unbounded PCollection into 60-second batches 
         # before writing to BigQuery.
         | 'Window Data' >> beam.WindowInto(beam.window.FixedWindows(60))
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             table=BQ_TABLE_SPEC,
             # Using WRITE_APPEND to add new data rows
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))

if __name__ == '__main__':
    run_pipeline()