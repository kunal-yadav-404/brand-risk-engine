# domain_checker.py
import requests
import whois
import ssl
import socket
from datetime import datetime, timedelta
from urllib.parse import urlparse
import dns.resolver

class DomainChecker:
    def __init__(self):
        self.blacklisted_domains = self._load_blacklists()
        self.suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.click', '.download']
        
    def check_domain(self, website_url, merchant_name):
        """Comprehensive domain verification"""
        if not website_url:
            return {"score": 0.0, "issues": ["No website provided"]}
            
        domain = self._extract_domain(website_url)
        checks = {}
        
        # Basic domain info
        checks["domain_age"] = self._get_domain_age(domain)
        checks["ssl_valid"] = self._check_ssl(domain)
        checks["dns_configured"] = self._check_dns(domain)
        checks["blacklist_status"] = self._check_blacklists(domain)
        checks["tld_reputation"] = self._check_tld_reputation(domain)
        checks["content_analysis"] = self._analyze_website_content(website_url, merchant_name)
        
        # Calculate overall score
        score = self._calculate_domain_score(checks)
        issues = self._identify_issues(checks)
        
        return {
            "domain": domain,
            "score": score,
            "checks": checks,
            "issues": issues
        }
    
    def _extract_domain(self, url):
        """Extract domain from URL"""
        try:
            parsed = urlparse(url if url.startswith('http') else f'http://{url}')
            return parsed.netloc
        except:
            return url
    
    def _get_domain_age(self, domain):
        """Check domain registration age"""
        try:
            w = whois.whois(domain)
            if w.creation_date:
                creation_date = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                age_days = (datetime.now() - creation_date).days
                return age_days
        except:
            return 0
        return 0
    
    def _check_ssl(self, domain):
        """Verify SSL certificate"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    return cert is not None
        except:
            return False
    
    def _check_dns(self, domain):
        """Check DNS configuration"""
        try:
            dns.resolver.resolve(domain, 'A')
            return True
        except:
            return False
    
    def _check_blacklists(self, domain):
        """Check against blacklists"""
        return domain not in self.blacklisted_domains
    
    def _check_tld_reputation(self, domain):
        """Check TLD reputation"""
        tld = '.' + domain.split('.')[-1]
        return tld not in self.suspicious_tlds
    
    def _analyze_website_content(self, url, merchant_name):
        """Basic website content analysis"""
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            content = response.text.lower()
            
            # Check if merchant name appears on website
            name_present = merchant_name.lower() in content
            
            # Check for suspicious patterns
            suspicious_patterns = ['click here to claim', 'get rich quick', 'guaranteed profit']
            has_suspicious_content = any(pattern in content for pattern in suspicious_patterns)
            
            # Check for minimal content (potential placeholder)
            is_minimal = len(content.strip()) < 500
            
            return {
                "name_match": name_present,
                "suspicious_content": has_suspicious_content,
                "minimal_content": is_minimal,
                "accessible": True
            }
        except:
            return {
                "name_match": False,
                "suspicious_content": False,
                "minimal_content": False,
                "accessible": False
            }
    
    def _calculate_domain_score(self, checks):
        """Calculate overall domain trustworthiness score"""
        score = 0.0
        
        # Domain age (30% weight)
        age_days = checks.get("domain_age", 0)
        if age_days > 365:
            score += 0.3
        elif age_days > 90:
            score += 0.2
        elif age_days > 30:
            score += 0.1
            
        # SSL (20% weight)
        if checks.get("ssl_valid"):
            score += 0.2
            
        # DNS (10% weight)
        if checks.get("dns_configured"):
            score += 0.1
            
        # Blacklist (15% weight)
        if checks.get("blacklist_status"):
            score += 0.15
            
        # TLD reputation (10% weight)
        if checks.get("tld_reputation"):
            score += 0.1
            
        # Content analysis (15% weight)
        content = checks.get("content_analysis", {})
        if content.get("accessible") and content.get("name_match"):
            score += 0.1
        if not content.get("suspicious_content"):
            score += 0.05
            
        return min(score, 1.0)
    
    def _identify_issues(self, checks):
        """Identify specific issues"""
        issues = []
        
        if checks.get("domain_age", 0) < 30:
            issues.append("Very new domain (< 30 days)")
        if not checks.get("ssl_valid"):
            issues.append("No valid SSL certificate")
        if not checks.get("blacklist_status"):
            issues.append("Domain on blacklist")
        if not checks.get("tld_reputation"):
            issues.append("Suspicious TLD")
            
        content = checks.get("content_analysis", {})
        if not content.get("accessible"):
            issues.append("Website not accessible")
        if not content.get("name_match"):
            issues.append("Merchant name not found on website")
        if content.get("suspicious_content"):
            issues.append("Suspicious website content detected")
            
        return issues
    
    def _load_blacklists(self):
        """Load domain blacklists"""
        # In production, load from external threat intelligence feeds
        return {
            "malicious-site.com",
            "phishing-example.net",
            "fraud-domain.org"
        }