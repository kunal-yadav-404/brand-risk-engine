import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
import logging
import sys

# --- HARDCODED CONFIGURATION START (Copied from onboarding_pipeline.py) ---
PROJECT_ID = "brand-risk-engine-1758962489"
REGION = "us-central1"
# --- HARDCODED CONFIGURATION END ---

# Configure logging for better visibility during local runs and on Dataflow logs
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class ParseReputationData(beam.DoFn):
    """
    Parses incoming JSON messages from Pub/Sub and prepares them for BigQuery.
    """
    def process(self, element):
        try:
            # Decode the message body (Pub/Sub sends bytes, Beam reads them as bytes)
            json_string = element.decode('utf-8')
            data = json.loads(json_string)
            
            # Prepare the row structure for BigQuery
            yield {
                'merchant_id': data.get('merchant_id'),
                'source': data.get('source'),
                'mention_id': data.get('mention_id'),
                'text': data.get('text'),
                'sentiment': data.get('sentiment', 0.0),
                # Ensure timestamp is correctly formatted (e.g., ISO 8601 string)
                'timestamp': data.get('timestamp') 
                # BigQuery will automatically handle the created_at default
            }
        except Exception as e:
            logging.error(f"Error parsing element: {element}. Error: {e}")
            # Dropping unparsable elements


def run_pipeline():
    """Builds and runs the Apache Beam pipeline using hardcoded configurations."""
    
    pipeline_options = PipelineOptions([
        '--project=' + PROJECT_ID,
        '--region=' + REGION,
        '--runner=DataflowRunner',
        '--temp_location=gs://brand-risk-temp/temp',
        '--staging_location=gs://brand-risk-temp/staging',
        # CRITICAL: Add streaming flag for unbounded Pub/Sub source
        '--streaming' 
    ])
    
    # Define the BigQuery table and Pub/Sub subscription paths using the constant PROJECT_ID
    BQ_TABLE_SPEC = f'{PROJECT_ID}:brand_risk_engine.reputation'
    PUB_SUB_SUBSCRIPTION = f'projects/{PROJECT_ID}/subscriptions/reputation-dataflow-sub'

    logging.info(f"Writing to BigQuery table: {BQ_TABLE_SPEC}")
    logging.info(f"Reading from Pub/Sub subscription: {PUB_SUB_SUBSCRIPTION}")
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        (pipeline
         | 'Read from Pub/Sub' >> beam.io.ReadFromPubSub(subscription=PUB_SUB_SUBSCRIPTION)
         | 'Parse Data' >> beam.ParDo(ParseReputationData())
         # CRITICAL: Window the unbounded PCollection (e.g., into 60-second batches) 
         # to enable batching required by WriteToBigQuery.
         | 'Window Data' >> beam.WindowInto(beam.window.FixedWindows(60))
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             table=BQ_TABLE_SPEC,
             # Using WRITE_APPEND to add new data rows
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))

if __name__ == '__main__':
    run_pipeline()
