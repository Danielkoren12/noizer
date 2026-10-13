'use strict';

// No analytics, cookies, form submission or external requests.
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const sprayArt = document.querySelector('#spray-art');
const skipAnimation = document.querySelector('#skip-animation');
let animationTimer;

function finishSpray() {
  window.clearTimeout(animationTimer);
  sprayArt.classList.remove('spraying');
  skipAnimation.hidden = true;
}

// Session storage means a refresh or return to the page does not replay the intro.
// When storage is unavailable the site still works; only persistence is unavailable.
let hasSeenIntro = false;
try {
  hasSeenIntro = sessionStorage.getItem('noizer:intro-seen') === '1';
  sessionStorage.setItem('noizer:intro-seen', '1');
} catch { /* Private/restricted storage must never block access to content. */ }

if (!hasSeenIntro && !motionPreference.matches) {
  sprayArt.classList.add('spraying');
  skipAnimation.hidden = false;
  animationTimer = window.setTimeout(finishSpray, 3100);
}
skipAnimation.addEventListener('click', () => {
  finishSpray();
  document.querySelector('.hero-actions a').focus({ preventScroll: true });
});
motionPreference.addEventListener('change', (event) => {
  if (event.matches) finishSpray();
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
