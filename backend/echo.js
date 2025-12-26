require('dotenv').config();
const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const jwt = require('jsonwebtoken');
const axios = require('axios');
const cors = require('cors');
const multer = require('multer');
const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');

const app = express();
const server = http.createServer(app);

// ====================
// CONFIGURATION
// ====================
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'echo-secret-key-change-in-production';
const PYTHON_BACKEND = process.env.PYTHON_BACKEND || 'https://echo-backend.up.railway.app';

// External Services Config
const BREVO_API_KEY = process.env.BREVO_API_KEY;
const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_PHONE_NUMBER = process.env.TWILIO_PHONE_NUMBER;

// AWS S3 Config
const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
  },
});
const S3_BUCKET = process.env.S3_BUCKET || 'echo-uploads';

// ====================
// MIDDLEWARE
// ====================
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request Logger
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// Enhanced JWT Authentication Middleware
const authenticate = (req, res, next) => {
  // Skip auth for login/register
  if (req.path === '/auth/login' || req.path === '/auth/register' || 
      req.path === '/users/login' || req.path === '/users/register') {
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
    
    // Additional validation check
    if (!decoded.userId && !decoded.id && !decoded.user_id) {
      return res.status(401).json({
        success: false,
        error: 'Invalid token: missing user identification',
        code: 'INVALID_TOKEN_FORMAT'
      });
    }
    
    // Store user information
    req.user = {
      userId: decoded.userId || decoded.id || decoded.user_id,
      email: decoded.email,
      role: decoded.role
    };
    
    next();
  } catch (error) {
    let errorMessage = 'Invalid token';
    let errorCode = 'INVALID_TOKEN';
    
    if (error.name === 'TokenExpiredError') {
      errorMessage = 'Token has expired';
      errorCode = 'TOKEN_EXPIRED';
    } else if (error.name === 'JsonWebTokenError') {
      errorMessage = 'Malformed token';
      errorCode = 'MALFORMED_TOKEN';
    }
    
    return res.status(401).json({
      success: false,
      error: errorMessage,
      code: errorCode
    });
  }
};

// Error Handler
const errorHandler = (err, req, res, next) => {
  console.error('Error:', err.message);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    code: 'INTERNAL_ERROR',
    details: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
};

// ====================
// WEBSOCKET CHAT SERVER
// ====================
const wss = new WebSocketServer({ server, path: '/ws' });
const activeConnections = new Map(); // userId -> WebSocket

wss.on('connection', (ws, req) => {
  console.log('New WebSocket connection attempt');

  // Authenticate via query token
  const url = new URL(req.url, `http://${req.headers.host}`);
  const token = url.searchParams.get('token');

  if (!token) {
    ws.close(1008, 'Authentication required');
    return;
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const userId = decoded.userId || decoded.id || decoded.user_id;
    
    if (!userId) {
      ws.close(1008, 'Invalid token: no user ID');
      return;
    }

    // Store connection
    activeConnections.set(userId.toString(), ws);
    console.log(`User ${userId} connected to chat`);

    // Send welcome
    ws.send(JSON.stringify({
      type: 'system',
      message: 'Connected to Echo Chat',
      timestamp: new Date().toISOString()
    }));

    // Broadcast online users
    broadcastOnlineUsers();

    // Handle messages
    ws.on('message', async (data) => {
      try {
        const message = JSON.parse(data.toString());
        await handleChatMessage(userId, message);
      } catch (error) {
        ws.send(JSON.stringify({
          type: 'error',
          error: 'Invalid message format'
        }));
      }
    });

    // Handle disconnect
    ws.on('close', () => {
      activeConnections.delete(userId.toString());
      console.log(`User ${userId} disconnected`);
      broadcastOnlineUsers();
    });

  } catch (error) {
    console.log('WebSocket auth failed:', error.message);
    ws.close(1008, 'Invalid token');
  }
});

async function handleChatMessage(senderId, message) {
  const { type, receiverId, content, chatId } = message;
  
  // Save message to database via Ronald's service if needed
  try {
    // TODO: Call Ronald's chat endpoint when available
    // For now, just relay to receiver
    if (type === 'private' && receiverId) {
      const receiverWs = activeConnections.get(receiverId.toString());
      if (receiverWs) {
        receiverWs.send(JSON.stringify({
          type: 'message',
          senderId,
          content,
          timestamp: new Date().toISOString()
        }));
      }
    }
  } catch (error) {
    console.error('Chat message handling error:', error);
  }
}

function broadcastOnlineUsers() {
  const onlineUsers = Array.from(activeConnections.keys());
  const message = JSON.stringify({
    type: 'online_users',
    users: onlineUsers,
    timestamp: new Date().toISOString()
  });
  
  activeConnections.forEach((ws) => {
    ws.send(message);
  });
}

// ====================
// PROXY TO RONALD'S PYTHON BACKEND (without v1 prefix)
// ====================

