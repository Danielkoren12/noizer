'use strict';

// No analytics, cookies, form submission or external requests.
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const sprayArt = document.querySelector('#spray-art');
const skipAnimation = document.querySelector('#skip-animation');
const replayAnimation = document.querySelector('#replay-animation');
const sprayCharacter = document.querySelector('#spray-character');
const paintTrail = document.querySelector('#paint-trail');
const sprayLines = [...document.querySelectorAll('.spray-line')];
const WRITE_MS = 1700;
const RETURN_MS = 450;
const TOTAL_MS = WRITE_MS * 3 + RETURN_MS * 2 + 250;
let characterFrame;
let characterGeometry;
let introRun = 0;
let startedAt;
const soundToggle = document.querySelector('#sound-toggle');
const soundLabel = document.querySelector('#sound-label');
let sprayAudio;
let soundEnabled = false;
let hissPlaying = false;

// A quiet aerosol hiss, synthesized locally. No sound files or network requests.
function createSprayAudio() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const context = new AudioContextClass();
  const noise = context.createBuffer(1, context.sampleRate * 2, context.sampleRate);
  const samples = noise.getChannelData(0);
  for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1;
  const source = context.createBufferSource();
  source.buffer = noise;
  source.loop = true;
  const highpass = context.createBiquadFilter();
  highpass.type = 'highpass';
  highpass.frequency.value = 1400;
  const lowpass = context.createBiquadFilter();
  lowpass.type = 'lowpass';
  lowpass.frequency.value = 8500;
  const gain = context.createGain();
  gain.gain.value = 0;
  source.connect(highpass).connect(lowpass).connect(gain).connect(context.destination);
  source.start();
  return { context, source, gain };
}

function setSprayHiss(writing) {
  const audible = Boolean(writing && soundEnabled && !document.hidden && document.hasFocus() && sprayAudio?.context.state === 'running');
  if (!sprayAudio || audible === hissPlaying) return;
  hissPlaying = audible;
  const now = sprayAudio.context.currentTime;
  const gain = sprayAudio.gain.gain;
  gain.cancelScheduledValues(now);
  gain.setValueAtTime(gain.value, now);
  gain.linearRampToValueAtTime(audible ? 0.12 : 0, now + 0.025);
}

if (window.AudioContext || window.webkitAudioContext) {
  soundToggle.hidden = motionPreference.matches;
  soundToggle.addEventListener('click', async () => {
    soundToggle.disabled = true;
    try {
      if (!soundEnabled) {
        sprayAudio ??= createSprayAudio();
        let timeout;
        try {
          await Promise.race([
            sprayAudio.context.resume(),
            new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error('Audio unavailable')), 1800); })
          ]);
        } finally { clearTimeout(timeout); }
      }
      soundEnabled = !soundEnabled;
      soundToggle.setAttribute('aria-pressed', String(soundEnabled));
      soundLabel.textContent = soundEnabled ? 'צליל ספריי: פועל' : 'צליל ספריי: כבוי';
      if (!soundEnabled) setSprayHiss(false);
      else if (!sprayArt.classList.contains('spraying')) startSpray();
    } catch {
      soundEnabled = false;
      soundToggle.setAttribute('aria-pressed', 'false');
      soundLabel.textContent = 'הצליל לא זמין — נסו שוב';
      setSprayHiss(false);
    } finally { soundToggle.disabled = false; }
  });
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden) setSprayHiss(false);
});
window.addEventListener('blur', () => setSprayHiss(false));
window.addEventListener('pagehide', () => setSprayHiss(false));

