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
  const publicPaths = ['/auth/login', '/auth/register', '/health', '/'];
  if (publicPaths.includes(req.path)) {
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
  const url = new URL(req.url, `http://${req.headers.host}`);
  const token = url.searchParams.get('token');

  if (!token) {
    ws.close(1008, 'No token');
    return;
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const userId = decoded.userId || decoded.id || decoded.user_id;
    
    if (!userId) {
      ws.close(1008, 'Invalid token');
      return;
    }

    activeConnections.set(userId.toString(), ws);
    console.log(`✅ WebSocket: User ${userId} connected`);

    ws.on('close', () => {
      activeConnections.delete(userId.toString());
      console.log(`⚠️ WebSocket: User ${userId} disconnected`);
    });

  } catch (error) {
    ws.close(1008, 'Auth failed');
  }
});

// ====================
// CORE PROXY FUNCTION
// ====================
const createProxyHandler = (requiresAuth = true) => {
  return async (req, res) => {
    // Apply auth if required
    if (requiresAuth) {
      const authResult = await new Promise((resolve) => {
        authenticate(req, res, () => resolve(true));
      });
      if (!authResult) return; // Auth middleware already sent response
    }

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
      
      const status = error.response?.status || 502;
      const message = error.response?.data?.error || 'Backend service unavailable';
      
      res.status(status).json({
        success: false,
        error: message,
        code: 'BACKEND_ERROR',
        path: req.originalUrl
      });
    }
  };
};

// ====================
// ROUTE DEFINITIONS
// ====================

// Public routes (no auth required)
app.post('/auth/login', createProxyHandler(false));
app.post('/auth/register', createProxyHandler(false));

// Protected API routes (auth required)
app.all('/api/schools*', createProxyHandler(true));
app.all('/api/classes*', createProxyHandler(true));
app.all('/api/teachers*', createProxyHandler(true));
app.all('/api/students*', createProxyHandler(true));
app.all('/api/subjects*', createProxyHandler(true));
app.all('/api/grades*', createProxyHandler(true));
app.all('/api/reports*', createProxyHandler(true));
app.all('/api/payments*', createProxyHandler(true));

// User management (mixed auth - handled in proxy)
app.all('/api/users*', createProxyHandler(true));

// ====================
// HEALTH & INFO ENDPOINTS
// ====================
app.get('/health', async (req, res) => {
  try {
    // Check if Python backend is reachable
    await axios.get(`${PYTHON_BACKEND}/health`, { timeout: 5000 });
    
    res.json({
      success: true,
      service: 'Echo Gateway',
      status: 'healthy',
      timestamp: new Date().toISOString(),
      backend: 'connected',
      websocket: wss.clients.size,
      environment: process.env.NODE_ENV || 'development'
    });
  } catch (error) {
    res.status(503).json({
      success: false,
      service: 'Echo Gateway',
      status: 'degraded',
      error: 'Backend unreachable',
      backend: PYTHON_BACKEND
    });
  }
});

app.get('/', (req, res) => {
  res.json({
    service: 'Echo Schools Platform Gateway',
    version: '1.0',
    status: 'operational',
    documentation: 'All /api/* routes proxy to Flask backend',
    endpoints: {
      auth: ['POST /auth/login', 'POST /auth/register'],
      api: [
        '/api/schools/*',
        '/api/classes/*',
        '/api/teachers/*',
        '/api/students/*',
        '/api/grades/*',
        '/api/reports/*'
      ],
      monitoring: 'GET /health'
    }
  });
});

// ====================
// ERROR HANDLER
// ====================
app.use((err, req, res, next) => {
  console.error('🔴 Gateway error:', err.stack);
  res.status(500).json({
    success: false,
    error: 'Internal gateway error',
    code: 'GATEWAY_ERROR',
    requestId: req.id
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: `Route not found: ${req.method} ${req.originalUrl}`,
    code: 'NOT_FOUND'
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
  ║  Status:    SECURE & SIMPLIFIED       ║
  ║  HTTP:      http://localhost:${PORT}      ║
  ║  Backend:   ${PYTHON_BACKEND}  ║
  ║  WebSocket: ws://localhost:${PORT}/ws     ║
  ╚═══════════════════════════════════════╝
  
  ✅ Public routes: /auth/login, /auth/register
  ✅ Protected API: All /api/* routes
  ✅ Health check: GET /health
  ⚠️  JWT_SECRET: ${JWT_SECRET ? '✓ Set' : '✗ NOT SET - SERVER WILL EXIT'}
  `);
});