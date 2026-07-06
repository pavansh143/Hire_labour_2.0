/* ═══════════════════════════════════════════════
   Landing Page JavaScript — Hire Labour AI
═══════════════════════════════════════════════ */

// ── Navbar scroll effect ─────────────────────
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 40);
});

// ── Mobile menu ──────────────────────────────
function toggleMenu() {
    const links = document.getElementById('navLinks');
    links.style.display = links.style.display === 'flex' ? 'none' : 'flex';
    links.style.flexDirection = 'column';
    links.style.position = 'absolute';
    links.style.top = '70px';
    links.style.left = '0'; links.style.right = '0';
    links.style.background = 'rgba(5,8,22,0.97)';
    links.style.padding = '20px 24px';
    links.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
}

// ── Particle generator ───────────────────────
function createParticles() {
    const container = document.getElementById('particles');
    if (!container) return;
    for (let i = 0; i < 18; i++) {
        const p = document.createElement('div');
        p.classList.add('particle');
        const size = Math.random() * 180 + 60;
        p.style.cssText = `
            width: ${size}px; height: ${size}px;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation-duration: ${Math.random() * 20 + 15}s;
            animation-delay: -${Math.random() * 20}s;
            opacity: ${Math.random() * 0.25 + 0.05};
        `;
        container.appendChild(p);
    }
}
createParticles();

// ── Scroll reveal ────────────────────────────
const revealEls = document.querySelectorAll(
    '.step-card, .feature-card, .stat-card, .skill-tile, .demo-card, .demo-verdict, .demo-json'
);
revealEls.forEach(el => el.classList.add('reveal'));

const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
            setTimeout(() => entry.target.classList.add('visible'), i * 60);
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

revealEls.forEach(el => observer.observe(el));

// ── Counter animation ─────────────────────────
function animateCounter(el, target, suffix) {
    let start = 0;
    const duration = 1800;
    const step = (timestamp) => {
        if (!start) start = timestamp;
        const progress = Math.min((timestamp - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * target);
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target;
    };
    requestAnimationFrame(step);
}

const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const el = entry.target.querySelector('.stat-number');
            const target = parseInt(el.dataset.target);
            animateCounter(el, target);
            statsObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

document.querySelectorAll('.stat-card').forEach(c => statsObserver.observe(c));

// ── Skill tile hover effect ──────────────────
document.querySelectorAll('.skill-tile').forEach(tile => {
    tile.addEventListener('click', () => {
        window.location.href = `search.html?skill=${encodeURIComponent(tile.querySelector('span:last-child').textContent)}`;
    });
});

// ── AI demo step cycle animation ─────────────
const demoSteps = [
    'Uploading selfie for Gemini Vision...',
    'Running liveness detection...',
    'Checking for spoofing artifacts...',
    'Analyzing profile text...',
    'Detecting spam / gibberish...',
    'Calculating confidence scores...',
    'Generating final verdict...'
];
let demoIdx = 0;
const demoActiveStep = document.querySelector('.ai-step.active');
if (demoActiveStep) {
    setInterval(() => {
        demoIdx = (demoIdx + 1) % demoSteps.length;
        demoActiveStep.textContent = '⚡ ' + demoSteps[demoIdx];
    }, 2200);
}

// ── Smooth scroll for nav links ──────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
        const target = document.querySelector(a.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});
