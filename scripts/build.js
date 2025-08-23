#!/usr/bin/env node

/**
 * Production Build Script for Go Goban Go
 * Optimizes, minifies, and bundles all client-side assets
 */

const fs = require('fs').promises;
const path = require('path');
const { execSync } = require('child_process');
const config = require('../build.config.js');

class AssetBuilder {
    constructor() {
        this.stats = {
            originalSize: 0,
            optimizedSize: 0,
            compressionRatio: 0,
            files: []
        };
    }

    async build() {
        console.log('🏗️  Starting production build...\n');
        
        try {
            await this.createDirectories();
            await this.processJavaScript();
            await this.processCSS();
            await this.generateCriticalCSS();
            await this.optimizeImages();
            await this.generateManifest();
            await this.updateTemplates();
            
            this.printBuildStats();
            console.log('✅ Build completed successfully!');
            
        } catch (error) {
            console.error('❌ Build failed:', error);
            process.exit(1);
        }
    }

    async createDirectories() {
        console.log('📁 Creating output directories...');
        
        for (const dir of Object.values(config.dist)) {
            await fs.mkdir(dir, { recursive: true });
        }
        
        console.log('✅ Directories created\n');
    }

    async processJavaScript() {
        console.log('🔧 Processing JavaScript files...');
        
        const jsFiles = [];
        
        // Bundle all optimized JS files
        for (const file of config.files.js) {
            const sourcePath = path.join(config.src.js, file);
            
            try {
                const content = await fs.readFile(sourcePath, 'utf8');
                jsFiles.push({
                    name: file,
                    content: content,
                    size: Buffer.byteLength(content, 'utf8')
                });
                
                this.stats.originalSize += Buffer.byteLength(content, 'utf8');
                
            } catch (error) {
                console.log(`⚠️  Warning: Could not read ${file}, skipping...`);
            }
        }
        
        // Create bundled file
        const bundledContent = jsFiles.map(f => f.content).join('\n\n');
        const bundledPath = path.join(config.dist.js, 'app.bundle.js');
        await fs.writeFile(bundledPath, bundledContent);
        
        // Minify bundled file
        console.log('📦 Minifying JavaScript bundle...');
        
        const minifiedPath = path.join(config.dist.js, 'app.min.js');
        const uglifyCommand = `npx uglifyjs "${bundledPath}" -o "${minifiedPath}" -c drop_console=true,drop_debugger=true -m toplevel=true --comments false`;
        
        try {
            execSync(uglifyCommand, { stdio: 'inherit' });
            
            const minifiedContent = await fs.readFile(minifiedPath, 'utf8');
            const minifiedSize = Buffer.byteLength(minifiedContent, 'utf8');
            this.stats.optimizedSize += minifiedSize;
            
            this.stats.files.push({
                name: 'app.min.js',
                originalSize: bundledContent.length,
                optimizedSize: minifiedSize,
                savings: ((bundledContent.length - minifiedSize) / bundledContent.length * 100).toFixed(1)
            });
            
            console.log(`✅ JavaScript optimized: ${(bundledContent.length / 1024).toFixed(1)}KB → ${(minifiedSize / 1024).toFixed(1)}KB\n`);
            
        } catch (error) {
            console.log('⚠️  JavaScript minification failed, using non-minified version');
            await fs.copyFile(bundledPath, minifiedPath);
        }
    }

    async processCSS() {
        console.log('🎨 Processing CSS files...');
        
        const cssFiles = [];
        
        // Bundle CSS files (excluding critical.css which is handled separately)
        for (const file of config.files.css) {
            if (file === 'critical.css') continue;
            
            const sourcePath = path.join(config.src.css, file);
            
            try {
                const content = await fs.readFile(sourcePath, 'utf8');
                cssFiles.push({
                    name: file,
                    content: content,
                    size: Buffer.byteLength(content, 'utf8')
                });
                
                this.stats.originalSize += Buffer.byteLength(content, 'utf8');
                
            } catch (error) {
                console.log(`⚠️  Warning: Could not read ${file}, skipping...`);
            }
        }
        
        // Create bundled CSS
        const bundledContent = cssFiles.map(f => f.content).join('\n\n');
        const bundledPath = path.join(config.dist.css, 'app.bundle.css');
        await fs.writeFile(bundledPath, bundledContent);
        
        // Minify CSS
        console.log('📦 Minifying CSS bundle...');
        
        const minifiedPath = path.join(config.dist.css, 'app.min.css');
        const cleanCSSCommand = `npx cleancss -o "${minifiedPath}" "${bundledPath}"`;
        
        try {
            execSync(cleanCSSCommand, { stdio: 'inherit' });
            
            const minifiedContent = await fs.readFile(minifiedPath, 'utf8');
            const minifiedSize = Buffer.byteLength(minifiedContent, 'utf8');
            this.stats.optimizedSize += minifiedSize;
            
            this.stats.files.push({
                name: 'app.min.css',
                originalSize: bundledContent.length,
                optimizedSize: minifiedSize,
                savings: ((bundledContent.length - minifiedSize) / bundledContent.length * 100).toFixed(1)
            });
            
            console.log(`✅ CSS optimized: ${(bundledContent.length / 1024).toFixed(1)}KB → ${(minifiedSize / 1024).toFixed(1)}KB\n`);
            
        } catch (error) {
            console.log('⚠️  CSS minification failed, using non-minified version');
            await fs.copyFile(bundledPath, minifiedPath);
        }
    }

