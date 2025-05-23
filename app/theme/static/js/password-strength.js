document.addEventListener('DOMContentLoaded', function() {
    // Support both registration form and change password form
    const passwordInput = document.getElementById('id_password') || document.getElementById('new_password');
    const confirmPasswordInput = document.getElementById('id_confirm_password') || document.getElementById('confirm_password');
    const strengthMeter = document.getElementById('password-strength-meter') || document.querySelector('.password-strength-bar');
    const strengthText = document.getElementById('password-strength-text') || document.querySelector('.password-strength-text');
    const matchStatus = document.getElementById('password-match-status') || document.querySelector('.password-match-text');
    
    // Get the criteria elements if they exist
    const criteriaItems = {
        length: document.getElementById('criteria-length'),
        uppercase: document.getElementById('criteria-uppercase'),
        lowercase: document.getElementById('criteria-lowercase'),
        number: document.getElementById('criteria-number'),
        special: document.getElementById('criteria-special')
    };
    
    if (!passwordInput || !strengthMeter || !strengthText) return;
      passwordInput.addEventListener('input', function() {
        const password = passwordInput.value;
        const strength = calculatePasswordStrength(password);
        
        // Update the strength meter
        strengthMeter.value = strength.score;
        
        // Update the strength text and color
        strengthText.textContent = strength.message;
        
        // Update text color based on strength
        strengthText.className = 'text-sm mt-1 ' + getColorClass(strength.score);
        
        // Update criteria status
        updateCriteriaStatus(password);
        
        // Check if passwords match if confirmPasswordInput has a value
        if (confirmPasswordInput && confirmPasswordInput.value) {
            checkPasswordsMatch();
        }
    });
    
    // Add event listener for confirm password
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordsMatch);
    }
    
    function checkPasswordsMatch() {
        if (!confirmPasswordInput || !passwordInput || !matchStatus) return;
        
        if (confirmPasswordInput.value === '') {
            matchStatus.textContent = '';
            matchStatus.className = '';
            return;
        }
        
        if (confirmPasswordInput.value === passwordInput.value) {
            matchStatus.textContent = 'Passwords match';
            matchStatus.className = 'text-green-500 text-xs mt-1';
            confirmPasswordInput.classList.add('border-green-500');
            confirmPasswordInput.classList.remove('border-red-500');
        } else {
            matchStatus.textContent = 'Passwords do not match';
            matchStatus.className = 'text-red-500 text-xs mt-1';
            confirmPasswordInput.classList.add('border-red-500');
            confirmPasswordInput.classList.remove('border-green-500');
        }
    }
    
    function updateCriteriaStatus(password) {
        // Create criteria checklist if it doesn't exist already
        const criteriaList = document.querySelector('.password-criteria-list');
        if (!criteriaList) {
            createCriteriaList();
            return; // Return and let the next input event handle updates
        }
        
        // Update each criteria item
        const criteria = [
            { id: 'criteria-length', test: password.length >= 8, text: 'At least 8 characters' },
            { id: 'criteria-uppercase', test: /[A-Z]/.test(password), text: 'At least 1 uppercase letter' },
            { id: 'criteria-lowercase', test: /[a-z]/.test(password), text: 'At least 1 lowercase letter' },
            { id: 'criteria-number', test: /[0-9]/.test(password), text: 'At least 1 number' },
            { id: 'criteria-special', test: /[!@#$%^&*(),.?":{}|<>]/.test(password), text: 'At least 1 special character' }
        ];
        
        criteria.forEach(criterion => {
            const item = document.getElementById(criterion.id);
            if (item) {
                if (criterion.test) {
                    item.classList.remove('text-neutral-600');
                    item.classList.add('text-green-500');
                    item.innerHTML = `<span class="inline-block w-4">✓</span> ${criterion.text}`;
                } else {
                    item.classList.remove('text-green-500');
                    item.classList.add('text-neutral-600');
                    item.innerHTML = `<span class="inline-block w-4">•</span> ${criterion.text}`;
                }
            }
        });
    }
    
    function createCriteriaList() {
        // Find the container for the criteria
        const container = document.querySelector('.text-xs.text-neutral-600.mt-1');
        if (!container) return;
        
        // Clear existing content
        container.innerHTML = '<p>Password must contain:</p>';
        
        // Create new list with IDs for each item
        const ul = document.createElement('ul');
        ul.className = 'password-criteria-list list-disc ml-5 space-y-1 mt-1';
        
        const criteria = [
            { id: 'criteria-length', text: 'At least 8 characters' },
            { id: 'criteria-uppercase', text: 'At least 1 uppercase letter' },
            { id: 'criteria-lowercase', text: 'At least 1 lowercase letter' },
            { id: 'criteria-number', text: 'At least 1 number' },
            { id: 'criteria-special', text: 'At least 1 special character' }
        ];
        
        criteria.forEach(criterion => {
            const li = document.createElement('li');
            li.id = criterion.id;
            li.className = 'text-neutral-600';
            li.innerHTML = `<span class="inline-block w-4">•</span> ${criterion.text}`;
            ul.appendChild(li);
        });
        
        container.appendChild(ul);
    }
    
    function calculatePasswordStrength(password) {
        // Initialize score and feedback message
        let score = 0;
        let message = 'Too weak';
        
        if (password.length === 0) {
            return { score: 0, message: '' };
        }
        
        // Check length
        if (password.length > 5) score += 1;
        if (password.length > 8) score += 1;
        
        // Check for mixed case characters
        if (password.match(/[a-z]/) && password.match(/[A-Z]/)) score += 1;
        
        // Check for numbers
        if (password.match(/[0-9]/)) score += 1;
        
        // Check for special characters
        if (password.match(/[^a-zA-Z0-9]/)) score += 1;
        
        // Determine message based on score
        if (score <= 1) {
            message = 'Too weak';
        } else if (score <= 2) {
            message = 'Could be stronger';
        } else if (score <= 3) {
            message = 'Medium strength';
        } else if (score <= 4) {
            message = 'Strong password';
        } else {
            message = 'Very strong password';
        }
        
        return { score, message };
    }
    
    function getColorClass(score) {
        if (score <= 1) {
            return 'text-red-500';
        } else if (score <= 2) {
            return 'text-orange-500';
        } else if (score <= 3) {
            return 'text-yellow-500';
        } else if (score <= 4) {
            return 'text-green-500';
        } else {
            return 'text-emerald-600';
        }
    }
});