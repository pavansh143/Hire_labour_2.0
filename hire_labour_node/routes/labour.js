const express = require('express');
const router = express.Router();
const labourController = require('../controllers/labourController');
const multer = require('multer');
const path = require('path');
const fs = require('fs');

// Ensure upload directories exist
['uploads', 'uploads/ids', 'uploads/selfies'].forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        if (file.fieldname === 'id_card')  cb(null, 'uploads/ids/');
        else if (file.fieldname === 'selfie') cb(null, 'uploads/selfies/');
        else cb(null, 'uploads/');
    },
    filename: (req, file, cb) => {
        cb(null, Date.now() + path.extname(file.originalname));
    }
});
const upload = multer({ storage });

router.post('/register',
    upload.fields([{ name: 'id_card', maxCount: 1 }, { name: 'selfie', maxCount: 1 }]),
    labourController.registerLabourer
);
router.get('/profile/:id',          labourController.getLabourerProfile);
router.get('/status/:id',           labourController.getVerificationStatus);
router.get('/all',                  labourController.getAllLabourers);

module.exports = router;
