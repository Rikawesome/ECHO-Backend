require('dotenv').config();
const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const jwt = require('jsonwebtoken');
const axios = require('axios');
const cors = require('cors');

const app = express();
const server = http.createServer(app);

// ====================
// CRITICAL CONFIGURATION - NO DEFAULTS FOR SECRETS
// ====================
const PORT = process.env.PORT || 3000;
const PYTHON_BACKEND = process.env.PYTHON_BACKEND || 'https://echo-backend.up.railway.app';

// SECURITY: Fail fast if JWT secret is not set
const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET) {
  console.error('❌ FATAL: JWT_SECRET environment variable is not set.');
  console.error('   Set it in Railway dashboard: Settings → Variables');
  process.exit(1);
}

// ====================
// ESSENTIAL MIDDLEWARE
// ====================
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request Logger
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`);
  next();
});

// ====================
// IMPROVED AUTHENTICATION MIDDLEWARE
// ====================
const authenticate = (req, res, next) => {
  // Use req.path for exact path matching without query params
  const requestPath = req.path;
  const publicPaths = ['/auth/login', '/auth/register', '/health', '/'];
  
  if (publicPaths.includes(requestPath)) {
    return next();
  }

  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      success: false,
      error: 'Access denied. No token provided.',
      code: 'NO_TOKEN'
    });
  }

  const token = authHeader.split(' ')[1];
  
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    
    // Enhanced validation
    if (!decoded.userId && !decoded.id && !decoded.user_id) {
      return res.status(401).json({
        success: false,
        error: 'Invalid token format',
        code: 'INVALID_TOKEN'
      });
    }
    
    // Standardize user object
    req.user = {
      id: decoded.userId || decoded.id || decoded.user_id,
      email: decoded.email,
      role: decoded.role,
      schoolId: decoded.schoolId
    };
    
    next();
  } catch (error) {
    const isExpired = error.name === 'TokenExpiredError';
    const message = isExpired ? 'Token expired. Please login again.' : 'Invalid token.';
    const code = isExpired ? 'TOKEN_EXPIRED' : 'INVALID_TOKEN';
    
    return res.status(401).json({
      success: false,
      error: message,
      code: code
    });
  }
};

// ====================
// SIMPLIFIED WEBSOCKET (OPTIONAL - CAN BE COMMENTED OUT)
// ====================
const wss = new WebSocketServer({ server, path: '/ws' });
const activeConnections = new Map();

wss.on('connection', (ws, req) => {
  try {
    // Parse token from query parameters
    const url = require('url').parse(req.url, true);
    const token = url.query.token;

    if (!token) {
      ws.close(1008, 'No token');
      return;
    }

    const decoded = jwt.verify(token, JWT_SECRET);
    const userId = decoded.userId || decoded.id || decoded.user_id;
    
    if (!userId) {
      ws.close(1008, 'Invalid token');
      return;
    }

    activeConnections.set(userId.toString(), ws);
    console.log(`✅ WebSocket: User ${userId} connected`);

    ws.on('message', async (data) => {
      try {
        const message = JSON.parse(data.toString());
        console.log(`WebSocket message from ${userId}:`, message);
        // Basic message handling - can be expanded
        if (message.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
        }
      } catch (error) {
        ws.send(JSON.stringify({
          type: 'error',
          error: 'Invalid message format'
        }));
      }
    });

    ws.on('close', () => {
      activeConnections.delete(userId.toString());
      console.log(`⚠️ WebSocket: User ${userId} disconnected`);
    });

  } catch (error) {
    console.log('WebSocket auth failed:', error.message);
    ws.close(1008, 'Auth failed');
  }
});

// ====================
// CORE PROXY FUNCTION (FIXED VERSION - NO DEADLOCK)
// ====================
const createProxyHandler = (requiresAuth = true) => {
  return async (req, res) => {
    // Apply auth if required
    if (requiresAuth) {
      return new Promise((resolve) => {
        authenticate(req, res, () => {
          // Authentication succeeded, now proxy the request
          proxyRequest(req, res).then(resolve).catch(resolve);
        });
      });
    } else {
      // No auth required, just proxy
      await proxyRequest(req, res);
    }
  };
};

// Helper function to handle the actual proxy request
async function proxyRequest(req, res) {
  const targetURL = `${PYTHON_BACKEND}${req.originalUrl}`;
  
  try {
    const response = await axios({
      method: req.method,
      url: targetURL,
      data: req.body,
      params: req.query,
      headers: {
        ...req.headers,
        'x-user-id': req.user?.id,
        'x-user-role': req.user?.role,
        'x-forwarded-by': 'echo-gateway',
        host: new URL(PYTHON_BACKEND).host
      },
      validateStatus: () => true // Pass through all status codes
    });

    // Forward the response exactly as received
    res.status(response.status).json(response.data);
    
  } catch (error) {
    console.error(`🔴 Proxy error for ${req.method} ${req.originalUrl}:`, error.message);
    
    res.status(502).json({
      success: false,
      error: 'Backend service unavailable',
      code: 'BACKEND_ERROR',
      path: req.originalUrl
    });
  }
}

// ====================
// ROUTE DEFINITIONS (COMPLETE SET)
// ====================

// Public routes (no auth required) - ALL HTTP METHODS
app.all('/auth/login', createProxyHandler(false));
app.all('/auth/register', createProxyHandler(false));

// School onboarding routes (auth required)
app.all('/schools/join', createProxyHandler(true));
app.all('/schools/create-and-join', createProxyHandler(true));

// Protected API routes (auth required)
app.all('/api/schools*', createProxyHandler(true));
app.all('/api/classes*', createProxyHandler(true));
app.all('/api/teachers*', createProxyHandler(true));
app.all('/api/students*', createProxyHandler(true));
app.all('/api/subjects*', createProxyHandler(true));
app.all('/api/grades*', createProxyHandler(true));
app.all('/api/reports*', createProxyHandler(true));
app.all('/api/payments*', createProxyHandler(true));
app.all('/api/users*', createProxyHandler(true));

// Catch-all for other /api routes
app.all('/api/*', createProxyHandler(true));

// ====================
// HEALTH & INFO ENDPOINTS (FIXED - ALWAYS RETURNS 200)
// ====================
app.get('/health', async (req, res) => {
  const healthData = {
    success: true,
    service: 'Echo Gateway',
    status: 'healthy',
    timestamp: new Date().toISOString(),
    websocket: wss.clients.size,
    environment: process.env.NODE_ENV || 'development',
    backend: 'checking'
  };
  
  try {
    // Check backend but don't fail if it's down
    await axios.get(`${PYTHON_BACKEND}/health`, { timeout: 3000 });
    healthData.backend = 'connected';
  } catch (error) {
    healthData.backend = 'disconnected';
    healthData.status = 'degraded';
    healthData.backendError = error.message;
  }
  
  // Always return 200 so Railway doesn't restart us
  res.status(200).json(healthData);
});

app.get('/', (req, res) => {
  res.json({
    service: 'Echo Schools Platform Gateway',
    version: '1.1',
    status: 'operational',
    documentation: 'Routes proxy to Flask backend',
    endpoints: {
      auth: [
        'POST /auth/login',
        'POST /auth/register'
      ],
      schools: [
        'POST /schools/join (auth required)',
        'POST /schools/create-and-join (auth required)'
      ],
      api: [
        '/api/schools/*',
        '/api/classes/*',
        '/api/teachers/*',
        '/api/students/*',
        '/api/grades/*',
        '/api/reports/*'
      ],
      monitoring: 'GET /health',
      websocket: 'GET /ws?token=JWT_TOKEN'
    },
    note: 'All /api/* routes require Authorization: Bearer <token> header'
  });
});

// ====================
// ERROR HANDLER (FIXED - NO req.id)
// ====================
app.use((err, req, res, next) => {
  console.error('🔴 Gateway error:', err.stack || err.message);
  res.status(500).json({
    success: false,
    error: 'Internal gateway error',
    code: 'GATEWAY_ERROR'
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: `Route not found: ${req.method} ${req.originalUrl}`,
    code: 'NOT_FOUND',
    suggestions: [
      'Check the URL path',
      'Verify the HTTP method (GET, POST, etc.)',
      'Visit GET / for available endpoints'
    ]
  });
});

// ====================
// START SERVER
// ====================
server.listen(PORT, () => {
  console.log(`
  ╔═══════════════════════════════════════╗
  ║       Echo Gateway - PRODUCTION       ║
  ╠═══════════════════════════════════════╣
  ║  Status:    FIXED & STABLE            ║
  ║  HTTP:      http://localhost:${PORT}      ║
  ║  Backend:   ${PYTHON_BACKEND}  ║
  ║  WebSocket: ws://localhost:${PORT}/ws     ║
  ╚═══════════════════════════════════════╝
  
  ✅ Public routes: /auth/login, /auth/register
  ✅ School routes: /schools/join, /schools/create-and-join
  ✅ Protected API: All /api/* routes
  ✅ Health check: GET /health (always returns 200)
  ⚠️  JWT_SECRET: ${JWT_SECRET ? '✓ Set' : '✗ NOT SET - SERVER WILL EXIT'}
  `);
});