// Proxy for user routes (login/register don't require auth)
app.all('/users*', async (req, res, next) => {
  // Only authenticate if not login/register
  if (req.path === '/users/login' || req.path === '/users/register') {
    return next();
  }
  
  // For other user routes, check authentication
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
    req.user = {
      userId: decoded.userId || decoded.id || decoded.user_id
    };
  } catch (error) {
    return res.status(401).json({
      success: false,
      error: 'Invalid token',
      code: 'INVALID_TOKEN'
    });
  }
  
  const targetURL = `${PYTHON_BACKEND}${req.path}`;
  
  console.log(`Proxying to Python: ${targetURL}`);
  
  try {
    const response = await axios({
      method: req.method,
      url: targetURL,
      headers: {
        ...req.headers,
        'x-forwarded-by': 'echo-gateway',
        host: new URL(PYTHON_BACKEND).host
      },
      data: req.body,
      params: req.query,
      validateStatus: () => true
    });
    
    res.status(response.status).json(response.data);
  } catch (error) {
    console.error('Proxy error:', error.message);
    res.status(502).json({
      success: false,
      error: 'Python service unavailable',
      code: 'SERVICE_UNAVAILABLE'
    });
  }
});

// Proxy for school routes (requires auth)
app.all('/api/schools*', authenticate, async (req, res) => {
  const targetURL = `${PYTHON_BACKEND}${req.path}`;
  
  console.log(`Proxying to Python: ${targetURL}`);
  
  try {
    const response = await axios({
      method: req.method,
      url: targetURL,
      headers: {
        ...req.headers,
        'x-forwarded-by': 'echo-gateway',
        'x-user-id': req.user.userId,
        host: new URL(PYTHON_BACKEND).host
      },
      data: req.body,
      params: req.query,
      validateStatus: () => true
    });
    
    res.status(response.status).json(response.data);
  } catch (error) {
    console.error('Proxy error:', error.message);
    res.status(502).json({
      success: false,
      error: 'Python service unavailable',
      code: 'SERVICE_UNAVAILABLE'
    });
  }
});

// Proxy for future endpoints: grades, results, payments
app.all('/grades*', authenticate, async (req, res) => {
  const targetURL = `${PYTHON_BACKEND}${req.path}`;
  
  console.log(`Proxying to Python: ${targetURL}`);
  
  try {
    const response = await axios({
      method: req.method,
      url: targetURL,
      headers: {
        ...req.headers,
        'x-forwarded-by': 'echo-gateway',
        'x-user-id': req.user.userId,
        host: new URL(PYTHON_BACKEND).host
      },
      data: req.body,
      params: req.query,
      validateStatus: () => true
    });
    
    res.status(response.status).json(response.data);
  } catch (error) {
    console.error('Proxy error:', error.message);
    res.status(502).json({
      success: false,
      error: 'Grades service unavailable',
      code: 'SERVICE_UNAVAILABLE'
    });
  }
});

app.all('/results*', authenticate, async (req, res) => {
  const targetURL = `${PYTHON_BACKEND}${req.path}`;
  
  console.log(`Proxying to Python: ${targetURL}`);
  
  try {
    const response = await axios({
      method: req.method,
      url: targetURL,
      headers: {
        ...req.headers,
        'x-forwarded-by': 'echo-gateway',
        'x-user-id': req.user.userId,
        host: new URL(PYTHON_BACKEND).host
      },
      data: req.body,
      params: req.query,
      validateStatus: () => true
    });
    
    res.status(response.status).json(response.data);
  } catch (error) {
    console.error('Proxy error:', error.message);
    res.status(502).json({
      success: false,
      error: 'Results service unavailable',
      code: 'SERVICE_UNAVAILABLE'
    });
  }
});

app.all('/payments*', authenticate, async (req, res) => {
  const targetURL = `${PYTHON_BACKEND}${req.path}`;
  
  console.log(`Proxying to Python: ${targetURL}`);
  
  try {
    const response = await axios({
      method: req.method,
      url: targetURL,
      headers: {
        ...req.headers,
        'x-forwarded-by': 'echo-gateway',
        'x-user-id': req.user.userId,
        host: new URL(PYTHON_BACKEND).host
      },
      data: req.body,
      params: req.query,
      validateStatus: () => true
    });
    
    res.status(response.status).json(response.data);
  } catch (error) {
    console.error('Proxy error:', error.message);
    res.status(502).json({
      success: false,
      error: 'Payments service unavailable',
      code: 'SERVICE_UNAVAILABLE'
    });
  }
});

// ====================
// EXTERNAL SERVICES (without v1 prefix)
// ====================

