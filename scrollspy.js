/**
 * Scrollspy & Mobile Cart Bar Handler
 * 
 * Handles:
 * - Smooth scrolling to categories
 * - Active category highlighting (Bootstrap 5 scrollspy)
 * - Mobile cart bar show/hide based on cart contents
 * - Sync cart between desktop and mobile views
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // BOOTSTRAP 5 SCROLLSPY INITIALIZATION
    // ==========================================
    
    const scrollSpyElement = document.querySelector('[data-bs-spy="scroll"]');
    if (scrollSpyElement) {
        // Bootstrap 5 automatically handles scrollspy
        // Just need to ensure smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
    
    // ==========================================
    // MOBILE CATEGORIES ACTIVE STATE
    // ==========================================
    
    const mobileCategoriesNav = document.querySelector('.mobile-categories-scroll .nav');
    if (mobileCategoriesNav) {
        // Use Intersection Observer for mobile category highlighting
        const categoryHeaders = document.querySelectorAll('.category-section');
        const mobileNavLinks = mobileCategoriesNav.querySelectorAll('.nav-link');
        
        const observerOptions = {
            root: null,
            rootMargin: '-100px 0px -70% 0px',
            threshold: 0
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const categoryId = entry.target.id;
                    
                    // Update mobile nav active state
                    mobileNavLinks.forEach(link => {
                        if (link.getAttribute('href') === `#${categoryId}`) {
                            link.classList.add('active');
                            
                            // Scroll the nav link into view
                            link.scrollIntoView({
                                behavior: 'smooth',
                                block: 'nearest',
                                inline: 'center'
                            });
                        } else {
                            link.classList.remove('active');
                        }
                    });
                }
            });
        }, observerOptions);
        
        categoryHeaders.forEach(header => observer.observe(header));
    }
    
    // ==========================================
    // MOBILE CART BAR VISIBILITY
    // ==========================================
    
    function updateMobileCartBar() {
        const cartData = Cart.get();
        const mobileCartBar = document.getElementById('mobileCartBar');
        
        if (!mobileCartBar) return;
        
        if (cartData.length > 0) {
            mobileCartBar.style.display = 'block';
        } else {
            mobileCartBar.style.display = 'none';
        }
    }
    
    // Update mobile cart bar on page load
    updateMobileCartBar();
    
    // Listen for cart changes (we'll need to trigger custom events from cart.js)
    document.addEventListener('cartUpdated', updateMobileCartBar);
    
    // ==========================================
    // SYNC CART BETWEEN DESKTOP & MOBILE VIEWS
    // ==========================================
    
    // Override Cart.updateUI to also update mobile view
    // Override Cart.updateUI to also update mobile cart bar
    const originalUpdateUI = Cart.updateUI;
    Cart.updateUI = function() {
        // Call original update (handles both desktop AND mobile cart)
        originalUpdateUI.call(this);
        
        // Update mobile cart bar visibility
        updateMobileCartBar();
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('cartUpdated'));
    };
    
});