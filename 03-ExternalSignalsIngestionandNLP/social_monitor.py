# social_monitor.py
import json
import random
from datetime import datetime, timedelta
from google.cloud import pubsub_v1

class SocialMediaSimulator:
    """Simulates social media mentions for demo purposes"""
    
    def __init__(self, project_id, topic_name):
        self.project_id = project_id
        self.topic_name = topic_name
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_name)
        
        # Sample social media posts for demo
        self.sample_posts = [
            {"text": "Great payment experience with Worldline! Fast and secure.", "sentiment": 0.8},
            {"text": "Worldline payment failed again. So frustrating!", "sentiment": -0.6},
            {"text": "Just processed payment through Worldline merchant. Smooth transaction.", "sentiment": 0.5},
            {"text": "Worldline service down? Can't complete my purchase.", "sentiment": -0.7},
            {"text": "Love how easy Worldline makes online payments", "sentiment": 0.7},
            {"text": "Worldline fees are getting too high", "sentiment": -0.4},
            {"text": "Merchant using Worldline = instant trust for me", "sentiment": 0.6},
            {"text": "Suspicious transaction from Worldline merchant", "sentiment": -0.5}
        ]
    
    def generate_social_mentions(self, count=10):
        """Generate simulated social media mentions"""
        mentions = []
        
        for i in range(count):
            post = random.choice(self.sample_posts)
            mention = {
                'mention_id': f"social_{datetime.now().timestamp()}_{i}",
                'source': random.choice(['twitter', 'facebook', 'reddit']),
                'text': post['text'],
                'sentiment': post['sentiment'],
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat(),
                'merchant_id': 'WORLDLINE_GLOBAL',
                'user_id': f"user_{random.randint(1000, 9999)}",
                'engagement': random.randint(1, 100)
            }
            mentions.append(mention)
        
        return mentions
    
    def publish_mentions(self, mentions):
        """Publish to reputation stream"""
        for mention in mentions:
            message_data = json.dumps(mention).encode('utf-8')
            self.publisher.publish(self.topic_path, message_data)
        
        print(f"Published {len(mentions)} social mentions")