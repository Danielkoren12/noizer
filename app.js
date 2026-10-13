'use strict';

// No analytics, cookies, form submission or external requests.
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const sprayArt = document.querySelector('#spray-art');
const skipAnimation = document.querySelector('#skip-animation');
const replayAnimation = document.querySelector('#replay-animation');
const sprayCharacter = document.querySelector('#spray-character');
const paintTrail = document.querySelector('#paint-trail');
let animationTimer;
let characterFrame;
let characterGeometry;

// Follow the existing CSS text reveal; its wording, timing and easing are unchanged.
function measureCharacterPath() {
  const wall = document.querySelector('.spray-wall');
  const style = getComputedStyle(wall);
  const matrix = new DOMMatrix(style.transform);
  const [originX, originY] = style.transformOrigin.split(' ').map(parseFloat);
  const width = sprayCharacter.clientWidth;
  const height = sprayCharacter.clientHeight;
  characterGeometry = {
    width, height,
    maxX: sprayArt.clientWidth - width,
    maxY: sprayArt.clientHeight - height,
    lines: [...wall.querySelectorAll('.spray-line')].map((line) => {
      const point = (x) => {
        const result = new DOMPoint(line.offsetLeft + x - originX,
          line.offsetTop + line.clientHeight * 0.74 - originY).matrixTransform(matrix);
        return { x: wall.offsetLeft + originX + result.x, y: wall.offsetTop + originY + result.y };
      };
      return { start: point(0), end: point(line.clientWidth) };
    })
  };
}

function moveSprayCharacter() {
  if (!sprayArt.classList.contains('spraying')) return;
  // CSS animations are the clock, so the illustrator follows the real paint edge.
  const animation = document.querySelector('.spray-first').getAnimations()[0];
  const elapsed = animation?.currentTime ?? 0;
  const row = Math.min(2, Math.floor(elapsed / 950));
  const rowTime = elapsed - row * 950;
  const progress = Math.min(1, Math.max(0, rowTime / 850));
  const { start, end } = characterGeometry.lines[row];
  const targetX = start.x + (end.x - start.x) * progress;
  const targetY = start.y + (end.y - start.y) * progress;
  const x = Math.min(characterGeometry.maxX, Math.max(0, targetX - 18));
  const y = Math.min(characterGeometry.maxY, Math.max(0, targetY + 12));
  sprayCharacter.style.transform = `translate(${x}px, ${y}px)`;
  const nozzleX = x + characterGeometry.width * 0.12;
  const nozzleY = y + characterGeometry.height * 0.11;
  paintTrail.setAttribute('d', `M${nozzleX} ${nozzleY} Q${targetX - 12} ${targetY + 10} ${targetX} ${targetY}`);
  paintTrail.style.opacity = rowTime < 850 ? '0.65' : '0';
  characterFrame = requestAnimationFrame(moveSprayCharacter);
}

function startSpray() {
  if (motionPreference.matches) return;
  sprayArt.classList.add('spraying');
  skipAnimation.hidden = false;
  replayAnimation.hidden = true;
  measureCharacterPath();
  characterFrame = requestAnimationFrame(moveSprayCharacter);
  animationTimer = window.setTimeout(finishSpray, 3100);
}

function finishSpray() {
  window.clearTimeout(animationTimer);
  cancelAnimationFrame(characterFrame);
  sprayArt.classList.remove('spraying');
  sprayCharacter.style.transform = '';
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
