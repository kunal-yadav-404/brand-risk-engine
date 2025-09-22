# reputation_pipeline.py
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json

class ParseReputationData(beam.DoFn):
    def process(self, element):
        try:
            data = json.loads(element)
            yield {
                'merchant_id': data.get('merchant_id'),
                'source': data.get('source'),
                'mention_id': data.get('mention_id'),
                'text': data.get('text'),
                'sentiment': data.get('sentiment', 0.0),
                'timestamp': data.get('timestamp')
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
             subscription=f'projects/{PROJECT_ID}/subscriptions/reputation-dataflow-sub')
         | 'Parse Data' >> beam.ParDo(ParseReputationData())
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             table=f'{PROJECT_ID}:brand_risk_engine.reputation',
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))

if __name__ == '__main__':
    run_pipeline()