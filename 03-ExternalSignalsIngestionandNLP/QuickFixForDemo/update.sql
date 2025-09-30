-- Update the sentiment monitoring view for demo purposes
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
    -- Use shorter baseline for demo (6 hours instead of 24)
    AVG(avg_sentiment) as baseline_sentiment,
    GREATEST(STDDEV(avg_sentiment), 0.1) as sentiment_variance, -- Minimum variance
    AVG(mention_count) as baseline_volume
  FROM hourly_sentiment
  WHERE hour_bucket <= DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 6 HOUR)
  GROUP BY merchant_id, source
),
current_metrics AS (
  SELECT 
    hs.*,
    COALESCE(sb.baseline_sentiment, 0.0) as baseline_sentiment, -- Default to neutral
    COALESCE(sb.sentiment_variance, 0.3) as sentiment_variance, -- Default variance
    COALESCE(sb.baseline_volume, 2.0) as baseline_volume        -- Default volume
  FROM hourly_sentiment hs
  LEFT JOIN sentiment_baselines sb 
    ON hs.merchant_id = sb.merchant_id AND hs.source = sb.source
  WHERE hs.hour_bucket >= DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 6 HOUR)
)
SELECT 
  *,
  -- Sentiment spike detection (more sensitive for demo)
  CASE 
    WHEN avg_sentiment < (baseline_sentiment - 1.5 * sentiment_variance) THEN 'NEGATIVE_SPIKE'
    WHEN avg_sentiment > (baseline_sentiment + 1.5 * sentiment_variance) THEN 'POSITIVE_SPIKE'
    ELSE 'NORMAL'
  END as sentiment_alert,
  
  -- Volume spike detection (more sensitive for demo)
  CASE 
    WHEN mention_count > (baseline_volume * 2) THEN 'VOLUME_SPIKE'
    ELSE 'NORMAL_VOLUME'
  END as volume_alert,
  
  -- Enhanced risk score calculation
  CASE 
    WHEN avg_sentiment < -0.5 AND mention_count > (baseline_volume * 1.5) THEN 0.9
    WHEN avg_sentiment < -0.3 THEN 0.7
    WHEN avg_sentiment < -0.1 THEN 0.5
    WHEN mention_count > (baseline_volume * 2) THEN 0.6
    WHEN avg_sentiment > 0.5 THEN 0.1 -- Very positive = low risk
    ELSE 0.3
  END as reputation_risk_score
  
FROM current_metrics;