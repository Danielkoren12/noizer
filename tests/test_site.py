"""Browser regression checks for the first NOIZER page. Uses installed Playwright."""
import json
import unittest
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from playwright.sync_api import sync_playwright


URL = 'http://127.0.0.1:4173/'


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path='/usr/bin/chromium', args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def page(self, **options):
        context = self.browser.new_context(**options)
        self.addCleanup(context.close)
        return context.new_page()

    def test_visible_business_content_and_metadata_without_javascript(self):
        page = self.page(java_script_enabled=False)
        self.assertEqual(page.goto(URL).status, 200)
        self.assertEqual(page.locator('html').get_attribute('lang'), 'he')
        self.assertEqual(page.locator('html').get_attribute('dir'), 'rtl')
        self.assertEqual(page.locator('h1').count(), 1)
        self.assertEqual(page.locator('main > section').count(), 4)
        self.assertIn('YouTube Shorts', page.locator('.hero-description').inner_text())
        self.assertIn('תשלום לפי צפיות', page.locator('.hero-description').inner_text())
        self.assertIn('NOIZER', page.title())
        data = json.loads(page.locator('script[type="application/ld+json"]').inner_text())
        self.assertEqual(data['@graph'][0]['email'], 'daniel@korenf.com')
        self.assertTrue(page.locator('.spray-third').is_visible())
        self.assertFalse(page.locator('#skip-animation').is_visible())
        self.assertFalse(page.locator('#banner-toggle').is_visible())
        for link in page.locator('a[href^="#"]').all():
            target = link.get_attribute('href')
            if target != '#':
                self.assertEqual(page.locator(target).count(), 1)

    def test_search_metadata_sitemap_and_crawl_access(self):
        page = self.page(java_script_enabled=False)
        page.goto(URL)
        canonical = 'https://noizer.co.il/'
        self.assertEqual(page.locator('link[rel="canonical"]').get_attribute('href'), canonical)
        self.assertEqual(page.locator('meta[property="og:url"]').get_attribute('content'), canonical)
        self.assertIn('index', page.locator('meta[name="robots"]').get_attribute('content'))
        data = json.loads(page.locator('script[type="application/ld+json"]').inner_text())
        entities = {entry['@type']: entry for entry in data['@graph']}
        self.assertEqual(set(entities), {'Organization', 'Service', 'WebSite'})
        self.assertEqual(entities['Service']['provider']['@id'], entities['Organization']['@id'])
        for entity in entities.values():
            self.assertTrue(entity['@id'].startswith(canonical))
            self.assertEqual(entity['url'], canonical)
        with urllib.request.urlopen(URL + 'sitemap.xml') as response:
            sitemap = ET.fromstring(response.read())
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        self.assertEqual([el.text for el in sitemap.findall('s:url/s:loc', ns)], [canonical])
        with urllib.request.urlopen(URL + 'robots.txt') as response:
            robots = response.read().decode()
        self.assertIn('Allow: /', robots)
        self.assertIn('Sitemap: ' + canonical + 'sitemap.xml', robots)

    def test_service_faq_readable_and_keyboard_operable_without_javascript(self):
        page = self.page(java_script_enabled=False)
        page.goto(URL)
        answers = page.locator('.faq-answers details')
        self.assertEqual(answers.count(), 5)
        self.assertTrue(answers.first.locator('p').is_visible())
        for answer in answers.all():
            self.assertTrue(answer.locator('p').text_content().strip())
        second = answers.nth(1)
        second.locator('summary').focus()
        page.keyboard.press('Enter')
        self.assertTrue(second.locator('p').is_visible())
        self.assertIn('Upper Funnel', second.locator('p').inner_text())

    def test_intro_can_be_skipped_and_does_not_replay_on_refresh(self):
        page = self.page()
        page.goto(URL)
        self.assertTrue(page.locator('#skip-animation').is_visible())
        self.assertIn('spraying', page.locator('#spray-art').get_attribute('class'))
        page.locator('#skip-animation').click()
        self.assertNotIn('spraying', page.locator('#spray-art').get_attribute('class'))
        self.assertFalse(page.locator('#skip-animation').is_visible())
        self.assertEqual(page.evaluate('document.activeElement.textContent.trim()'), 'בואו נעשה רעש')
        page.reload()
        self.assertFalse(page.locator('#skip-animation').is_visible())

    def test_intro_finishes_automatically_without_blocking_content(self):
        page = self.page()
        page.goto(URL)
        self.assertTrue(page.locator('.hero-actions').is_visible())
        page.wait_for_function("!document.querySelector('#spray-art').classList.contains('spraying')")
        self.assertFalse(page.locator('#skip-animation').is_visible())

    def test_reduced_motion_and_runtime_change(self):
        page = self.page(reduced_motion='reduce')
        page.goto(URL)
        self.assertNotIn('spraying', page.locator('#spray-art').get_attribute('class'))
        self.assertEqual(page.locator('.spray-first').evaluate('(el) => getComputedStyle(el).animationName'), 'none')
        another = self.page()
        another.goto(URL)
        another.emulate_media(reduced_motion='reduce')
        another.wait_for_function("!document.querySelector('#spray-art').classList.contains('spraying')")

    def test_spray_character_tracks_text_and_stops_on_skip_and_reduced_motion(self):
        page = self.page()
        page.goto(URL)
        page.wait_for_timeout(100)
        def sample(time):
            return page.evaluate("""(time) => {
                cancelAnimationFrame(characterFrame);
                moveSprayCharacter(startedAt + time);
                cancelAnimationFrame(characterFrame);
                return {
                    lines: [...document.querySelectorAll('.spray-line')].map(el => el.style.clipPath),
                    position: document.querySelector('#spray-character').style.transform,
                    spray: document.querySelector('#paint-trail').style.opacity
                };
            }""", time)
        writing = sample(850)
        self.assertIn('50%', writing['lines'][0])
        self.assertIn('100%', writing['lines'][1])
        end_of_line = sample(1700)
        returning = sample(1900)
        self.assertEqual(end_of_line['lines'], returning['lines'])
        self.assertNotEqual(end_of_line['position'], returning['position'])
        self.assertEqual(returning['spray'], '0')
        next_line = sample(3000)
        self.assertIn('50%', next_line['lines'][1])
        self.assertIn('100%', next_line['lines'][2])
        self.assertNotEqual(next_line['spray'], '0')
        page.locator('#skip-animation').click()
        self.assertEqual(page.locator('#spray-character').get_attribute('style'), '')
        self.assertEqual(page.locator('#paint-trail').evaluate('(el) => getComputedStyle(el).opacity'), '0')
        page.locator('#replay-animation').click()
        self.assertTrue(page.locator('#skip-animation').is_visible())
        page.emulate_media(reduced_motion='reduce')
        page.wait_for_function("!document.querySelector('#spray-art').classList.contains('spraying')")
        self.assertFalse(page.locator('#replay-animation').is_visible())
        self.assertEqual(page.locator('#spray-character').get_attribute('style'), '')

    def test_banner_comparison_and_status(self):
        page = self.page(reduced_motion='reduce')
        page.goto(URL)
        button = page.locator('#banner-toggle')
        self.assertEqual(button.get_attribute('aria-pressed'), 'true')
        button.click()
        self.assertEqual(button.get_attribute('aria-pressed'), 'false')
        self.assertIn('ללא הבאנר', page.locator('#toggle-status').inner_text())
        for banner in page.locator('.mock-banner').all():
            self.assertEqual(banner.get_attribute('aria-hidden'), 'true')
            self.assertEqual(banner.evaluate('(el) => getComputedStyle(el).opacity'), '0')
        button.click()
        self.assertEqual(button.get_attribute('aria-pressed'), 'true')
        self.assertEqual(page.locator('.mock-banner').first.get_attribute('aria-hidden'), 'false')

    def test_spray_audio_starts_automatically_when_allowed_and_stops_on_return_and_skip(self):
        browser = self.playwright.chromium.launch(executable_path='/usr/bin/chromium',
            args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
        self.addCleanup(browser.close)
        page = browser.new_page()
        page.goto(URL)
        self.assertEqual(page.locator('#sound-toggle').count(), 0)
        page.wait_for_function('sprayAudio && sprayAudio.context.state === "running"')
        page.evaluate('''() => {
            cancelAnimationFrame(characterFrame);
            moveSprayCharacter(startedAt + 850);
            cancelAnimationFrame(characterFrame);
            window.audioMeter = sprayAudio.context.createAnalyser();
            window.audioMeter.fftSize = 2048;
            sprayAudio.gain.connect(window.audioMeter);
            window.audioMeter.connect(sprayAudio.context.destination);
        }''')
        page.wait_for_timeout(130)
        def rms():
            return page.evaluate('''() => {
                const data = new Float32Array(window.audioMeter.fftSize);
                window.audioMeter.getFloatTimeDomainData(data);
                return Math.sqrt(data.reduce((sum, value) => sum + value * value, 0) / data.length);
            }''')
        self.assertGreater(rms(), 0.001)
        page.evaluate('''() => {
            moveSprayCharacter(startedAt + 1900);
            cancelAnimationFrame(characterFrame);
        }''')
        page.wait_for_timeout(130)
        self.assertLess(rms(), 0.00001)
        page.locator('#skip-animation').click()
        self.assertFalse(page.evaluate('hissPlaying'))
        page.locator('#replay-animation').click()
        page.wait_for_function('hissPlaying')
        page.locator('#skip-animation').click()
        self.assertFalse(page.evaluate('hissPlaying'))

    def test_contact_routes_are_real_and_distinct(self):
        page = self.page()
        page.goto(URL)
        routes = [unquote(link.get_attribute('href')) for link in page.locator('[data-contact]').all()]
        self.assertTrue(all(route.startswith('mailto:daniel@korenf.com?subject=') for route in routes))
        self.assertIn('מותג או משרד פרסום', routes[0])
        self.assertIn('יוצר/ת תוכן', routes[1])
        self.assertTrue(all('&body=' in route for route in routes))

    def test_clipboard_success_and_failure_messages(self):
        page = self.page(permissions=['clipboard-read', 'clipboard-write'])
        page.goto(URL)
        page.locator('#copy-email').click()
        page.wait_for_function("document.querySelector('#copy-status').textContent.includes('הועתקה')")
        self.assertEqual(page.evaluate('navigator.clipboard.readText()'), 'daniel@korenf.com')
        page.evaluate("() => { navigator.clipboard.writeText = () => Promise.reject(new Error('denied')); }")
        page.locator('#copy-email').click()
        page.wait_for_function("document.querySelector('#copy-status').textContent.includes('לא ניתן')")

    def test_keyboard_navigation_and_skip_link(self):
        page = self.page(reduced_motion='reduce')
        page.goto(URL)
        page.keyboard.press('Tab')
        self.assertEqual(page.evaluate('document.activeElement.className'), 'skip-link')
        page.keyboard.press('Enter')
        self.assertEqual(page.evaluate('location.hash'), '#main')

    def test_viewports_no_overflow_missing_resources_or_console_errors(self):
        for width in [320, 390, 768, 1024, 1440]:
            with self.subTest(width=width):
                page = self.page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                errors = []
                bad_responses = []
                requests = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: bad_responses.append(response.url) if response.status >= 400 else None)
                page.on('request', lambda request: requests.append(request.url))
                page.goto(URL, wait_until='networkidle')
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                self.assertEqual(errors, [])
                self.assertEqual(bad_responses, [])
                self.assertTrue(all(url.startswith(URL) for url in requests))
                self.assertTrue(page.evaluate('document.fonts.check("700 32px Karantina")'))
                self.assertEqual(page.locator('img').count(), 0)
                self.assertEqual(page.locator('.character-placeholder').count(), 0)
                self.assertTrue(page.locator('#spray-character').is_visible())
                self.assertEqual(page.locator('.empty-video').count(), 2)
                page.close()

    def test_portable_preview_without_resource_access(self):
        html = (Path(__file__).resolve().parents[1] / 'preview.html').read_text()
        for width in [390, 1440]:
            with self.subTest(width=width):
                page = self.page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                requests, errors = [], []
                page.on('request', lambda request: requests.append(request.url))
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.route('**/*', lambda route: route.abort())
                page.set_content(html, wait_until='load')
                page.evaluate('document.fonts.ready')
                self.assertEqual(page.locator('body').evaluate('(el) => getComputedStyle(el).backgroundColor'), 'rgb(255, 255, 255)')
                self.assertEqual(page.locator('.blue').first.evaluate('(el) => getComputedStyle(el).color'), 'rgb(21, 72, 255)')
                self.assertTrue(page.evaluate('document.fonts.check("700 32px Karantina")'))
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                page.locator('#banner-toggle').click()
                self.assertEqual(page.locator('#banner-toggle').get_attribute('aria-pressed'), 'false')
                self.assertEqual(requests, [])
                self.assertEqual(errors, [])
                page.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
