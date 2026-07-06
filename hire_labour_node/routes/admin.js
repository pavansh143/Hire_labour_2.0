const express = require('express');
const router = express.Router();
const db = require('../db');

// Get all labourers for admin (including flagged)
router.get('/labourers', async (req, res) => {
    try {
        const [rows] = await db.query('SELECT * FROM labourers ORDER BY created_at DESC');
        res.json(rows);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Update status (Approve/Reject/Ban)
router.post('/update-status', async (req, res) => {
    const { id, status, is_banned } = req.body;
    try {
        await db.query('UPDATE labourers SET status = ?, is_banned = ? WHERE id = ?', [status, is_banned, id]);
        res.json({ success: true, message: 'Status updated' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;
