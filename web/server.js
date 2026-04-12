const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const DB_PATH = path.join(__dirname, 'db.json');

const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml'
};

// --- Helper Database Functions ---
const readDB = () => {
    try {
        const data = fs.readFileSync(DB_PATH, 'utf8');
        return JSON.parse(data);
    } catch (e) {
        return { inventory: [], orders: [], sales: 0 };
    }
};

const writeDB = (data) => {
    fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2));
};

// --- API Router ---
const handleAPI = (req, res) => {
    const { method, url } = req;
    
    // --- CORS Headers for External Requests ---
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, ngrok-skip-browser-warning');

    if (method === 'OPTIONS') {
        res.writeHead(204);
        return res.end();
    }
    // ------------------------------------------

    // API: Get Inventory
    if (method === 'GET' && url === '/api/inventory') {
        const db = readDB();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(db.inventory));
    }

    // API: Update Inventory (Add stock)
    if (method === 'POST' && url === '/api/inventory/update') {
        let body = '';
        req.on('data', chunk => body += chunk.toString());
        req.on('end', () => {
            const { id, amount } = JSON.parse(body);
            const db = readDB();
            const item = db.inventory.find(i => i.id === id);
            if (item) {
                item.stock = parseFloat((item.stock + amount).toFixed(2));
                item.status = item.stock < item.min ? (item.stock < item.min / 2 ? 'CRITICO' : 'BAJO') : 'OK';
                writeDB(db);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, item }));
            } else {
                res.writeHead(404);
                res.end(JSON.stringify({ error: 'Item not found' }));
            }
        });
        return;
    }

    // API: Get Orders (for KDS)
    if (method === 'GET' && url === '/api/orders') {
        const db = readDB();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(db.orders));
    }

    // API: Create Order (from POS or WhatsApp)
    if (method === 'POST' && url === '/api/orders') {
        let body = '';
        req.on('data', chunk => body += chunk.toString());
        req.on('end', () => {
            const order = JSON.parse(body);
            const db = readDB();
            
            // Basic logic: reduce stock (example: every combo reduces 0.2kg of meat)
            db.inventory.forEach(item => {
                if (item.name === 'Carne molida') item.stock -= 0.2;
                if (item.name === 'Pan de hamburguesa') item.stock -= 1;
                item.status = item.stock < item.min ? (item.stock < item.min / 2 ? 'CRITICO' : 'BAJO') : 'OK';
            });

            const newOrder = {
                ...order,
                id: 'ORD-' + Date.now().toString().slice(-4),
                time: 0,
                status: 'RECIBIDO',
                createdAt: new Date().toISOString()
            };
            
            db.orders.push(newOrder);
            db.sales += order.total;
            writeDB(db);

            res.writeHead(201, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(newOrder));
        });
        return;
    }

    // API: Complete/Start Order
    if (method === 'POST' && url.startsWith('/api/orders/status')) {
        let body = '';
        req.on('data', chunk => body += chunk.toString());
        req.on('end', () => {
            const { id, status } = JSON.parse(body);
            const db = readDB();
            const order = db.orders.find(o => o.id === id);
            if (order) {
                if (status === 'COMPLETADO') {
                    db.orders = db.orders.filter(o => o.id !== id);
                } else {
                    order.status = status;
                }
                writeDB(db);
                res.writeHead(200);
                res.end(JSON.stringify({ success: true }));
            }
        });
        return;
    }

    // 404 API
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not Found' }));
};

// --- Static File Server ---
const server = http.createServer((req, res) => {
    // Check if it's an API call
    if (req.url.startsWith('/api')) {
        return handleAPI(req, res);
    }

    // Default static file serving
    let filePath = req.url === '/' ? './index.html' : '.' + req.url;
    filePath = path.normalize(filePath).replace(/^(\.\.[/\\])+/, '');
    
    const extname = String(path.extname(filePath)).toLowerCase();
    const contentType = MIME_TYPES[extname] || 'application/octet-stream';

    fs.readFile(filePath, (error, content) => {
        if (error) {
            if (error.code === 'ENOENT') {
                res.writeHead(404);
                res.end('File Not Found');
            } else {
                res.writeHead(500);
                res.end(`Server Error: ${error.code}`);
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

const os = require('os');
const networkInterfaces = os.networkInterfaces();
let localIP = '127.0.0.1';

Object.keys(networkInterfaces).forEach((ifname) => {
    networkInterfaces[ifname].forEach((iface) => {
        if (iface.family === 'IPv4' && !iface.internal) {
            localIP = iface.address;
        }
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log('--------------------------------------------------');
    console.log(`🚀 SERVIDOR RESTAURANTE MULTI-DISPOSITIVO ACTIVO`);
    console.log(`🏠 Local: http://localhost:${PORT}`);
    console.log(`🌐 En Red: http://${localIP}:${PORT}`);
    console.log('--------------------------------------------------');
    console.log(`📦 Base de datos JSON (db.json) conectada.`);
    console.log('Presiona Ctrl+C para detener el servidor');
});
