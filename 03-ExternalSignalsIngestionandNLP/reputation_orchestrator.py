# reputation_orchestrator.py
import time
from news_ingestion import NewsMonitor
from social_monitor import SocialMediaSimulator

PROJECT_ID = "brand-risk-engine-1758962489"
REGION = "us-central1"

class ReputationOrchestrator:
    def __init__(self, project_id):
        self.project_id = project_id
        self.news_monitor = NewsMonitor(project_id, 'reputation-stream')
        self.social_simulator = SocialMediaSimulator(project_id, 'reputation-stream')
    
    def run_continuous_monitoring(self):
        """Run continuous reputation monitoring"""
        print("Starting reputation monitoring...")
        
        while True:
            try:
                # Fetch news mentions
                news_mentions = self.news_monitor.fetch_worldline_mentions()
                if news_mentions:
                    self.news_monitor.publish_mentions(news_mentions)
                
                # Generate social media mentions (for demo)
                social_mentions = self.social_simulator.generate_social_mentions(5)
                self.social_simulator.publish_mentions(social_mentions)
                
                print(f"Processed {len(news_mentions)} news mentions, {len(social_mentions)} social mentions")
                
                # Wait 5 minutes
                time.sleep(300)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(60)

if __name__ == '__main__':
    orchestrator = ReputationOrchestrator(PROJECT_ID)
    orchestrator.run_continuous_monitoring()