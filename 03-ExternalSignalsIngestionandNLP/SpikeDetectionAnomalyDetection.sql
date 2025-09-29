-- Create spike detection view
CREATE OR REPLACE VIEW `brand_risk_engine.sentiment_monitoring` AS
WITH hourly_sentiment AS (
  SELECT 
    merchant_id,
    source,
    DATETIME_TRUNC(DATETIME(timestamp), HOUR) as hour_bucket,
    AVG(sentiment) as avg_sentiment,
    COUNT(*) as mention_count,
    STDDEV(sentiment) as sentiment_stddev
  FROM `brand_risk_engine.reputation`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY merchant_id, source, hour_bucket
),
sentiment_baselines AS (
  SELECT 
    merchant_id,
    source,
    AVG(avg_sentiment) as baseline_sentiment,
    STDDEV(avg_sentiment) as sentiment_variance,
    AVG(mention_count) as baseline_volume
  FROM hourly_sentiment
  WHERE hour_bucket <= DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 24 HOUR)
  GROUP BY merchant_id, source
),
current_metrics AS (
  SELECT 
    hs.*,
    sb.baseline_sentiment,
    sb.sentiment_variance,
    sb.baseline_volume
  FROM hourly_sentiment hs
  LEFT JOIN sentiment_baselines sb 
    ON hs.merchant_id = sb.merchant_id AND hs.source = sb.source
  WHERE hs.hour_bucket >= DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 24 HOUR)
)
SELECT 
  *,
  -- Sentiment spike detection
  CASE 
    WHEN baseline_sentiment IS NULL THEN 'INSUFFICIENT_DATA'
    WHEN avg_sentiment < (baseline_sentiment - 2 * sentiment_variance) THEN 'NEGATIVE_SPIKE'
    WHEN avg_sentiment > (baseline_sentiment + 2 * sentiment_variance) THEN 'POSITIVE_SPIKE'
    ELSE 'NORMAL'
  END as sentiment_alert,
  
  -- Volume spike detection
  CASE 
    WHEN baseline_volume IS NULL THEN 'INSUFFICIENT_DATA'
    WHEN mention_count > (baseline_volume * 3) THEN 'VOLUME_SPIKE'
    ELSE 'NORMAL_VOLUME'
  END as volume_alert,
  
  -- Combined risk score
  CASE 
    WHEN avg_sentiment < -0.5 AND mention_count > (COALESCE(baseline_volume, 1) * 2) THEN 0.9
    WHEN avg_sentiment < -0.3 THEN 0.7
    WHEN mention_count > (COALESCE(baseline_volume, 1) * 3) THEN 0.6
    ELSE 0.2
  END as reputation_risk_score
  
FROM current_metrics;

-- Create reputation risk aggregation
CREATE OR REPLACE TABLE `brand_risk_engine.reputation_risk_summary` AS
SELECT 
  merchant_id,
  AVG(reputation_risk_score) as avg_reputation_risk,
  MAX(reputation_risk_score) as max_reputation_risk,
  COUNT(CASE WHEN sentiment_alert != 'NORMAL' THEN 1 END) as alert_count,
  COUNT(CASE WHEN volume_alert = 'VOLUME_SPIKE' THEN 1 END) as volume_spike_count,
  CURRENT_TIMESTAMP() as last_updated
FROM `brand_risk_engine.sentiment_monitoring`
GROUP BY merchant_id;