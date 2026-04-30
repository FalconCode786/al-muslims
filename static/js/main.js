// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const themeToggle = document.getElementById('theme-toggle');
    const themeToggleMobile = document.getElementById('theme-toggle-mobile');

    const applyTheme = (theme) => {
        const isDark = theme === 'dark';
        document.documentElement.classList.toggle('dark', isDark);
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');

        if (themeToggle) {
            themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            themeToggle.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        }

        if (themeToggleMobile) {
            themeToggleMobile.textContent = isDark ? 'Switch to light theme' : 'Switch to dark theme';
        }

        const themeIcon = document.querySelector('[data-theme-icon="desktop"]');
        if (themeIcon) {
            themeIcon.setAttribute('data-lucide', isDark ? 'sun' : 'moon');
            lucide.createIcons();
        }
    };

    const getCurrentTheme = () => document.documentElement.classList.contains('dark') ? 'dark' : 'light';

    const toggleTheme = () => {
        const nextTheme = getCurrentTheme() === 'dark' ? 'light' : 'dark';
        applyTheme(nextTheme);
    };
    const closeMenu = () => {
        mobileMenu.classList.add('hidden');
        mobileMenuButton.innerHTML = '<i data-lucide="menu" class="h-6 w-6"></i>';
        mobileMenuButton.setAttribute('aria-expanded', 'false');
        mobileMenuButton.setAttribute('aria-label', 'Open mobile menu');
        lucide.createIcons();
    };
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            const isCollapsed = mobileMenu.classList.contains('hidden');
            
            if (isCollapsed) {
                mobileMenu.classList.remove('hidden');
                mobileMenuButton.innerHTML = '<i data-lucide="x" class="h-6 w-6"></i>';
                mobileMenuButton.setAttribute('aria-expanded', 'true');
                mobileMenuButton.setAttribute('aria-label', 'Close mobile menu');
            } else {
                closeMenu();
                return;
            }
            
            lucide.createIcons();
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && !mobileMenu.classList.contains('hidden')) {
                closeMenu();
                mobileMenuButton.focus();
            }
        });
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    if (themeToggleMobile) {
        themeToggleMobile.addEventListener('click', toggleTheme);
    }

    applyTheme(getCurrentTheme());
    
    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.3s ease-out';
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });
});

// Form validation enhancement
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('border-red-500');
            isValid = false;
        } else {
            input.classList.remove('border-red-500');
        }
    });
    
    return isValid;
}

// Prevent double submission
document.addEventListener('submit', function(e) {
    const form = e.target;
    if (form.classList.contains('submitted')) {
        e.preventDefault();
        return false;
    }
    form.classList.add('submitted');
    setTimeout(() => form.classList.remove('submitted'), 2000);
});