function measureCharacterPath() {
  const wall = document.querySelector('.spray-wall');
  const style = getComputedStyle(wall);
  const matrix = new DOMMatrix(style.transform);
  const [originX, originY] = style.transformOrigin.split(' ').map(parseFloat);
  characterGeometry = {
    width: sprayCharacter.clientWidth,
    height: sprayCharacter.clientHeight,
    maxX: sprayArt.clientWidth - sprayCharacter.clientWidth,
    maxY: sprayArt.clientHeight - sprayCharacter.clientHeight,
    restX: sprayArt.clientWidth - sprayCharacter.clientWidth - parseFloat(getComputedStyle(sprayCharacter).getPropertyValue("--kid-rest-right")),
    restY: sprayArt.clientHeight - sprayCharacter.clientHeight - parseFloat(getComputedStyle(sprayCharacter).getPropertyValue("--kid-rest-bottom")),
    lines: sprayLines.map((line) => {
      const point = (x) => {
        const result = new DOMPoint(line.offsetLeft + x - originX,
          line.offsetTop + line.clientHeight * 0.74 - originY).matrixTransform(matrix);
        return { x: wall.offsetLeft + originX + result.x, y: wall.offsetTop + originY + result.y };
      };
      return { start: point(0), end: point(line.clientWidth) };
    })
  };
}

const mixPoint = (from, to, amount) => ({
  x: from.x + (to.x - from.x) * amount,
  y: from.y + (to.y - from.y) * amount
});

// One clock draws the letters, moves the boy and places the spray endpoint.
// The return journey is real movement; the next line stays unpainted until arrival.
function moveSprayCharacter(now) {
  if (!sprayArt.classList.contains('spraying')) return;
  startedAt ??= now;
  const elapsed = now - startedAt;
  const row = Math.min(2, Math.floor(elapsed / (WRITE_MS + RETURN_MS)));
  const localTime = elapsed - row * (WRITE_MS + RETURN_MS);
  const progress = Math.min(1, localTime / WRITE_MS);
  const returning = localTime >= WRITE_MS;
  sprayLines.forEach((line, index) => {
    const amount = index < row ? 1 : index === row ? progress : 0;
    line.style.clipPath = `inset(-5% ${(1 - amount) * 100}% -5% -5%)`;
  });
  const line = characterGeometry.lines[row];
  let target = mixPoint(line.start, line.end, progress);
  if (returning) {
    const fraction = Math.min(1, (localTime - WRITE_MS) / (row < 2 ? RETURN_MS : 250));
    const smooth = fraction * fraction * (3 - 2 * fraction);
    const destination = row < 2 ? characterGeometry.lines[row + 1].start : {
      x: characterGeometry.restX + characterGeometry.width * 0.75,
      y: characterGeometry.restY + characterGeometry.height * (25 / 280) - 18
    };
    target = mixPoint(line.end, destination, smooth);
  }
  const nozzleOffsetX = characterGeometry.width * 0.75;
  const nozzleOffsetY = characterGeometry.height * (25 / 280);
  const x = Math.min(characterGeometry.maxX, Math.max(0, target.x - nozzleOffsetX));
  const y = Math.min(characterGeometry.maxY, Math.max(0, target.y + 18 - nozzleOffsetY));
  sprayCharacter.style.transform = `translate(${x}px, ${y}px)`;
  sprayCharacter.classList.toggle('is-walking', localTime < WRITE_MS || returning);
  paintTrail.setAttribute('d', `M${x + nozzleOffsetX} ${y + nozzleOffsetY} L${target.x} ${target.y}`);
  paintTrail.style.opacity = !returning && localTime < WRITE_MS ? '0.7' : '0';
  setSprayHiss(!returning && localTime < WRITE_MS);
  if (elapsed >= TOTAL_MS) {
    finishSpray();
    return;
  }
  characterFrame = requestAnimationFrame(moveSprayCharacter);
}

async function startSpray() {
  if (motionPreference.matches) return;
  const run = ++introRun;
  skipAnimation.hidden = false;
  replayAnimation.hidden = true;
  // Measure the actual loaded letterforms so no font swap shifts the paint path.
  await document.fonts.ready;
  if (run !== introRun || motionPreference.matches) return;
  sprayArt.classList.add('spraying');
  startedAt = undefined;
  measureCharacterPath();
  characterFrame = requestAnimationFrame(moveSprayCharacter);
}

function finishSpray() {
  setSprayHiss(false);
  introRun++;
  cancelAnimationFrame(characterFrame);
  sprayArt.classList.remove('spraying');
  sprayCharacter.classList.remove('is-walking');
  sprayCharacter.style.transform = '';
  sprayLines.forEach((line) => { line.style.clipPath = ''; });
  paintTrail.style.opacity = '0';
  skipAnimation.hidden = true;
  replayAnimation.hidden = motionPreference.matches;
}

