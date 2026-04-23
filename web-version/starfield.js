/**
 * Calming Interactive Starfield Component
 * Creates a soothing starfield with mouse-responsive drift effects
 */

class CalmingStarfield {
    constructor(options = {}) {
        // Default configuration
        this.config = {
            container: '#starfield-container',
            starCount: 200,
            driftSensitivity: 0.5,
            colors: ['#4a90e2', '#9b59b6', '#ffffff', '#f8c9d4', '#87ceeb'],
            maxStarSize: 3,
            minStarSize: 0.5,
            layers: 3,
            reducedMotion: false,
            ...options
        };

        // Initialize component
        this.container = null;
        this.canvas = null;
        this.ctx = null;
        this.stars = [];
        this.mouse = { x: 0, y: 0, isMoving: false };
        this.animationId = null;
        this.lastTime = 0;
        this.isInitialized = false;

        // Performance tracking
        this.frameCount = 0;
        this.lastFpsTime = 0;
        this.fps = 60;

        this.init();
    }

    /**
     * Initialize the starfield component
     */
    init() {
        try {
            this.setupContainer();
            this.setupCanvas();
            this.createStars();
            this.bindEvents();
            this.startAnimation();
            this.isInitialized = true;
        } catch (error) {
            console.error('Failed to initialize Calming Starfield:', error);
        }
    }

    /**
     * Set up the container element
     */
    setupContainer() {
        const containerElement = typeof this.config.container === 'string' 
            ? document.querySelector(this.config.container)
            : this.config.container;

        if (!containerElement) {
            throw new Error(`Container not found: ${this.config.container}`);
        }

        this.container = containerElement;
        this.container.style.position = 'relative';
        
        // Add loading indicator
        this.showLoading();
    }

    /**
     * Set up the canvas element
     */
    setupCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.className = 'starfield-canvas';
        this.ctx = this.canvas.getContext('2d');

        // Set canvas size
        this.resizeCanvas();

        // Add canvas to container
        this.container.appendChild(this.canvas);
        
