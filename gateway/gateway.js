require('dotenv').config();
const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const jwt = require('jsonwebtoken');
const axios = require('axios');
const https = require('https');
const cors = require('cors');

const app = express();
const server = http.createServer(app);

// ====================
// CRITICAL CONFIGURATION
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
// PERFORMANCE OPTIMIZATIONS
// ====================
const axiosInstance = axios.create({
  baseURL: PYTHON_BACKEND,
  timeout: 10000, // 10 second timeout
  httpsAgent: new https.Agent({
    keepAlive: true,
    keepAliveMsecs: 1000,
    maxSockets: 100,
    maxFreeSockets: 20,
    timeout: 10000,
    freeSocketTimeout: 30000
  }),
  maxRedirects: 0,
  headers: {
    'Connection': 'keep-alive',
    'X-Forwarded-By': 'echo-gateway-v1.4'
  }
});

// ====================
// OPTIMIZED MIDDLEWARE
// ====================
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-User-ID', 'X-User-Role']
}));

app.use(express.json({ 
  limit: '2mb',
  verify: (req, res, buf) => {
    req.rawBody = buf.toString();
  }
}));

app.use(express.urlencoded({ extended: false, limit: '2mb' }));

// Optimized Request Logger - only log in development
const isDevelopment = process.env.NODE_ENV !== 'production';
app.use((req, res, next) => {
  if (isDevelopment) {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`);
  }
  next();
});

// ====================
// FAST AUTHENTICATION MIDDLEWARE
// ====================
const authenticate = (req, res, next) => {
  // Use requestPath for better matching
  const requestPath = req.path.toLowerCase();
  const publicPaths = ['/login', '/register', '/health', '/'];
  
  // Exact match for public routes
  if (publicPaths.includes(requestPath) || requestPath.startsWith('/health')) {
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
    // FAST VERIFICATION: Verify signature only
    const decoded = jwt.verify(token, JWT_SECRET, { ignoreExpiration: false });
    
    // Simple user object creation
    req.user = {
      id: decoded.user_id || decoded.userId || decoded.id,
      email: decoded.email,
      role: decoded.role,
      schoolId: decoded.school_id || decoded.schoolId
    };
    
    next();
  } catch (error) {
    const isExpired = error.name === 'TokenExpiredError';
    return res.status(401).json({
      success: false,
      error: isExpired ? 'Token expired. Please login again.' : 'Invalid token.',
      code: isExpired ? 'TOKEN_EXPIRED' : 'INVALID_TOKEN'
    });
  }
};

// ====================
// SIMPLIFIED WEBSOCKET
// ====================
const wss = new WebSocketServer({ server, path: '/ws' });
const activeConnections = new Map();

wss.on('connection', (ws, req) => {
  try {
    const url = require('url').parse(req.url, true);
    const token = url.query.token;

    if (!token) {
      ws.close(1008, 'No token');
      return;
    }

    const decoded = jwt.verify(token, JWT_SECRET, { ignoreExpiration: false });
    const userId = decoded.user_id || decoded.userId || decoded.id;
    
    if (!userId) {
      ws.close(1008, 'Invalid token');
      return;
    }

    activeConnections.set(userId.toString(), ws);
    if (isDevelopment) {
      console.log(`✅ WebSocket: User ${userId} connected`);
    }

    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        if (message.type === 'ping') {
          ws.send(JSON.stringify({ 
            type: 'pong', 
            timestamp: new Date().toISOString() 
          }));
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
      if (isDevelopment) {
        console.log(`⚠️ WebSocket: User ${userId} disconnected`);
      }
    });

  } catch (error) {
    ws.close(1008, 'Auth failed');
  }
});

// ====================
// OPTIMIZED PROXY FUNCTION
// ====================
const createProxyHandler = (requiresAuth = true) => {
  return async (req, res) => {
    const startTime = Date.now();
    
    if (requiresAuth) {
      return authenticate(req, res, () => {
        handleProxyRequest(req, res, startTime);
      });
    } else {
      return handleProxyRequest(req, res, startTime);
    }
  };
};

// Fast proxy request handler
async function handleProxyRequest(req, res, startTime) {
  try {
    const targetURL = `${PYTHON_BACKEND}${req.originalUrl}`;
    
    const response = await axiosInstance({
      method: req.method,
      url: req.originalUrl, // Use relative URL since baseURL is set
      data: req.body,
      params: req.query,
      headers: {
        ...req.headers,
        'x-user-id': req.user?.id || '',
        'x-user-role': req.user?.role || '',
        'x-forwarded-by': 'echo-gateway-optimized',
        'x-request-start-time': startTime.toString(),
        'host': new URL(PYTHON_BACKEND).host,
        'connection': 'close' // Avoid connection reuse issues
      },
      validateStatus: () => true // Accept all status codes
    });

    const duration = Date.now() - startTime;
    
    // Log slow requests
    if (duration > 1000) {
      console.warn(`🐢 SLOW: ${req.method} ${req.originalUrl} ${response.status} ${duration}ms`);
    } else if (isDevelopment) {
      console.log(`✅ ${req.method} ${req.originalUrl} ${response.status} ${duration}ms`);
    }
    
    // Forward response
    res.status(response.status).json(response.data);
    
  } catch (error) {
    const duration = Date.now() - startTime;
    
    console.error(`🔴 Proxy error for ${req.method} ${req.originalUrl} (${duration}ms):`, 
                  error.code || error.message);
    
    if (error.code === 'ECONNABORTED') {
      res.status(504).json({
        success: false,
        error: 'Backend timeout',
        code: 'BACKEND_TIMEOUT',
        path: req.originalUrl
      });
    } else if (error.response) {
      // Forward error response from backend
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(502).json({
        success: false,
        error: 'Backend service unavailable',
        code: 'BACKEND_ERROR',
        path: req.originalUrl,
        duration: duration
      });
    }
  }
}

// ====================
// ROUTE DEFINITIONS - OPTIMIZED
// ====================

// Public routes (fast path)
app.all('/login', createProxyHandler(false));
app.all('/register', createProxyHandler(false));

// Authentication required routes
app.all('/create-and-join', createProxyHandler(true));
app.all('/join', createProxyHandler(true));

// School routes
app.all('/schools*', createProxyHandler(true));

// Resource routes - using wildcards for all subpaths
app.all('/teachers*', createProxyHandler(true));
app.all('/students*', createProxyHandler(true));
app.all('/classes*', createProxyHandler(true));
app.all('/subjects*', createProxyHandler(true));
app.all('/users*', createProxyHandler(true));
app.all('/dashboard*', createProxyHandler(true));
app.all('/utils*', createProxyHandler(true));

// Dynamic routes (school_id, etc.)
app.all('/:schoolId*', (req, res, next) => {
  // Check if this is a dynamic school route
  if (req.params.schoolId && req.params.schoolId.length > 10) {
    return createProxyHandler(true)(req, res);
  }
  next(); // Pass to 404 if not a valid school ID
});

// ====================
// HEALTH & INFO ENDPOINTS
// ====================
app.get('/health', async (req, res) => {
  const startTime = Date.now();
  
  const healthData = {
    success: true,
    service: 'Echo Gateway - Optimized v1.4',
    status: 'healthy',
    timestamp: new Date().toISOString(),
    performance: {
      websocket: wss.clients.size,
      active_connections: activeConnections.size,
      uptime: process.uptime()
    },
    backend: 'checking',
    gateway_response_time: 0
  };
  
  try {
    // Fast health check with timeout
    const backendResponse = await axios.get(`${PYTHON_BACKEND}/health`, { 
      timeout: 3000 
    });
    healthData.backend = 'connected';
    healthData.backend_details = backendResponse.data;
  } catch (error) {
    healthData.backend = 'disconnected';
    healthData.status = 'degraded';
    healthData.backend_error = error.message;
  }
  
  healthData.gateway_response_time = Date.now() - startTime;
  res.status(200).json(healthData);
});

app.get('/', (req, res) => {
  res.json({
    service: 'Echo Schools Platform Gateway',
    version: '1.4 - Optimized',
    status: 'FIXED & OPTIMIZED - Matches Flask routes',
    performance: 'Connection pooling enabled, 10s timeout',
    endpoints: {
      auth: ['POST /login', 'POST /register'],
      schools: [
        'POST /create-and-join (auth)',
        'POST /join (auth)',
        'GET /schools (auth)',
        'GET /schools/<id> (auth)'
      ],
      management: [
        '/teachers/*',
        '/students/*', 
        '/classes/*',
        '/subjects/*',
        '/users/*',
        '/dashboard/*',
        '/utils/*'
      ],
      monitoring: 'GET /health',
      websocket: 'GET /ws?token=JWT_TOKEN'
    },
    note: 'All routes except /login and /register require Authorization: Bearer <token> header'
  });
});

// ====================
// OPTIMIZED ERROR HANDLER
// ====================
app.use((err, req, res, next) => {
  console.error('🔴 Gateway error:', err.message);
  res.status(500).json({
    success: false,
    error: 'Internal gateway error',
    code: 'GATEWAY_ERROR'
  });
});

// Fast 404 handler
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
  ║  Echo Gateway - OPTIMIZED v1.4        ║
  ╠═══════════════════════════════════════╣
  ║  Status:    OPTIMIZED FOR SPEED       ║
  ║  HTTP:      http://localhost:${PORT}      ║
  ║  Backend:   ${PYTHON_BACKEND}  ║
  ║  WebSocket: ws://localhost:${PORT}/ws     ║
  ║  Timeout:   10 seconds                ║
  ║  Pooling:   Enabled                   ║
  ╚═══════════════════════════════════════╝
  
  ✅ Public routes: /login, /register
  ✅ School creation: /create-and-join (auth)
  ✅ School join: /join (auth)
  ✅ All other routes: /schools, /teachers, etc.
  ✅ Health check: GET /health
  ⚠️  JWT_SECRET: ${JWT_SECRET ? '✓ Set' : '✗ NOT SET'}
  
  📊 Performance optimizations:
  • Connection pooling enabled
  • Keep-alive connections
  • Fast JWT verification
  • Request timeout: 10s
  • Response time logging
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🔄 SIGTERM received. Shutting down gracefully...');
  wss.close();
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});