// Session storage means a refresh or return to the page does not replay the intro.
// When storage is unavailable the site still works; only persistence is unavailable.
let hasSeenIntro = false;
try {
  hasSeenIntro = sessionStorage.getItem('noizer:intro-seen') === '1';
  sessionStorage.setItem('noizer:intro-seen', '1');
} catch { /* Private/restricted storage must never block access to content. */ }

if (!hasSeenIntro && !motionPreference.matches) {
  startSpray();
} else {
  replayAnimation.hidden = motionPreference.matches;
}
replayAnimation.addEventListener('click', () => {
  startSpray();
  skipAnimation.focus({ preventScroll: true });
});
window.addEventListener('resize', () => {
  if (sprayArt.classList.contains('spraying')) measureCharacterPath();
});
document.fonts.ready.then(() => {
  if (sprayArt.classList.contains('spraying')) measureCharacterPath();
});
skipAnimation.addEventListener('click', () => {
  finishSpray();
  document.querySelector('.hero-actions a').focus({ preventScroll: true });
});
motionPreference.addEventListener('change', (event) => {
  if (event.matches) finishSpray();
  replayAnimation.hidden = event.matches;
  soundToggle.hidden = event.matches || !(window.AudioContext || window.webkitAudioContext);
});

// A working before/after demonstration without pretending the stills are videos.
const bannerToggle = document.querySelector('#banner-toggle');
const examples = document.querySelector('#examples');
bannerToggle.hidden = false;
bannerToggle.addEventListener('click', () => {
  const visible = bannerToggle.getAttribute('aria-pressed') !== 'true';
  bannerToggle.setAttribute('aria-pressed', String(visible));
  examples.classList.toggle('no-banners', !visible);
  document.querySelector('#toggle-label').textContent = visible ? 'הסתירו את הבאנר' : 'הציגו את הבאנר';
  document.querySelector('#toggle-status').textContent = visible ? 'הבאנר מוצג בהדמיות' : 'התוכן מוצג ללא הבאנר';
  examples.querySelectorAll('.mock-banner').forEach((banner) => {
    banner.setAttribute('aria-hidden', String(!visible));
  });
});

const email = 'daniel@korenf.com';
const contactRoutes = {
  brands: { subject: 'NOIZER — פנייה ממותג או משרד פרסום', body: 'היי NOIZER,\nנרצה לשמוע על קמפיין באנרים.\n\nשם המותג / המשרד:\nשם איש / אשת הקשר:\nקצת על הקמפיין:\n' },
  creators: { subject: 'NOIZER — הצטרפות יוצר/ת תוכן', body: 'היי NOIZER,\nנרצה להצטרף לבית היוצרים.\n\nשם:\nקישור לפרופיל Instagram / YouTube:\nקצת על התוכן שלנו:\n' }
};
document.querySelectorAll('[data-contact]').forEach((link) => {
  const route = contactRoutes[link.dataset.contact];
  link.href = `mailto:${email}?subject=${encodeURIComponent(route.subject)}&body=${encodeURIComponent(route.body)}`;
});

const copyButton = document.querySelector('#copy-email');
if (navigator.clipboard?.writeText) {
  copyButton.hidden = false;
  copyButton.addEventListener('click', async () => {
    const status = document.querySelector('#copy-status');
    try {
      await navigator.clipboard.writeText(email);
      status.textContent = 'כתובת הדוא״ל הועתקה';
    } catch {
      status.textContent = 'לא ניתן להעתיק אוטומטית. אפשר לסמן ולהעתיק את הכתובת.';
    }
  });
}

// Content is always visible. Observers only add a small one-time settling motion.
if ('IntersectionObserver' in window && !motionPreference.matches) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('arriving');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.18 });
  document.querySelectorAll('.how-heading, .contact-heading').forEach((heading) => observer.observe(heading));
}
document.querySelector('#year').textContent = String(new Date().getFullYear());
