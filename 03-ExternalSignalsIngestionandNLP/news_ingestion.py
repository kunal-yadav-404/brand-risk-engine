# news_ingestion.py
import requests
import json
from datetime import datetime, timedelta
from google.cloud import pubsub_v1

class NewsMonitor:
    def __init__(self, project_id, topic_name):
        self.project_id = project_id
        self.topic_name = topic_name
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_name)
        
        # Free news APIs (for demo)
        self.news_sources = {
            'newsapi': 'b05563b2a9054bab8ea1dbf8f5b5ab0e',  # Get free key from newsapi.org
            'guardian': 'fd0f8798-15b0-424b-9367-8b341fbee81b'  # Get free key from guardian.com
        }
    
    def fetch_worldline_mentions(self):
        """Fetch recent mentions of Worldline"""
        mentions = []
        
        # NewsAPI search
        mentions.extend(self._fetch_from_newsapi())
        
        # Guardian API search
        mentions.extend(self._fetch_from_guardian())
        
        return mentions
    
    def _fetch_from_newsapi(self):
        """Fetch from NewsAPI"""
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': 'Worldline OR "payment processing" OR "merchant services"',
                'from': (datetime.now() - timedelta(hours=24)).isoformat(),
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': self.news_sources['newsapi']
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                articles = response.json().get('articles', [])
                return self._format_news_data(articles, 'newsapi')
        except Exception as e:
            print(f"NewsAPI error: {e}")
        
        return []
    
    def _fetch_from_guardian(self):
        """Fetch from Guardian API"""
        try:
            url = "https://content.guardianapis.com/search"
            params = {
                'q': 'Worldline',
                'from-date': (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d'),
                'show-fields': 'headline,body',
                'api-key': self.news_sources['guardian']
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                articles = response.json().get('response', {}).get('results', [])
                return self._format_guardian_data(articles)
        except Exception as e:
            print(f"Guardian API error: {e}")
        
        return []
    
    def _format_news_data(self, articles, source):
        """Format NewsAPI data"""
        formatted = []
        for article in articles:
            formatted.append({
                'mention_id': f"{source}_{hash(article['url'])}",
                'source': source,
                'title': article.get('title', ''),
                'text': article.get('description', '') + ' ' + article.get('content', ''),
                'url': article.get('url'),
                'published_at': article.get('publishedAt'),
                'merchant_id': 'WORLDLINE_GLOBAL',  # Global brand mentions
                'raw_data': json.dumps(article)
            })
        return formatted
    
    def _format_guardian_data(self, articles):
        """Format Guardian data"""
        formatted = []
        for article in articles:
            formatted.append({
                'mention_id': f"guardian_{article['id']}",
                'source': 'guardian',
                'title': article.get('webTitle', ''),
                'text': article.get('fields', {}).get('body', ''),
                'url': article.get('webUrl'),
                'published_at': article.get('webPublicationDate'),
                'merchant_id': 'WORLDLINE_GLOBAL',
                'raw_data': json.dumps(article)
            })
        return formatted
    
    def publish_mentions(self, mentions):
        """Publish mentions to Pub/Sub"""
        for mention in mentions:
            message_data = json.dumps(mention).encode('utf-8')
            self.publisher.publish(self.topic_path, message_data)
        
        print(f"Published {len(mentions)} mentions to {self.topic_name}")