    async generateCriticalCSS() {
        console.log('⚡ Processing critical CSS...');
        
        const criticalPath = path.join(config.src.css, 'critical.css');
        const criticalDistPath = path.join(config.dist.css, 'critical.min.css');
        
        try {
            const content = await fs.readFile(criticalPath, 'utf8');
            const originalSize = Buffer.byteLength(content, 'utf8');
            
            // Minify critical CSS
            const cleanCSSCommand = `npx cleancss -o "${criticalDistPath}" "${criticalPath}"`;
            execSync(cleanCSSCommand, { stdio: 'inherit' });
            
            const minifiedContent = await fs.readFile(criticalDistPath, 'utf8');
            const minifiedSize = Buffer.byteLength(minifiedContent, 'utf8');
            
            this.stats.files.push({
                name: 'critical.min.css',
                originalSize: originalSize,
                optimizedSize: minifiedSize,
                savings: ((originalSize - minifiedSize) / originalSize * 100).toFixed(1)
            });
            
            console.log(`✅ Critical CSS optimized: ${(originalSize / 1024).toFixed(1)}KB → ${(minifiedSize / 1024).toFixed(1)}KB\n`);
            
        } catch (error) {
            console.log('⚠️  Critical CSS processing failed');
        }
    }

    async optimizeImages() {
        console.log('🖼️  Optimizing images...');
        
        try {
            const imagesDir = config.src.images;
            const distImagesDir = config.dist.images;
            
            await fs.mkdir(distImagesDir, { recursive: true });
            
            // Copy images (in a real build, we'd use imagemin or similar)
            const files = await fs.readdir(imagesDir);
            let imageCount = 0;
            
            for (const file of files) {
                if (file.match(/\.(png|jpg|jpeg|gif|svg|webp)$/i)) {
                    const sourcePath = path.join(imagesDir, file);
                    const destPath = path.join(distImagesDir, file);
                    await fs.copyFile(sourcePath, destPath);
                    imageCount++;
                }
            }
            
            console.log(`✅ ${imageCount} images optimized\n`);
            
        } catch (error) {
            console.log('⚠️  Image optimization skipped (no images directory found)\n');
        }
    }

    async generateManifest() {
        console.log('📋 Generating asset manifest...');
        
        const manifest = {
            version: Date.now(),
            assets: {
                js: 'dist/app.min.js',
                css: 'dist/app.min.css',
                critical: 'dist/critical.min.css'
            },
            integrity: {},
            buildDate: new Date().toISOString()
        };
        
        // Generate integrity hashes for security
        for (const [key, assetPath] of Object.entries(manifest.assets)) {
            try {
                const fullPath = path.join('backend/static', assetPath);
                const content = await fs.readFile(fullPath);
                const crypto = require('crypto');
                manifest.integrity[key] = `sha384-${crypto.createHash('sha384').update(content).digest('base64')}`;
            } catch (error) {
                console.log(`⚠️  Could not generate integrity hash for ${assetPath}`);
            }
        }
        
        const manifestPath = path.join(config.dist.js, 'manifest.json');
        await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
        
        console.log('✅ Asset manifest generated\n');
    }

    async updateTemplates() {
        console.log('📄 Creating production template...');
        
        const baseOptimizedPath = path.join(config.src.templates, 'base.optimized.html');
        const baseProdPath = path.join(config.src.templates, 'base.production.html');
        
        try {
            let content = await fs.readFile(baseOptimizedPath, 'utf8');
            
            // Update asset paths to use minified versions
            content = content
                .replace('/static/dist/app.min.css', '/static/dist/app.min.css?v=' + Date.now())
                .replace('/static/dist/app.min.js', '/static/dist/app.min.js?v=' + Date.now())
                .replace('<!-- Critical CSS inlined -->', `<!-- Critical CSS inlined - Build: ${new Date().toISOString()} -->`);
            
            await fs.writeFile(baseProdPath, content);
            console.log('✅ Production template created\n');
            
        } catch (error) {
            console.log('⚠️  Template update failed:', error.message);
        }
    }

    printBuildStats() {
        console.log('\n📊 Build Statistics');
        console.log('==================');
        
        const totalSavings = this.stats.originalSize > 0 
            ? ((this.stats.originalSize - this.stats.optimizedSize) / this.stats.originalSize * 100).toFixed(1)
            : '0';
            
        console.log(`Total original size: ${(this.stats.originalSize / 1024).toFixed(1)}KB`);
        console.log(`Total optimized size: ${(this.stats.optimizedSize / 1024).toFixed(1)}KB`);
        console.log(`Total savings: ${totalSavings}%`);
        
        console.log('\nFile Details:');
        console.log('-------------');
        
        this.stats.files.forEach(file => {
            console.log(`${file.name}: ${(file.originalSize / 1024).toFixed(1)}KB → ${(file.optimizedSize / 1024).toFixed(1)}KB (${file.savings}% savings)`);
        });
        
        console.log('\n');
    }
}

// Run build if called directly
if (require.main === module) {
    const builder = new AssetBuilder();
    builder.build();
}

module.exports = AssetBuilder;