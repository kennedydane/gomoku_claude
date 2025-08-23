/**
 * Build Configuration for Go Goban Go
 * Handles asset optimization, minification, and production builds
 */

const path = require('path');
const fs = require('fs');

const config = {
    // Source paths
    src: {
        js: 'backend/static/js',
        css: 'backend/static/css', 
        images: 'backend/static/img',
        templates: 'backend/templates'
    },
    
    // Output paths for optimized assets
    dist: {
        js: 'backend/static/dist',
        css: 'backend/static/dist',
        images: 'backend/static/dist/img'
    },
    
    // Files to process
    files: {
        js: [
            'app.optimized.js',
            'sse-manager.optimized.js', 
            'htmx-sse-integration.optimized.js'
        ],
        css: [
            'critical.css',
            'style.css'
        ]
    },
    
    // Optimization settings
    optimization: {
        js: {
            compress: {
                drop_console: true,
                drop_debugger: true,
                pure_funcs: ['console.log', 'console.info', 'console.debug']
            },
            mangle: {
                toplevel: true,
                reserved: ['htmx', 'sseManager', 'OptimizedSSEManager']
            },
            output: {
                comments: false
            }
        },
        css: {
            level: 2,
            compatibility: 'ie11',
            format: 'beautify'
        }
    },
    
    // File size targets (in bytes)
    targets: {
        'app.min.js': 50000,        // 50KB target
        'app.min.css': 30000,       // 30KB target
        'critical.css': 10000       // 10KB for critical CSS
    }
};

module.exports = config;