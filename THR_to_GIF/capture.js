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
const outputGif = process.argv[3] || "output.gif";
const duration = parseFloat(process.argv[4] || 10); // seconds
const fps = DEFAULT_FPS;
const totalFrames = Math.ceil(duration * fps);

// File paths
const tempDir = './frames';
const palette = 'palette.png';

// Validate inputs
if (!htmlPath) {
    console.error("Usage: node capture.js input.html output.gif duration_seconds");
    process.exit(1);
}

if (duration <= 0) {
    console.error("Duration must be positive");
    process.exit(1);
}

if (duration > 43200) { // 12 hours
    console.warn("Warning: Duration exceeds 12 hours, this may cause performance issues");
}

function updateProgress(current, total) {
    const percent = Math.round((current / total) * 100);
    const width = 30;
    const filled = Math.round((percent / 100) * width);
    const bar = '█'.repeat(filled) + '-'.repeat(width - filled);
    process.stdout.write(`\r[${bar}] ${percent}%`);
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
        await delay(1000);

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

        await delay(200);

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
        if (fs.existsSync(tempDir)) {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
        if (fs.existsSync(palette)) {
            fs.rmSync(palette, { force: true });
        }
    } catch (error) {
        console.error(`Error during cleanup: ${error.message}`);
    }
}

async function main() {
    let browser;
    try {
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir);
        }

        const htmlFile = `file://${path.resolve(htmlPath)}`;
        browser = await puppeteer.launch({
            headless: true,
            protocolTimeout: 300000
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

        let completed = 0;
        for (let i = 0; i < totalFrames; i++) {
            await captureWithRetry(page, i);
            completed++;
            updateProgress(completed, totalFrames);
        }

        await page.close();
        await browser.close();
        browser = null;

        console.log('\n✅ Capture complete.');
        fillMissingFrames();

        console.log('🎨 Generating palette...');
        const paletteCmd = `ffmpeg -y -i ${quotePath(tempDir + '/frame_%04d.png')} -vf palettegen ${quotePath(palette)}`;
        await new Promise((resolve, reject) => {
            exec(paletteCmd, (err) => {
                if (err) {
                    reject(new Error(`Error generating palette: ${err.message}`));
                } else {
                    resolve();
                }
            });
        });

        console.log('🌀 Creating GIF...');
        const gifCmd = `ffmpeg -y -framerate ${fps} -i ${quotePath(tempDir + '/frame_%04d.png')} -i ${quotePath(palette)} -lavfi "paletteuse=dither=bayer" ${quotePath(outputGif)}`;
        await new Promise((resolve, reject) => {
            exec(gifCmd, async (err) => {
                if (err) {
                    reject(new Error(`Error creating GIF: ${err.message}`));
                } else {
                    console.log(`✅ GIF created at ${outputGif}`);
                    await cleanup();

                    // Generate PNG preview from frame 1 (time 0)
                    const baseName = path.basename(outputGif, '.gif');
                    const outputDir = path.dirname(outputGif);
                    const pngPath = path.join(outputDir, `${baseName}.png`);
                    await capturePreviewImage(htmlPath, pngPath, 0);
                    resolve();
                }
            });
        });
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    } finally {
        if (browser) {
            await browser.close();
        }
        await cleanup();
    }
}

main().catch(error => {
    console.error(`Fatal error: ${error.message}`);
    process.exit(1);
});