const puppeteer = require('puppeteer');
const fs = require('fs');
const { exec } = require('child_process');
const path = require('path');
const { createCanvas } = require('canvas');

// Configuration
const DEFAULT_FPS = 30;
const MAX_RETRIES = 3;
const TIMEOUT_MS = 20000;
const MAX_CANVAS_SIZE = 4096;

// Helper function for delay
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

// Command line arguments
const htmlPath = process.argv[2];
const outputGif = process.argv[3];
const duration = parseFloat(process.argv[4] || 10); // seconds
const noPngFlag = process.argv[5] === '--no-png'; // Check for --no-png flag
const fps = DEFAULT_FPS;
const totalFrames = Math.ceil(duration * fps);

// File paths
const tempDir = './frames';
const palette = 'palette.png';

// Validate inputs
if (!htmlPath) {
    console.error("Usage: node capture.js input.html [output.gif|NO_GIF] duration_seconds [--no-png]");
    process.exit(1);
}

if (duration <= 0) {
    console.error("Duration must be positive");
    process.exit(1);
}

if (duration > 43200) { // 12 hours
    console.warn("Warning: Duration exceeds 12 hours, this may cause performance issues");
}

// Check if we should generate GIF
const shouldGenerateGif = outputGif && outputGif !== 'NO_GIF' && outputGif !== 'undefined' && outputGif !== 'null';

// Add debug logging (only in development - comment out for production)
// console.error(`\n🔍 CAPTURE.JS DEBUG:
// - outputGif: "${outputGif}"
// - shouldGenerateGif: ${shouldGenerateGif}
// - noPngFlag: ${noPngFlag}
// - Command line args: ${process.argv.join(' ')}
// `);

function updateProgress(current, total) {
    const percent = Math.round((current / total) * 100);
    const width = 40;  // Make progress bar wider
    const filled = Math.round((percent / 100) * width);
    const bar = '█'.repeat(filled) + '░'.repeat(width - filled);
    process.stdout.write(`\r📹 Capturing frames: [${bar}] ${percent}% (${current}/${total})`);
    
    // Clear the line and show completion when done
    if (current === total) {
        process.stdout.write('\n');
    }
}

function quotePath(p) {
    return `"${p.replace(/"/g, '\\"')}"`;
}

function createBlankFrame(filePath, width = 1000, height = 1000) {
    try {
        const canvas = createCanvas(width, height);
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'black';
        ctx.fillRect(0, 0, width, height);
        fs.writeFileSync(filePath, canvas.toBuffer('image/png'));
        console.log(`🩹 Created blank fallback frame at ${filePath}`);
    } catch (error) {
        console.error(`Error creating blank frame: ${error.message}`);
        throw error;
    }
}

function fillMissingFrames() {
    try {
        const firstFramePath = `${tempDir}/frame_0000.png`;
        if (!fs.existsSync(firstFramePath)) {
            const secondFramePath = `${tempDir}/frame_0001.png`;
            if (fs.existsSync(secondFramePath)) {
                fs.copyFileSync(secondFramePath, firstFramePath);
                console.log(`🩹 Missing first frame 0000 fixed by copying frame 0001`);
            } else {
                createBlankFrame(firstFramePath);
            }
        }

        for (let i = 0; i < totalFrames; i++) {
            const framePath = `${tempDir}/frame_${String(i).padStart(4, '0')}.png`;
            if (!fs.existsSync(framePath)) {
                let j = i - 1;
                while (j >= 0 && !fs.existsSync(`${tempDir}/frame_${String(j).padStart(4, '0')}.png`)) {
                    j--;
                }
                if (j >= 0) {
                    fs.copyFileSync(`${tempDir}/frame_${String(j).padStart(4, '0')}.png`, framePath);
                    console.log(`🩹 Filled missing frame ${i} by copying frame ${j}`);
                } else {
                    createBlankFrame(framePath);
                }
            }
        }
    } catch (error) {
        console.error(`Error filling missing frames: ${error.message}`);
        throw error;
    }
}

