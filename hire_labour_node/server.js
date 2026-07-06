const express = require('express');
const cors = require('cors');
const path = require('path');
const multer = require('multer');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));
app.use('/uploads', express.static('uploads'));

// Multer Storage Configuration
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        if (file.fieldname === 'id_card') cb(null, 'uploads/ids/');
        else if (file.fieldname === 'selfie') cb(null, 'uploads/selfies/');
        else cb(null, 'uploads/');
    },
    filename: (req, file, cb) => {
        cb(null, Date.now() + path.extname(file.originalname));
    }
});

const upload = multer({ storage: storage });

// Routes
const authRoutes = require('./routes/auth');
const labourRoutes = require('./routes/labour');
const adminRoutes = require('./routes/admin');

app.use('/api/auth', authRoutes);
app.use('/api/labour', labourRoutes);
app.use('/api/admin', adminRoutes);

// Serve landing page at root
app.get('/', (req, res) => {
    res.sendFile('landing.html', { root: 'public' });
});

app.listen(PORT, () => {
    console.log(`🚀 Hire Labour AI running at http://localhost:${PORT}`);
    console.log(`   → Landing page: http://localhost:${PORT}/landing.html`);
    console.log(`   → Register:     http://localhost:${PORT}/index.html`);
});
