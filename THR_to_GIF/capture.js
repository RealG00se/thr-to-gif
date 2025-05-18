const puppeteer = require('puppeteer');
const fs = require('fs');
const { exec } = require('child_process');
const path = require('path');
const { createCanvas } = require('canvas');

const htmlPath = process.argv[2];
const outputGif = process.argv[3] || "output.gif";
const duration = parseFloat(process.argv[4] || 10); // seconds
const fps = 30;
const totalFrames = Math.ceil(duration * fps);

const tempDir = './frames';
const palette = 'palette.png';

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
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'black';
  ctx.fillRect(0, 0, width, height);
  fs.writeFileSync(filePath, canvas.toBuffer('image/png'));
  console.log(`🩹 Created blank fallback frame at ${filePath}`);
}

function fillMissingFrames() {
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
}

async function captureFrame(page, frameIndex) {
  const time = frameIndex / fps;

  await page.evaluate((t) => {
    const svg = document.querySelector('svg');
    svg.setCurrentTime(t);
    svg.style.visibility = 'hidden';
    void svg.offsetHeight;
    svg.style.visibility = 'visible';
  }, time);

  const delay =
    frameIndex <= 1 ? 300 :
    frameIndex > totalFrames * 0.9 ? 100 : 20;

  await new Promise(resolve => setTimeout(resolve, delay));

  const clip = await page.evaluate(() => {
    const svg = document.querySelector('svg');
    const rect = svg.getBoundingClientRect();
    return { x: rect.left, y: rect.top, width: rect.width, height: rect.height };
  });

  const filePath = `${tempDir}/frame_${String(frameIndex).padStart(4, '0')}.png`;
  await page.screenshot({ path: filePath, clip });
}

async function captureWithRetry(page, frameIndex, retries = 3) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      await Promise.race([
        captureFrame(page, frameIndex),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Timeout')), 20000)
        )
      ]);
      return true;
    } catch (err) {
      if (attempt === retries) {
        console.error(`❌ Frame ${frameIndex} failed after ${retries + 1} attempts: ${err.message}`);
        return false;
      } else {
        console.warn(`⚠️  Retry ${attempt + 1} for frame ${frameIndex}...`);
      }
    }
  }
}

(async () => {
  if (!htmlPath) {
    console.error("Usage: node capture.js input.html output.gif duration_seconds");
    process.exit(1);
  }

  if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir);

  const htmlFile = `file://${path.resolve(htmlPath)}`;
  const browser = await puppeteer.launch({
    headless: true,
    protocolTimeout: 300000
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1000, height: 1000 });
  await page.goto(htmlFile, { waitUntil: 'networkidle2' });

  await page.waitForFunction(() => {
    const svg = document.querySelector('svg');
    return svg && typeof svg.setCurrentTime === 'function';
  }, { timeout: 10000 });

  let completed = 0;
  for (let i = 0; i < totalFrames; i++) {
    await captureWithRetry(page, i);
    completed++;
    updateProgress(completed, totalFrames);
  }

  await page.close();
  await browser.close();

  console.log('\n✅ Capture complete.');
  fillMissingFrames();

  console.log('🎨 Generating palette...');
  const paletteCmd = `ffmpeg -y -i ${quotePath(tempDir + '/frame_%04d.png')} -vf palettegen ${quotePath(palette)}`;
  exec(paletteCmd, (err1) => {
    if (err1) {
      console.error("❌ Error generating palette:", err1);
      process.exit(1);
    }

    console.log('🌀 Creating GIF...');
    const gifCmd = `ffmpeg -y -framerate ${fps} -i ${quotePath(tempDir + '/frame_%04d.png')} -i ${quotePath(palette)} -lavfi "paletteuse=dither=bayer" ${quotePath(outputGif)}`;
    exec(gifCmd, (err2) => {
      if (err2) {
        console.error("❌ Error creating GIF:", err2);
        process.exit(1);
      } else {
        console.log(`✅ GIF created at ${outputGif}`);
        fs.rmSync(tempDir, { recursive: true, force: true });
        fs.rmSync(palette, { force: true });
      }
    });
  });
})();