async function captureFrame(page, frameIndex) {
    const time = frameIndex / fps;

    try {
        await page.evaluate((t) => {
            const path = document.getElementById('animatedPath');
            if (!path) {
                throw new Error('Animated path element not found');
            }
            const hoursInput = document.getElementById('hours');
            const minutesInput = document.getElementById('minutes');
            const secondsInput = document.getElementById('seconds');
            if (!hoursInput || !minutesInput || !secondsInput) {
                throw new Error('Time input elements not found');
            }
            const hours = parseInt(hoursInput.value) || 0;
            const minutes = parseInt(minutesInput.value) || 0;
            const seconds = parseInt(secondsInput.value) || 0;
            const duration = hours * 3600 + minutes * 60 + seconds;
            const pathLength = parseFloat(path.getAttribute('stroke-dasharray'));
            const offset = pathLength * (1 - t / duration);
            path.setAttribute('stroke-dashoffset', offset);
        }, time);

        const delay = frameIndex <= 1 ? 300 :
                     frameIndex > totalFrames * 0.9 ? 100 : 20;

        await new Promise(resolve => setTimeout(resolve, delay));

        const clip = await page.evaluate(() => {
            const svg = document.querySelector('svg');
            if (!svg) {
                throw new Error('SVG element not found');
            }
            const rect = svg.getBoundingClientRect();
            // Since the SVG is rotated, we need to swap width and height
            return { 
                x: rect.left, 
                y: rect.top, 
                width: rect.height, 
                height: rect.width 
            };
        });

        const filePath = `${tempDir}/frame_${String(frameIndex).padStart(4, '0')}.png`;
        await page.screenshot({ path: filePath, clip });
    } catch (error) {
        console.error(`Error capturing frame ${frameIndex}: ${error.message}`);
        throw error;
    }
}

async function captureWithRetry(page, frameIndex, retries = MAX_RETRIES) {
    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            await Promise.race([
                captureFrame(page, frameIndex),
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('Timeout')), TIMEOUT_MS)
                )
            ]);
            return true;
        } catch (err) {
            if (attempt === retries) {
                console.error(`❌ Frame ${frameIndex} failed after ${retries + 1} attempts: ${err.message}`);
                return false;
            } else {
                console.warn(`⚠️  Retry ${attempt + 1} for frame ${frameIndex}...`);
                await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1))); // Exponential backoff
            }
        }
    }
}

async function capturePreviewImageOptimized(page, outputPngPath, finalTime) {
    try {
        // Reset the animation to the desired time
        await page.evaluate((t) => {
            const path = document.getElementById('animatedPath');
            if (!path) {
                throw new Error('Animated path element not found');
            }
            const hoursInput = document.getElementById('hours');
            const minutesInput = document.getElementById('minutes');
            const secondsInput = document.getElementById('seconds');
            if (!hoursInput || !minutesInput || !secondsInput) {
                throw new Error('Time input elements not found');
            }
            const hours = parseInt(hoursInput.value) || 0;
            const minutes = parseInt(minutesInput.value) || 0;
            const seconds = parseInt(secondsInput.value) || 0;
            const duration = hours * 3600 + minutes * 60 + seconds;
            const pathLength = parseFloat(path.getAttribute('stroke-dasharray'));
            const offset = pathLength * (1 - t / duration);
            path.setAttribute('stroke-dashoffset', offset);
        }, finalTime);

        // Small delay to ensure rendering
        await delay(100);

        const clip = await page.evaluate(() => {
            const svg = document.querySelector('svg');
            if (!svg) {
                throw new Error('SVG element not found');
            }
            const rect = svg.getBoundingClientRect();
            return { 
                x: rect.left, 
                y: rect.top, 
                width: rect.height, 
                height: rect.width 
            };
        });

        await page.screenshot({ path: outputPngPath, clip });
        console.log(`🖼️  PNG preview saved: ${outputPngPath}`);
    } catch (error) {
        console.error(`Error capturing optimized preview image: ${error.message}`);
        throw error;
    }
}

