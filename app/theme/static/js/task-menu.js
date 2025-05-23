// Task menu dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    // Task menu dropdown toggle
    document.addEventListener('click', function(event) {
        const isMenuBtn = event.target.closest('.task-menu-btn');
        const isMenuDropdown = event.target.closest('.task-menu-dropdown');
        
        // Close all open dropdowns first
        document.querySelectorAll('.task-menu-dropdown').forEach(dropdown => {
            if (!isMenuDropdown || (isMenuDropdown && isMenuDropdown !== dropdown)) {
                dropdown.classList.add('hidden');
            }
        });        // If a menu button was clicked, toggle its dropdown
        if (isMenuBtn) {
            event.stopPropagation();
            const taskId = isMenuBtn.getAttribute('data-task-id');
            const dropdown = isMenuBtn.nextElementSibling;
            dropdown.classList.toggle('hidden');
            
            // Position the dropdown to the left side of the three-dot button
            const btnRect = isMenuBtn.getBoundingClientRect();
            const dropdownWidth = 288; // w-72 = 288px
            
            dropdown.style.position = 'fixed';
            dropdown.style.top = `${btnRect.bottom + window.scrollY + 5}px`;
            
            // Position to the left of the button
            let leftPosition = btnRect.left - dropdownWidth - 5;
            
            // If dropdown would go off the left edge of screen, position it to the right
            if (leftPosition < 0) {
                leftPosition = btnRect.right + 5;
            }
            
            // If it would still go off the right edge, center it under the button
            if (leftPosition + dropdownWidth > window.innerWidth) {
                leftPosition = btnRect.left - (dropdownWidth / 2) + (btnRect.width / 2);
            }
            
            dropdown.style.left = `${leftPosition}px`;
        }});

    // Handle color selection in task menu dropdown
    document.addEventListener('click', function(event) {
        const colorSquare = event.target.closest('.task-menu-dropdown .grid.grid-cols-5 > div');
        
        if (colorSquare) {
            event.stopPropagation();
            
            // Remove any previous selection indication from this dropdown
            const grid = colorSquare.closest('.grid');
            grid.querySelectorAll('div').forEach(el => {
                el.classList.remove('ring-2', 'ring-offset-1', 'ring-gray-400');
            });
            
            // Add selection indication to clicked color
            colorSquare.classList.add('ring-2', 'ring-offset-1', 'ring-gray-400');
            
            // Get the background color
            const bgColor = window.getComputedStyle(colorSquare).backgroundColor;
            
            // Get the task element and update its color
            const dropdown = colorSquare.closest('.task-menu-dropdown');
            const taskId = dropdown.previousElementSibling.getAttribute('data-task-id');
            const taskElement = document.querySelector(`.task-item-${taskId}`);
            
            if (taskElement) {
                // Update the color of the task circle
                const colorCircle = taskElement.querySelector('.w-5.h-5');
                if (colorCircle) {
                    // Remove all background color classes
                    colorCircle.className = colorCircle.className.replace(/bg-\w+-\d+/g, '');
                    // Add the new background color
                    colorCircle.style.backgroundColor = bgColor;
                }
            }
            
            // Save the color preference to the database
            console.log('Selected color for task:', taskId, 'Color:', bgColor);
            
            // Close the dropdown after a short delay to show the selection
            setTimeout(() => {
                dropdown.classList.add('hidden');
            }, 300);
        }    });

    // Handle Cancel button clicks
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('cancel-color-btn')) {
            event.stopPropagation();
            const dropdown = event.target.closest('.task-menu-dropdown');
            dropdown.classList.add('hidden');
        }
    });

    // Handle Apply button clicks
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('apply-color-btn')) {
            event.stopPropagation();
            const dropdown = event.target.closest('.task-menu-dropdown');
            dropdown.classList.add('hidden');
        }
    });

    // Handle custom color input 
    document.querySelectorAll('.task-menu-dropdown input[type="text"]').forEach(input => {
        input.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                event.stopPropagation();
                
                const dropdown = this.closest('.task-menu-dropdown');
                const customColor = this.value;
                
                // Get the task ID from the menu button
                const taskId = dropdown.previousElementSibling.getAttribute('data-task-id');
                
                // Here you would save the custom color to the database
                console.log('Applied custom color for task:', taskId, 'Color:', customColor);
                
                // Close the dropdown
                dropdown.classList.add('hidden');
            }
        });
    });
});