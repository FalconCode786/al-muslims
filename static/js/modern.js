// ============================================
// ALMUSLIM MODERN UI INTERACTIONS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initSplashScreen();
    initMobileMenu();
    initNavbarScroll();
    initScrollReveal();
    initTiltCards();
    initCounters();
    initRippleEffect();
    initSmoothScroll();
});

// Splash Screen
function initSplashScreen() {
    const splash = document.getElementById('splash-screen');
    if (!splash) return;
    
    setTimeout(() => {
        splash.classList.add('hide');
        setTimeout(() => splash.remove(), 700);
    }, 2000);
}

// Mobile Menu
function initMobileMenu() {
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');
    
    if (!btn || !menu) return;
    
    btn.addEventListener('click', () => {
        const isHidden = menu.classList.contains('hidden');
        menu.classList.toggle('hidden');
        
        const icon = btn.querySelector('i');
        if (isHidden) {
            icon.setAttribute('data-lucide', 'x');
        } else {
            icon.setAttribute('data-lucide', 'menu');
        }
        lucide.createIcons();
    });
}

// Navbar Scroll Effect
function initNavbarScroll() {
    const nav = document.querySelector('nav');
    if (!nav) return;
    
    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            nav.querySelector('.bg-navy-900\\/80').classList.add('shadow-2xl');
        } else {
            nav.querySelector('.bg-navy-900\\/80').classList.remove('shadow-2xl');
        }
        
        lastScroll = currentScroll;
    });
}

// Scroll Reveal Animation
function initScrollReveal() {
    const reveals = document.querySelectorAll('.scroll-reveal');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    reveals.forEach(el => observer.observe(el));
}

// Tilt Effect on Cards
function initTiltCards() {
    const cards = document.querySelectorAll('.tilt-card');
    
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 20;
            const rotateY = (centerX - x) / 20;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)';
        });
    });
}

// Animated Counters
function initCounters() {
    const counters = document.querySelectorAll('.stat-counter');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = parseInt(counter.getAttribute('data-target'));
                const duration = 2000;
                const start = parseInt(counter.textContent) || 0;
                const increment = (target - start) / (duration / 16);
                let current = start;
                
                const updateCounter = () => {
                    current += increment;
                    if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
                        counter.textContent = target;
                    } else {
                        counter.textContent = Math.floor(current);
                        requestAnimationFrame(updateCounter);
                    }
                };
                
                updateCounter();
                observer.unobserve(counter);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => observer.observe(counter));
}

// Ripple Effect
function initRippleEffect() {
    document.addEventListener('click', (e) => {
        const rippleElement = e.target.closest('.ripple');
        if (!rippleElement) return;
        
        const ripple = document.createElement('span');
        const rect = rippleElement.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: scale(0);
            animation: ripple 0.6s ease-out;
            pointer-events: none;
        `;
        
        rippleElement.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
    });
}

// Smooth Scroll for Anchor Links
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ 
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Flash Message Auto Dismiss
function initFlashMessages() {
    const messages = document.querySelectorAll('.flash-message');
    messages.forEach((msg, index) => {
        setTimeout(() => {
            msg.style.animation = 'slideDown 0.3s ease reverse forwards';
            setTimeout(() => msg.remove(), 300);
        }, 5000 + index * 1000);
    });
}

// Parallax Effect
function initParallax() {
    window.addEventListener('scroll', () => {
        const parallaxElements = document.querySelectorAll('.parallax');
        parallaxElements.forEach(el => {
            const speed = el.getAttribute('data-speed') || 0.5;
            const yPos = -(window.pageYOffset * speed);
            el.style.transform = `translateY(${yPos}px)`;
        });
    });
}

// Magnetic Button Effect
function initMagneticButtons() {
    const buttons = document.querySelectorAll('.magnetic-btn');
    
    buttons.forEach(btn => {
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            
            btn.style.transform = `translate(${x * 0.3}px, ${y * 0.3}px)`;
        });
        
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'translate(0, 0)';
        });
    });
}

// Initialize all effects
initFlashMessages();
initParallax();
initMagneticButtons();