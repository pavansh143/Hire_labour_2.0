const db = require('../db');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const { analyzeText } = require('../utils/openai');

// ═══════════════════════════════════════════════════════════════════
// REGISTER LABOURER
// ═══════════════════════════════════════════════════════════════════
exports.registerLabourer = async (req, res) => {
    const { full_name, phone, location, skills, bio, aadhaar_number, experience } = req.body;
    const id_card_image = req.files['id_card'] ? req.files['id_card'][0].path : null;
    const selfie_image  = req.files['selfie']  ? req.files['selfie'][0].path  : null;

    try {
        const [result] = await db.query(
            `INSERT INTO labourers 
             (full_name, phone, location, skills, bio, aadhaar_number, id_card_image, selfie_image)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
            [full_name, phone, location, skills, bio, aadhaar_number, id_card_image, selfie_image]
        );

        const labourerId = result.insertId;

        // Trigger AI Verification asynchronously (non-blocking)
        triggerVerification(labourerId, id_card_image, selfie_image, aadhaar_number, bio, full_name, skills, experience);

        res.json({
            success: true,
            message: 'Registration successful. AI Verification in progress.',
            labourerId
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

// ═══════════════════════════════════════════════════════════════════
// VERIFICATION ENGINE (runs in background after registration)
// ═══════════════════════════════════════════════════════════════════
async function triggerVerification(id, idPath, selfiePath, inputAadhaar, bio, full_name, skills, experience) {
    try {
        let geminiResult = null;
        let geminiTrustScore = 50; // default if Gemini offline
        let geminiStatus = 'Pending';
        let aiAuthNotes = '';
        let aiValidationNotes = '';

        // ── STEP 1: Gemini Vision + Text Validation ──────────────────
        if (selfiePath && fs.existsSync(selfiePath)) {
            try {
                const form = new FormData();
                form.append('selfie', fs.createReadStream(selfiePath));
                form.append('full_name',  full_name  || '');
                form.append('bio',        bio        || '');
                form.append('skills',     skills     || '');
                form.append('experience', experience || '');

                const geminiResp = await axios.post(
                    `${process.env.AI_SERVICE_URL}/validate-registration`,
                    form,
                    { headers: form.getHeaders(), timeout: 30000 }
                );

                geminiResult = geminiResp.data;

                const auth       = geminiResult.authentication || {};
                const validation = geminiResult.validation     || {};

                // Convert 0-1 scores to 0-100
                const faceScore    = (auth.confidence_score    || 0) * 100;
                const profileScore = (validation.data_quality_score || 0) * 100;
                geminiTrustScore   = Math.round((faceScore + profileScore) / 2);

                aiAuthNotes       = auth.anti_spoofing_notes || '';
                aiValidationNotes = validation.validation_notes || '';

                if (geminiResult.final_action === 'REJECT_REGISTRATION') {
                    geminiStatus = 'Fake';
                } else if (geminiTrustScore >= 75) {
                    geminiStatus = 'Verified';
                } else if (geminiTrustScore >= 40) {
                    geminiStatus = 'Suspicious';
                } else {
                    geminiStatus = 'Fake';
                }

                console.log(`[Gemini] Labour ${id} → ${geminiResult.final_action} | Trust: ${geminiTrustScore}`);
            } catch (geminiErr) {
                console.warn(`[Gemini] Offline or error for labour ${id}: ${geminiErr.message}`);
                aiAuthNotes = 'Gemini AI service was unavailable during verification.';
            }
        } else {
            aiAuthNotes = 'No selfie uploaded; face verification skipped.';
        }

        // ── STEP 2: Legacy OpenAI Bio Analysis (penalty check) ───────
        let bioPenalty = 0;
        try {
            const bioAnalysis = await analyzeText(bio || '', 'bio');
            bioPenalty = bioAnalysis.is_suspicious ? 15 : 0;
        } catch (e) {
            console.warn('[OpenAI Bio] Skipped:', e.message);
        }

        let finalScore = Math.max(0, geminiTrustScore - bioPenalty);

        // ── STEP 3: Legacy OCR + Face matching (optional boost) ───────
        let extractedAadhaar = null;
        let faceEncoding     = '';

        try {
            const legacyResp = await axios.post(
                `${process.env.AI_SERVICE_URL}/verify`,
                {
                    id_card_path:  idPath,
                    selfie_path:   selfiePath,
                    input_aadhaar: inputAadhaar
                },
                { timeout: 15000 }
            );

            const { ocr_match, face_match, trust_score: legacy_score, extracted_aadhaar, face_encoding } = legacyResp.data;
            extractedAadhaar = extracted_aadhaar;
            faceEncoding     = face_encoding || '';

            // Legacy score is a bonus, not the primary verdict
            if (ocr_match)  finalScore = Math.min(100, finalScore + 10);
            if (face_match) finalScore = Math.min(100, finalScore + 10);
        } catch (e) {
            console.warn('[Legacy AI] /verify offline, skipping OCR/face boost.');
        }

        // ── STEP 4: Duplicate Detection ───────────────────────────────
        if (faceEncoding) {
            try {
                const [existing] = await db.query(
                    'SELECT id, face_encoding AS encoding FROM labourers WHERE id != ?', [id]
                );
                const dupResp = await axios.post(
                    `${process.env.AI_SERVICE_URL}/check-duplicate`,
                    { new_encoding: faceEncoding, existing_encodings: existing },
                    { timeout: 10000 }
                );
                if (dupResp.data.is_duplicate) {
                    finalScore  = 0;
                    geminiStatus = 'Fake';
                    aiAuthNotes += ' Duplicate face detected in system.';
                }
            } catch (e) {
                console.warn('[Duplicate Check] Skipped:', e.message);
            }
        }

        // ── STEP 5: Write results to DB ───────────────────────────────
        await db.query(
            `UPDATE labourers 
             SET trust_score = ?, status = ?,
                 aadhaar_number = COALESCE(?, aadhaar_number),
                 face_encoding  = ?,
                 ai_auth_notes  = ?,
                 ai_val_notes   = ?
             WHERE id = ?`,
            [finalScore, geminiStatus, extractedAadhaar, faceEncoding, aiAuthNotes, aiValidationNotes, id]
        );

        console.log(`[Verification Complete] Labour ${id} → Status: ${geminiStatus}, Score: ${finalScore}`);

    } catch (err) {
        console.error(`[Verification Error] Labour ${id}:`, err.message);
    }
}

// ═══════════════════════════════════════════════════════════════════
// GET SINGLE PROFILE
// ═══════════════════════════════════════════════════════════════════
exports.getLabourerProfile = async (req, res) => {
    const { id } = req.params;
    try {
        const [rows] = await db.query('SELECT * FROM labourers WHERE id = ?', [id]);
        if (rows.length > 0) res.json(rows[0]);
        else res.status(404).json({ message: 'Labourer not found' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

// ═══════════════════════════════════════════════════════════════════
// GET ALL LABOURERS (for search page)
// ═══════════════════════════════════════════════════════════════════
exports.getAllLabourers = async (req, res) => {
    try {
        const [rows] = await db.query(
            'SELECT * FROM labourers WHERE is_banned = FALSE ORDER BY trust_score DESC'
        );
        res.json(rows);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

// ═══════════════════════════════════════════════════════════════════
// GET VERIFICATION STATUS (for frontend polling)
// ═══════════════════════════════════════════════════════════════════
exports.getVerificationStatus = async (req, res) => {
    const { id } = req.params;
    try {
        const [rows] = await db.query(
            'SELECT id, status, trust_score, ai_auth_notes, ai_val_notes FROM labourers WHERE id = ?',
            [id]
        );
        if (rows.length > 0) res.json(rows[0]);
        else res.status(404).json({ message: 'Not found' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};
