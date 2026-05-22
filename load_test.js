import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
export const errorRate = new Rate('errors');
export const ingestLatency = new Trend('ingest_latency');
export const chatLatency = new Trend('chat_latency');

export const options = {
  stages: [
    { duration: '30s', target: 20 }, // Ramp-up to 20 users
    { duration: '1m', target: 50 },  // Peak 50 concurrent users
    { duration: '30s', target: 0 },  // Ramp-down
  ],
  thresholds: {
    // 95% of requests must complete below 3000ms
    'http_req_duration': ['p(95)<3000'],
    // Error rate must be strictly less than 1%
    'errors': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://real-estate-ai-lead-agent-2.onrender.com';

export default function () {
  // Generate a unique session ID for every iteration to test concurrency properly
  const session_id = `k6_user_${__VU}_${__ITER}`;

  // ==========================================
  // 1. Test the Ingest API (Lead Creation)
  // ==========================================
  const ingestPayload = JSON.stringify({
    session_id: session_id,
    source: 'website',
    name: 'K6 Load Tester',
    phone: '1234567890',
    intent: 'buy',
    whatsapp_opt_in: false
  });

  const ingestParams = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const ingestRes = http.post(`${BASE_URL}/api/v1/ingest`, ingestPayload, ingestParams);

  const ingestSuccess = check(ingestRes, {
    'ingest status is 200': (r) => r.status === 200,
    'ingest response has success status': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === 'success';
      } catch (e) {
        return false;
      }
    }
  });

  errorRate.add(!ingestSuccess);
  ingestLatency.add(ingestRes.timings.duration);

  // Think time between actions
  sleep(1);

  // ==========================================
  // 2. Test the Chat API (LLM Integration)
  // ==========================================
  // Use URL-encoded query parameters for FastAPI query/path vars
  const chatUrl = `${BASE_URL}/api/v1/chat?session_id=${session_id}&message=What%20properties%20do%20you%20have%3F`;

  const chatRes = http.post(chatUrl, null, {
    headers: {
      'Accept': 'application/json'
    }
  });

  const chatSuccess = check(chatRes, {
    'chat status is 200': (r) => r.status === 200,
    'chat response has reply': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === 'success' && body.reply !== undefined;
      } catch (e) {
        return false;
      }
    }
  });

  errorRate.add(!chatSuccess);
  chatLatency.add(chatRes.timings.duration);

  // Pacing
  sleep(2);
}
