// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            const isExpanded = mobileMenu.classList.contains('hidden');
            
            if (isExpanded) {
                mobileMenu.classList.remove('hidden');
                mobileMenuButton.innerHTML = '<i data-lucide="x" class="h-6 w-6"></i>';
            } else {
                mobileMenu.classList.add('hidden');
                mobileMenuButton.innerHTML = '<i data-lucide="menu" class="h-6 w-6"></i>';
            }
            
            lucide.createIcons();
        });
    }
    
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