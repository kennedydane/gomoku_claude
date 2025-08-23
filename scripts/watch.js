#!/usr/bin/env node

/**
 * Development Watch Script for Go Goban Go
 * Watches for file changes and rebuilds assets automatically
 */

const chokidar = require('chokidar');
const path = require('path');
const config = require('../build.config.js');
const AssetBuilder = require('./build.js');

class DevelopmentWatcher {
    constructor() {
        this.builder = new AssetBuilder();
        this.isBuilding = false;
        this.buildQueue = new Set();
    }

    async start() {
        console.log('👀 Starting development watcher...\n');
        
        // Initial build
        await this.builder.build();
        
        // Watch for changes
        this.setupWatchers();
        
        console.log('🔄 Watching for file changes... (Press Ctrl+C to stop)\n');
    }

    setupWatchers() {
        // Watch JavaScript files
        const jsWatcher = chokidar.watch(path.join(config.src.js, '*.optimized.js'), {
            persistent: true,
            ignoreInitial: true
        });
        
        jsWatcher.on('change', (filePath) => {
            console.log(`🔧 JavaScript changed: ${path.basename(filePath)}`);
            this.queueBuild('js');
        });
        
        // Watch CSS files
        const cssWatcher = chokidar.watch(path.join(config.src.css, '*.css'), {
            persistent: true,
            ignoreInitial: true
        });
        
        cssWatcher.on('change', (filePath) => {
            console.log(`🎨 CSS changed: ${path.basename(filePath)}`);
            this.queueBuild('css');
        });
        
        // Watch templates
        const templateWatcher = chokidar.watch(path.join(config.src.templates, '*.optimized.html'), {
            persistent: true,
            ignoreInitial: true
        });
        
        templateWatcher.on('change', (filePath) => {
            console.log(`📄 Template changed: ${path.basename(filePath)}`);
            this.queueBuild('template');
        });
    }

    async queueBuild(type) {
        this.buildQueue.add(type);
        
        if (!this.isBuilding) {
            this.isBuilding = true;
            
            // Debounce builds (wait 500ms for more changes)
            setTimeout(async () => {
                try {
                    const buildTypes = Array.from(this.buildQueue);
                    this.buildQueue.clear();
                    
                    console.log(`🏗️  Rebuilding: ${buildTypes.join(', ')}`);
                    
                    if (buildTypes.includes('js') || buildTypes.includes('css') || buildTypes.includes('template')) {
                        await this.builder.build();
                        console.log('✅ Rebuild completed\n');
                    }
                    
                } catch (error) {
                    console.error('❌ Rebuild failed:', error);
                } finally {
                    this.isBuilding = false;
                }
            }, 500);
        }
    }
}

// Run watcher if called directly
if (require.main === module) {
    const watcher = new DevelopmentWatcher();
    watcher.start().catch(console.error);
    
    // Handle graceful shutdown
    process.on('SIGINT', () => {
        console.log('\n👋 Stopping development watcher...');
        process.exit(0);
    });
}

module.exports = DevelopmentWatcher;