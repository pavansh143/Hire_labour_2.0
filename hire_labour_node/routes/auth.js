const express = require('express');
const router = express.Router();
const db = require('../db');

// Mock OTP Generation
router.post('/send-otp', async (req, res) => {
    const { phone } = req.body;
    const otp = Math.floor(100000 + Math.random() * 900000).toString();
    
    try {
        await db.query('INSERT INTO otp_verifications (phone, code) VALUES (?, ?)', [phone, otp]);
        res.json({ message: 'OTP sent successfully', otp }); // Returning OTP for development convenience
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Verify OTP
router.post('/verify-otp', async (req, res) => {
    const { phone, otp } = req.body;
    
    try {
        const [rows] = await db.query('SELECT * FROM otp_verifications WHERE phone = ? AND code = ? ORDER BY created_at DESC LIMIT 1', [phone, otp]);
        if (rows.length > 0) {
            res.json({ success: true, message: 'Phone verified' });
        } else {
            res.status(400).json({ success: false, message: 'Invalid OTP' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;
