/* ═══════════════════════════════════════════════
   Registration Page JS — Hire Labour AI
═══════════════════════════════════════════════ */

let currentStep = 1;
let isPhoneVerified = false;
let registeredLabourId = null;

// ── Step Progress ────────────────────────────
function setProgress(step) {
    for (let i = 1; i <= 4; i++) {
        const ps = document.getElementById(`ps${i}`);
        if (!ps) continue;
        ps.classList.remove('active', 'done');
        if (i < step) ps.classList.add('done');
        else if (i === step) ps.classList.add('active');
    }
}

function nextStep(step) {
    if (step === 2 && !isPhoneVerified) {
        showToast('⚠️ Please verify your phone number first!', 'warn');
        return;
    }
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(`step${step}`);
    if (target) target.classList.add('active');
    currentStep = step;
    setProgress(step);
}

// ── Toast ────────────────────────────────────
function showToast(msg, type = 'info') {
    const existing = document.getElementById('toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.id = 'toast';
    const colors = { info: '#6366f1', warn: '#f59e0b', error: '#ef4444', success: '#22c55e' };
    toast.style.cssText = `
        position:fixed;top:20px;right:20px;z-index:9999;
        padding:12px 20px;border-radius:12px;
        background:${colors[type] || colors.info};
        color:#fff;font-size:0.875rem;font-weight:600;
        box-shadow:0 10px 30px rgba(0,0,0,0.4);
        animation:fadeIn 0.3s ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── OTP Flow ─────────────────────────────────
async function sendOTP() {
    const phone = document.getElementById('phoneInput').value.trim();
    if (!phone || phone.length < 10) { showToast('Enter a valid 10-digit phone number', 'warn'); return; }
    const btn = document.getElementById('sendOtpBtn');
    btn.disabled = true; btn.textContent = 'Sending...';
    try {
        const res = await fetch('/api/auth/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone })
        });
        const data = await res.json();
        if (data.otp) {
            showToast(`Dev Mode — OTP: ${data.otp}`, 'info');
            document.getElementById('otpGroup').style.display = 'block';
        } else {
            showToast('Failed to send OTP', 'error');
        }
    } catch (e) {
        showToast('Network error sending OTP', 'error');
    }
    btn.disabled = false; btn.textContent = 'Resend OTP';
}

async function verifyOTP() {
    const phone = document.getElementById('phoneInput').value.trim();
    const otp   = document.getElementById('otpInput').value.trim();
    const btn   = document.getElementById('verifyOtpBtn');
    btn.disabled = true; btn.textContent = 'Verifying...';
    try {
        const res = await fetch('/api/auth/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, otp })
        });
        const data = await res.json();
        if (data.success) {
            isPhoneVerified = true;
            document.getElementById('otpGroup').innerHTML = `
                <div style="display:flex;align-items:center;gap:8px;color:#4ade80;font-weight:600;">
                    <span style="font-size:1.2rem;">✅</span> Phone verified successfully!
                </div>`;
            document.getElementById('nextBtn1').style.display = 'block';
            showToast('Phone verified!', 'success');
        } else {
            showToast('Invalid OTP — please try again', 'error');
            btn.disabled = false; btn.textContent = 'Verify OTP';
        }
    } catch (e) {
        showToast('Network error', 'error');
        btn.disabled = false; btn.textContent = 'Verify OTP';
    }
}

// ── AI Loading Steps Animation ───────────────
const LOADING_STEPS = [
    { id: 'als1', text: '⚡ Submitting registration data...',      delay: 0    },
    { id: 'als2', text: '👁️ Running liveness detection on selfie...', delay: 1200 },
    { id: 'als3', text: '🛡️ Anti-spoofing analysis...',            delay: 2400 },
    { id: 'als4', text: '🧠 Validating profile and skills...',     delay: 3600 },
    { id: 'als5', text: '📊 Calculating AI trust score...',        delay: 5000 },
];

function animateLoadingSteps() {
    LOADING_STEPS.forEach((s, idx) => {
        setTimeout(() => {
            if (idx > 0) {
                const prev = document.getElementById(LOADING_STEPS[idx - 1].id);
                if (prev) { prev.classList.remove('active'); prev.classList.add('done'); prev.textContent = '✅ ' + prev.textContent.replace(/^[^\s]+\s/, ''); }
            }
            const cur = document.getElementById(s.id);
            if (cur) { cur.classList.add('active'); cur.textContent = s.text; }
        }, s.delay);
    });
}

// ── Poll verification status ─────────────────
async function pollVerificationStatus(labourId) {
    const MAX_POLLS = 20;
    let polls = 0;
    return new Promise((resolve) => {
        const interval = setInterval(async () => {
            polls++;
            try {
                const res = await fetch(`/api/labour/status/${labourId}`);
                const data = await res.json();
                if (data.status && data.status !== 'Pending') {
                    clearInterval(interval);
                    resolve(data);
                } else if (polls >= MAX_POLLS) {
                    clearInterval(interval);
                    resolve(data); // Return whatever we have after timeout
                }
            } catch (e) {
                if (polls >= MAX_POLLS) { clearInterval(interval); resolve(null); }
            }
        }, 2000);
    });
}

// ── Render AI Result ─────────────────────────
function renderAIResult(statusData, geminiResult) {
    const isAllow = statusData.status === 'Verified' ||
                    (geminiResult && geminiResult.final_action === 'ALLOW_REGISTRATION');

    // Verdict panel
    const verdict  = document.getElementById('resultVerdict');
    const emoji    = document.getElementById('verdictEmoji');
    const action   = document.getElementById('verdictAction');
    const desc     = document.getElementById('verdictDesc');
    verdict.className = `result-verdict ${isAllow ? 'allow' : 'reject'}`;
    emoji.textContent  = isAllow ? '✅' : '❌';
    action.className   = `verdict-action ${isAllow ? 'allow' : 'reject'}`;
    action.textContent = isAllow ? 'ALLOW_REGISTRATION' : 'REJECT_REGISTRATION';
    desc.textContent   = isAllow
        ? 'Your identity and profile have been approved. You are now visible to employers.'
        : 'Your registration was flagged. Please ensure your selfie is a real live photo and your profile is genuine.';

    // Metrics
    const auth = geminiResult?.authentication || {};
    const val  = geminiResult?.validation     || {};

    const faceOk = auth.face_verified !== false;
    document.getElementById('resFaceVerified').textContent  = faceOk ? '✓ YES' : '✗ NO';
    document.getElementById('resFaceVerified').className    = `result-box-val ${faceOk ? 'green' : 'red'}`;

    const liveOk = auth.liveness_detected !== false;
    document.getElementById('resLiveness').textContent      = liveOk ? '✓ LIVE' : '✗ SPOOF';
    document.getElementById('resLiveness').className        = `result-box-val ${liveOk ? 'green' : 'red'}`;

    const faceScore = auth.confidence_score != null ? `${(auth.confidence_score * 100).toFixed(0)}%` : 'N/A';
    document.getElementById('resFaceScore').textContent     = faceScore;

    const profScore = val.data_quality_score != null ? `${(val.data_quality_score * 100).toFixed(0)}%` : 'N/A';
    document.getElementById('resProfileScore').textContent  = profScore;

    document.getElementById('resAuthNotesText').textContent = auth.anti_spoofing_notes || statusData.ai_auth_notes || 'No notes available.';
    document.getElementById('resValNotesText').textContent  = val.validation_notes     || statusData.ai_val_notes  || 'No notes available.';

    // Action buttons
    const actions = document.getElementById('resultActions');
    if (isAllow) {
        actions.innerHTML = `
            <a href="profile.html?id=${registeredLabourId}" class="btn-primary" style="display:block;text-align:center;padding:13px;">
                🎉 View My Profile
            </a>`;
    } else {
        actions.innerHTML = `
            <button onclick="retryRegistration()" class="btn-primary">↩ Try Again</button>`;
    }
}

function retryRegistration() {
    document.getElementById('aiResultPanel').style.display = 'none';
    document.getElementById('registrationForm').style.display = 'block';
    document.getElementById('progressSteps').style.display = 'flex';
    nextStep(1);
    isPhoneVerified = false;
    registeredLabourId = null;
}

// ── Form Submit ──────────────────────────────
document.getElementById('registrationForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Show AI panel
    const form  = document.getElementById('registrationForm');
    const panel = document.getElementById('aiResultPanel');
    const ps    = document.getElementById('progressSteps');
    form.style.display = 'none';
    panel.style.display = 'block';
    document.getElementById('aiLoading').style.display = 'block';
    document.getElementById('aiResultContent').style.display = 'none';
    ps.style.display = 'none';
    animateLoadingSteps();

    const formData = new FormData(e.target);
    let labourId   = null;
    let geminiData = null;

    try {
        // Step 1: Submit registration
        const regRes  = await fetch('/api/labour/register', { method: 'POST', body: formData });
        const regData = await regRes.json();

        if (!regData.success) throw new Error(regData.error || 'Registration failed');
        labourId = regData.labourerId;
        registeredLabourId = labourId;

        // Step 2: Poll for AI verification result (runs async on server)
        const statusData = await pollVerificationStatus(labourId);

        // Show result
        document.getElementById('aiLoading').style.display = 'none';
        document.getElementById('aiResultContent').style.display = 'block';
        renderAIResult(statusData || { status: 'Pending' }, geminiData);
        setProgress(4);

    } catch (err) {
        document.getElementById('aiLoading').style.display = 'none';
        document.getElementById('aiResultContent').style.display = 'block';
        renderAIResult({ status: 'Fake', ai_auth_notes: err.message }, null);
    }
});