        // Remove loading indicator
        this.hideLoading();
    }

    /**
     * Resize canvas to match container
     */
    resizeCanvas() {
        const rect = this.container.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';

        this.ctx.scale(dpr, dpr);
        
        // Store dimensions for easy access
        this.width = rect.width;
        this.height = rect.height;
    }

    /**
     * Create star particles with multiple layers
     */
    createStars() {
        this.stars = [];
        const starsPerLayer = Math.floor(this.config.starCount / this.config.layers);

        for (let layer = 0; layer < this.config.layers; layer++) {
            const layerDepth = (layer + 1) / this.config.layers;
            const layerStars = layer === this.config.layers - 1 
                ? this.config.starCount - (starsPerLayer * layer)
                : starsPerLayer;

            for (let i = 0; i < layerStars; i++) {
                this.stars.push(this.createStar(layerDepth));
            }
        }
    }

    /**
     * Create a single star particle
     */
    createStar(depth) {
        const sizeMultiplier = depth * 0.8 + 0.2; // Closer stars are bigger
        const baseSize = this.config.minStarSize + 
            (this.config.maxStarSize - this.config.minStarSize) * Math.random();

        return {
            x: Math.random() * this.width,
            y: Math.random() * this.height,
            originalX: 0,
            originalY: 0,
            vx: 0,
            vy: 0,
            size: baseSize * sizeMultiplier,
            opacity: 0.3 + Math.random() * 0.7,
            baseOpacity: 0.3 + Math.random() * 0.7,
            color: this.config.colors[Math.floor(Math.random() * this.config.colors.length)],
            depth: depth,
            twinklePhase: Math.random() * Math.PI * 2,
            twinkleSpeed: 0.02 + Math.random() * 0.03,
            glowIntensity: 0.5 + Math.random() * 0.5
        };
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Mouse movement tracking
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseenter', () => this.mouse.isMoving = true);
        this.canvas.addEventListener('mouseleave', () => {
            this.mouse.isMoving = false;
            this.mouse.x = this.width / 2;
            this.mouse.y = this.height / 2;
        });

        // Resize handling
        window.addEventListener('resize', () => this.handleResize());

        // Reduced motion preference
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
            mediaQuery.addListener(() => this.updateReducedMotion(mediaQuery.matches));
            this.updateReducedMotion(mediaQuery.matches);
        }
    }

    /**
     * Handle mouse movement
     */
    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        this.mouse.x = e.clientX - rect.left;
        this.mouse.y = e.clientY - rect.top;
        this.mouse.isMoving = true;
    }

    /**
     * Handle window resize
     */
    handleResize() {
        this.resizeCanvas();
        // Reposition stars that are now outside bounds
        this.stars.forEach(star => {
            if (star.x > this.width) star.x = this.width;
            if (star.y > this.height) star.y = this.height;
        });
    }

    /**
     * Update reduced motion setting
     */
    updateReducedMotion(reduced) {
        this.config.reducedMotion = reduced;
    }

    /**
     * Start the animation loop
     */
    startAnimation() {
        const animate = (currentTime) => {
            const deltaTime = currentTime - this.lastTime;
            this.lastTime = currentTime;

            this.updateFPS(currentTime);
            this.updateStars(deltaTime);
            this.render();

            this.animationId = requestAnimationFrame(animate);
        };

        this.animationId = requestAnimationFrame(animate);
    }

    /**
     * Update FPS tracking
     */
    updateFPS(currentTime) {
        this.frameCount++;
        if (currentTime - this.lastFpsTime >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastFpsTime = currentTime;
        }
    }

    /**
     * Update star positions and properties
     */
    updateStars(deltaTime) {
        const motionMultiplier = this.config.reducedMotion ? 0.1 : 1;
        const time = Date.now() * 0.001;

        this.stars.forEach(star => {
            // Store original position for drift calculations
            if (star.originalX === 0 && star.originalY === 0) {
                star.originalX = star.x;
                star.originalY = star.y;
            }

            // Calculate drift away from mouse
            if (this.mouse.isMoving) {
                const dx = star.x - this.mouse.x;
                const dy = star.y - this.mouse.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                const maxDistance = Math.sqrt(this.width * this.width + this.height * this.height);
                
                if (distance < maxDistance * 0.3) {
                    const force = (1 - distance / (maxDistance * 0.3)) * this.config.driftSensitivity;
                    const angle = Math.atan2(dy, dx);
                    
                    star.vx += Math.cos(angle) * force * star.depth * motionMultiplier;
                    star.vy += Math.sin(angle) * force * star.depth * motionMultiplier;
                }
            }

            // Apply gentle return force to original position
            const returnForce = 0.02 * motionMultiplier;
            star.vx += (star.originalX - star.x) * returnForce;
            star.vy += (star.originalY - star.y) * returnForce;

            // Apply friction
            star.vx *= 0.95;
            star.vy *= 0.95;

            // Update position
            star.x += star.vx;
            star.y += star.vy;

            // Wrap around screen edges
            if (star.x < -star.size) star.x = this.width + star.size;
            if (star.x > this.width + star.size) star.x = -star.size;
            if (star.y < -star.size) star.y = this.height + star.size;
            if (star.y > this.height + star.size) star.y = -star.size;

            // Update twinkle effect
            star.twinklePhase += star.twinkleSpeed * motionMultiplier;
            const twinkle = Math.sin(star.twinklePhase) * 0.3 + 0.7;
            star.opacity = star.baseOpacity * twinkle;
        });
    }

    /**
     * Render the starfield
     */
    render() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.width, this.height);

        // Sort stars by depth for proper layering
        const sortedStars = [...this.stars].sort((a, b) => a.depth - b.depth);

        // Render each star
        sortedStars.forEach(star => this.renderStar(star));
    }

    /**
     * Render a single star with glow effect
     */
    renderStar(star) {
        const x = star.x;
        const y = star.y;
        const size = star.size;
        const opacity = Math.max(0, Math.min(1, star.opacity));

        // Create radial gradient for glow effect
        const gradient = this.ctx.createRadialGradient(x, y, 0, x, y, size * 3);
        gradient.addColorStop(0, this.hexToRgba(star.color, opacity));
        gradient.addColorStop(0.4, this.hexToRgba(star.color, opacity * 0.6));
        gradient.addColorStop(1, this.hexToRgba(star.color, 0));

        // Draw glow
        this.ctx.fillStyle = gradient;
        this.ctx.beginPath();
        this.ctx.arc(x, y, size * 3, 0, Math.PI * 2);
        this.ctx.fill();

        // Draw core star
        this.ctx.fillStyle = this.hexToRgba(star.color, opacity);
        this.ctx.beginPath();
        this.ctx.arc(x, y, size, 0, Math.PI * 2);
        this.ctx.fill();

        // Add bright center point for larger stars
        if (size > 2) {
            this.ctx.fillStyle = this.hexToRgba('#ffffff', opacity * 0.8);
            this.ctx.beginPath();
            this.ctx.arc(x, y, size * 0.3, 0, Math.PI * 2);
            this.ctx.fill();
        }
    }

    /**
     * Convert hex color to rgba
     */
    hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    /**
     * Show loading indicator
     */
    showLoading() {
        const loading = document.createElement('div');
        loading.className = 'starfield-loading';
        loading.textContent = 'Initializing starfield...';
        this.container.appendChild(loading);
    }

    /**
     * Hide loading indicator
     */
    hideLoading() {
        const loading = this.container.querySelector('.starfield-loading');
        if (loading) {
            loading.remove();
        }
    }

    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        const oldStarCount = this.config.starCount;
        this.config = { ...this.config, ...newConfig };

        // Recreate stars if count changed
        if (newConfig.starCount && newConfig.starCount !== oldStarCount) {
            this.createStars();
        }

        // Update colors if changed
        if (newConfig.colors) {
            this.stars.forEach(star => {
                star.color = this.config.colors[Math.floor(Math.random() * this.config.colors.length)];
            });
        }
    }

    /**
     * Destroy the starfield and clean up
     */
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }

        // Remove event listeners
        window.removeEventListener('resize', this.handleResize);

        this.isInitialized = false;
    }

    /**
     * Get current performance stats
     */
    getStats() {
        return {
            fps: this.fps,
            starCount: this.stars.length,
            isInitialized: this.isInitialized
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CalmingStarfield;
}

// Make available globally
window.CalmingStarfield = CalmingStarfield;