async function capturePreviewImage(htmlPath, outputPngPath, finalTime) {
    let browser;
    try {
        browser = await puppeteer.launch({ headless: true });
        const page = await browser.newPage();
        await page.setViewport({ width: 1000, height: 1000 });
        
        // Navigate to the page and wait for it to be fully loaded
        await page.goto(`file://${path.resolve(htmlPath)}`, { 
            waitUntil: ['networkidle0', 'domcontentloaded'],
            timeout: 30000 
        });

        // Wait for the SVG and animated path to be ready
        await page.waitForFunction(() => {
            const svg = document.querySelector('svg');
            const path = document.getElementById('animatedPath');
            const hoursInput = document.getElementById('hours');
            const minutesInput = document.getElementById('minutes');
            const secondsInput = document.getElementById('seconds');
            return svg && path && hoursInput && minutesInput && secondsInput && 
                   path.getAttribute('stroke-dasharray') && 
                   path.getAttribute('stroke-dashoffset');
        }, { timeout: TIMEOUT_MS });

        // Additional wait to ensure everything is initialized
        await delay(500);

        await page.evaluate((t) => {
            const path = document.getElementById('animatedPath');
            if (!path) {
                throw new Error('Animated path element not found');
            }
            const hoursInput = document.getElementById('hours');
            const minutesInput = document.getElementById('minutes');
            const secondsInput = document.getElementById('seconds');
            if (!hoursInput || !minutesInput || !secondsInput) {
                throw new Error('Time input elements not found');
            }
            const hours = parseInt(hoursInput.value) || 0;
            const minutes = parseInt(minutesInput.value) || 0;
            const seconds = parseInt(secondsInput.value) || 0;
            const duration = hours * 3600 + minutes * 60 + seconds;
            const pathLength = parseFloat(path.getAttribute('stroke-dasharray'));
            const offset = pathLength * (1 - t / duration);
            path.setAttribute('stroke-dashoffset', offset);
        }, finalTime);

        await delay(100);

        const clip = await page.evaluate(() => {
            const svg = document.querySelector('svg');
            if (!svg) {
                throw new Error('SVG element not found');
            }
            const rect = svg.getBoundingClientRect();
            // Since the SVG is rotated, we need to swap width and height
            return { 
                x: rect.left, 
                y: rect.top, 
                width: rect.height, 
                height: rect.width 
            };
        });

        await page.screenshot({ path: outputPngPath, clip });
        console.log(`🖼️  PNG preview saved: ${outputPngPath}`);
    } catch (error) {
        console.error(`Error capturing preview image: ${error.message}`);
        throw error;
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

async function cleanup() {
    try {
        // Clean up frames directory
        if (fs.existsSync(tempDir)) {
            console.log('🧹 Cleaning up temporary frames...');
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
        // Clean up palette file
        if (fs.existsSync(palette)) {
            fs.rmSync(palette, { force: true });
        }
        // Clean up any stray frame directories
        const parentDir = path.dirname(tempDir);
        const dirs = fs.readdirSync(parentDir);
        for (const dir of dirs) {
            const fullPath = path.join(parentDir, dir);
            if (fs.statSync(fullPath).isDirectory() && dir.startsWith('frames_')) {
                console.log(`🧹 Cleaning up stray frames directory: ${dir}`);
                fs.rmSync(fullPath, { recursive: true, force: true });
            }
        }
    } catch (error) {
        console.error(`Error during cleanup: ${error.message}`);
        // Don't throw the error, just log it
    }
}

// Add cleanup on process exit
process.on('exit', () => {
    // This runs synchronously, so we can't use async/await
    try {
        if (fs.existsSync(tempDir)) {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
        if (fs.existsSync(palette)) {
            fs.rmSync(palette, { force: true });
        }
    } catch (error) {
        console.error(`Error during exit cleanup: ${error.message}`);
    }
});

// Add cleanup on process termination
process.on('SIGINT', async () => {
    console.log('\n🧹 Cleaning up before exit...');
    await cleanup();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n🧹 Cleaning up before exit...');
    await cleanup();
    process.exit(0);
});

async function main() {
    let browser;
    try {
        const htmlFile = `file://${path.resolve(htmlPath)}`;
        browser = await puppeteer.launch({
            headless: true,
            protocolTimeout: 300000,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'] // Faster startup/shutdown
        });

        const page = await browser.newPage();
        await page.setViewport({ width: 1000, height: 1000 });
        
        // Navigate to the page and wait for it to be fully loaded
        await page.goto(htmlFile, { 
            waitUntil: ['networkidle0', 'domcontentloaded'],
            timeout: 30000 
        });

        // Wait for the SVG and animated path to be ready
        await page.waitForFunction(() => {
            const svg = document.querySelector('svg');
            const path = document.getElementById('animatedPath');
            const hoursInput = document.getElementById('hours');
            const minutesInput = document.getElementById('minutes');
            const secondsInput = document.getElementById('seconds');
            return svg && path && hoursInput && minutesInput && secondsInput && 
                   path.getAttribute('stroke-dasharray') && 
                   path.getAttribute('stroke-dashoffset');
        }, { timeout: TIMEOUT_MS });

        // Additional wait to ensure everything is initialized
        await delay(1000);

        if (shouldGenerateGif) {
            // console.error('\n🔍 CAPTURE.JS: Generating GIF - capturing all frames...');
            console.log(`🎬 Starting GIF generation (${totalFrames} frames at ${fps} FPS)`);
            
            // Create frames directory for GIF generation
            if (!fs.existsSync(tempDir)) {
                fs.mkdirSync(tempDir);
            }

            console.log('📹 Phase 1/4: Capturing animation frames...');
            let completed = 0;
            for (let i = 0; i < totalFrames; i++) {
                await captureWithRetry(page, i);
                completed++;
                updateProgress(completed, totalFrames);
            }

            console.log('✅ Frame capture complete.');
            
            console.log('🔧 Phase 2/4: Processing frames...');
            fillMissingFrames();

            console.log('🎨 Phase 3/4: Generating color palette...');
            const paletteCmd = `ffmpeg -y -i ${quotePath(tempDir + '/frame_%04d.png')} -vf palettegen ${quotePath(palette)} -loglevel error`;
            await new Promise((resolve, reject) => {
                exec(paletteCmd, (err) => {
                    if (err) {
                        reject(new Error(`Error generating palette: ${err.message}`));
                    } else {
                        console.log('✅ Palette generated successfully');
                        resolve();
                    }
                });
            });

            console.log('🌀 Phase 4/4: Creating final GIF...');
            const gifStartTime = Date.now();
            const gifCmd = `ffmpeg -y -framerate ${fps} -i ${quotePath(tempDir + '/frame_%04d.png')} -i ${quotePath(palette)} -lavfi "paletteuse=dither=bayer" ${quotePath(outputGif)} -loglevel error`;
            await new Promise((resolve, reject) => {
                exec(gifCmd, async (err) => {
                    if (err) {
                        reject(new Error(`Error creating GIF: ${err.message}`));
                    } else {
                        const gifTime = ((Date.now() - gifStartTime) / 1000).toFixed(1);
                        console.log(`✅ GIF created successfully in ${gifTime}s: ${outputGif}`);
                        
                        console.log('🧹 Cleaning up temporary files...');
                        const cleanupStartTime = Date.now();
                        await cleanup();
                        const cleanupTime = ((Date.now() - cleanupStartTime) / 1000).toFixed(1);
                        console.log(`✅ Cleanup completed in ${cleanupTime}s`);

                        // Generate PNG preview using existing page for better performance
                        if (!noPngFlag) {
                            const baseName = path.basename(outputGif, '.gif');
                            const outputDir = path.dirname(outputGif);
                            const pngPath = path.join(outputDir, `${baseName}.png`);
                            console.log('📸 Creating PNG preview...');
                            const pngStartTime = Date.now();
                            await capturePreviewImageOptimized(page, pngPath, 0);
                            const pngTime = ((Date.now() - pngStartTime) / 1000).toFixed(1);
                            console.log(`✅ PNG preview created in ${pngTime}s: ${pngPath}`);
                        } else {
                            console.log('🚫 PNG preview skipped (--no-png flag)');
                        }
                        resolve();
                    }
                });
            });

            // Force close browser immediately after completion
            try {
                await page.close();
                await browser.close();
                browser = null;
                console.log('✅ Process completed successfully');
            } catch (closeError) {
                // Ignore browser close errors, just exit
            }
        } else {
            // console.error('\n🔍 CAPTURE.JS: PNG-only mode - skipping frame capture');
            console.log('📸 Creating PNG preview...');
            // If no GIF requested, just generate the PNG preview directly
            const baseName = path.basename(htmlPath, '.html');
            const outputDir = path.dirname(htmlPath);
            const pngPath = path.join(outputDir, `${baseName}.png`);
            await capturePreviewImage(htmlPath, pngPath, 0);
            
            try {
                await page.close();
                await browser.close();
                browser = null;
            } catch (closeError) {
                // Ignore browser close errors
            }
            
            console.log(`✅ PNG preview created: ${pngPath}`);
        }
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    } finally {
        // Quick cleanup without awaiting - let the OS handle it
        if (browser) {
            browser.close().catch(() => {}); // Don't await, just fire and forget
        }
        // Don't do cleanup here - already done in main flow
        // Immediate exit
        process.exit(0);
    }
}

main().catch(error => {
    console.error(`Fatal error: ${error.message}`);
    process.exit(1);
});