// Email via Brevo (from original file)
app.post('/email/send', authenticate, async (req, res) => {
  const { to, subject, htmlContent } = req.body;
  
  if (!BREVO_API_KEY) {
    return res.status(501).json({
      success: false,
      error: 'Email service not configured',
      code: 'EMAIL_SERVICE_DISABLED'
    });
  }
  
  try {
    const response = await axios.post(
      'https://api.brevo.com/v3/smtp/email',
      {
        sender: { email: process.env.FROM_EMAIL || 'noreply@echo.example.com' },
        to: [{ email: to }],
        subject,
        htmlContent
      },
      {
        headers: {
          'api-key': BREVO_API_KEY,
          'Content-Type': 'application/json'
        }
      }
    );
    
    res.json({
      success: true,
      messageId: response.data.messageId,
      message: 'Email sent successfully'
    });
  } catch (error) {
    console.error('Brevo error:', error.response?.data || error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to send email',
      code: 'EMAIL_SEND_FAILED'
    });
  }
});

// SMS via Twilio (from original file)
app.post('/sms/send', authenticate, async (req, res) => {
  const { to, message } = req.body;
  
  if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN) {
    return res.status(501).json({
      success: false,
      error: 'SMS service not configured',
      code: 'SMS_SERVICE_DISABLED'
    });
  }
  
  try {
    const response = await axios.post(
      `https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Messages.json`,
      new URLSearchParams({
        To: to,
        From: TWILIO_PHONE_NUMBER,
        Body: message
      }),
      {
        auth: {
          username: TWILIO_ACCOUNT_SID,
          password: TWILIO_AUTH_TOKEN
        },
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );
    
    res.json({
      success: true,
      sid: response.data.sid,
      message: 'SMS sent successfully'
    });
  } catch (error) {
    console.error('Twilio error:', error.response?.data || error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to send SMS',
      code: 'SMS_SEND_FAILED'
    });
  }
});

// File Upload to S3 (from original file)
const upload = multer({ storage: multer.memoryStorage() });
app.post('/upload', authenticate, upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      error: 'No file uploaded',
      code: 'NO_FILE'
    });
  }
  
  const file = req.file;
  const fileName = `${Date.now()}-${file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_')}`;
  
  try {
    const command = new PutObjectCommand({
      Bucket: S3_BUCKET,
      Key: `uploads/${fileName}`,
      Body: file.buffer,
      ContentType: file.mimetype,
      Metadata: {
        uploadedBy: req.user.userId || 'unknown',
        originalName: file.originalname
      }
    });
    
    await s3Client.send(command);
    
    const fileUrl = `https://${S3_BUCKET}.s3.amazonaws.com/uploads/${fileName}`;
    
    res.json({
      success: true,
      fileName,
      fileUrl,
      size: file.size,
      type: file.mimetype,
      message: 'File uploaded successfully'
    });
  } catch (error) {
    console.error('S3 upload error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to upload file',
      code: 'UPLOAD_FAILED'
    });
  }
});

// ====================
// AUTH ENDPOINTS (without v1 prefix) - from your endpoints list
// ====================
app.post('/auth/register', async (req, res) => {
  try {
    const response = await axios.post(
      `${PYTHON_BACKEND}/users/register`,
      req.body
    );
    res.status(response.status).json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json(error.response?.data || {
      error: 'Registration failed'
    });
  }
});

app.post('/auth/login', async (req, res) => {
  try {
    const response = await axios.post(
      `${PYTHON_BACKEND}/users/login`,
      req.body
    );
    res.status(response.status).json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json(error.response?.data || {
      error: 'Login failed'
    });
  }
});

// ====================
// HEALTH CHECK & INFO (from original file)
// ====================
app.get('/health', (req, res) => {
  res.json({
    success: true,
    service: 'Echo API Gateway',
    status: 'running',
    timestamp: new Date().toISOString(),
    python_backend: PYTHON_BACKEND,
    features: ['proxy', 'websocket-chat', 'email', 'sms', 'file-upload']
  });
});

app.get('/', (req, res) => {
  res.json({
    message: 'Echo API Gateway v1.0',
    endpoints: {
      auth: {
        register: 'POST /auth/register',
        login: 'POST /auth/login'
      },
      users: 'ALL /users/* -> Python backend',
      schools: 'ALL /api/schools/* -> Python backend',
      grades: 'ALL /grades/* -> Python backend',
      results: 'ALL /results/* -> Python backend',
      payments: 'ALL /payments/* -> Python backend',
      external: {
        email: 'POST /email/send',
        sms: 'POST /sms/send',
        upload: 'POST /upload'
      },
      chat: 'WebSocket: /ws?token=JWT',
      health: 'GET /health'
    }
  });
});

// Apply error handler
app.use(errorHandler);

// ====================
// START SERVER
// ====================
server.listen(PORT, () => {
  console.log(`
  ╔═══════════════════════════════════════╗
  ║       Echo API Gateway Started        ║
  ╠═══════════════════════════════════════╣
  ║  HTTP Server: http://localhost:${PORT}   ║
  ║  WebSocket:   ws://localhost:${PORT}/ws  ║
  ║  Python Backend: ${PYTHON_BACKEND} ║
  ╚═══════════════════════════════════════╝
  `);
});