"""Both languages are crawlable pages with working localized interactions."""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote
from playwright.sync_api import sync_playwright, expect
import test_site


class LanguageTests(unittest.TestCase):
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

    def test_static_language_links_metadata_and_english_content(self):
        page = self.page(java_script_enabled=False, locale='en-US', reduced_motion='reduce')
        self.assertEqual(page.goto(test_site.URL).status, 200)
        self.assertEqual(page.locator('html').get_attribute('lang'), 'he')
        page.locator('.language-switch').click()
        self.assertEqual(page.url, test_site.URL + 'en/')
        self.assertEqual(page.locator('html').get_attribute('lang'), 'en')
        self.assertEqual(page.locator('html').get_attribute('dir'), 'ltr')
        self.assertIn('Your brand.', page.locator('h1').text_content())
        self.assertIn('payment based on views', page.locator('.hero-description').inner_text())
        self.assertEqual(page.locator('main > section').count(), 4)
        self.assertEqual(page.locator('.faq-answers details').count(), 5)
        self.assertNotRegex(page.locator('body').inner_text().replace('עברית', ''), r'[\u0590-\u05ff]')
        for link in page.locator('[data-contact]').all():
            self.assertIn('mailto:daniel@noizer.co.il?subject=NOIZER', unquote(link.get_attribute('href')))
            self.assertNotRegex(unquote(link.get_attribute('href')), r'[\u0590-\u05ff]')
        self.assertEqual(page.locator('link[rel="canonical"]').get_attribute('href'), 'https://noizer.co.il/en/')
        self.assertEqual(page.locator('meta[property="og:locale"]').get_attribute('content'), 'en_US')
        self.assertEqual(page.locator('meta[property="og:url"]').get_attribute('content'), 'https://noizer.co.il/en/')
        for language, href in [('he', 'https://noizer.co.il/'), ('en', 'https://noizer.co.il/en/'), ('x-default', 'https://noizer.co.il/')]:
            self.assertEqual(page.locator(f'link[hreflang="{language}"]').get_attribute('href'), href)
        graph = json.loads(page.locator('script[type="application/ld+json"]').inner_text())['@graph']
        self.assertEqual(graph[2]['inLanguage'], 'en')
        self.assertEqual(graph[1]['provider']['@id'], graph[0]['@id'])
        self.assertEqual(graph[0]['email'], 'daniel@noizer.co.il')
        page.locator('.faq-answers details').nth(1).locator('summary').focus()
        page.keyboard.press('Enter')
        self.assertTrue(page.locator('.faq-answers details').nth(1).locator('p').is_visible())
        page.locator('.language-switch').click()
        self.assertEqual(page.url, test_site.URL)
        self.assertEqual(page.locator('html').get_attribute('lang'), 'he')
        self.assertEqual(page.locator('html').get_attribute('dir'), 'rtl')
        self.assertEqual(page.locator('meta[property="og:locale"]').get_attribute('content'), 'he_IL')

    def test_english_video_banner_mail_and_clipboard_messages(self):
        page = self.page(reduced_motion='reduce', permissions=['clipboard-read', 'clipboard-write'])
        page.goto(test_site.URL + 'en/')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.locator('.demo-one .video-play').click()
        page.wait_for_function("document.querySelector('#creator-one').currentTime > 0.1")
        expect(page.locator('.demo-one .video-play')).to_have_attribute('aria-label', 'Pause video 1')
        page.locator('.demo-one .video-sound').click()
        expect(page.locator('.demo-one .video-sound')).to_have_attribute('aria-label', 'Mute video 1')
        page.locator('#banner-toggle').click()
        self.assertEqual(page.locator('#toggle-label').inner_text(), 'Show the banner')
        self.assertIn('without banners', page.locator('#toggle-status').inner_text())
        self.assertFalse(page.locator('#creator-one').evaluate('(v) => v.paused'))
        page.locator('#banner-toggle').click()
        self.assertEqual(page.locator('#toggle-label').inner_text(), 'Hide the banner')
        self.assertIn('visible', page.locator('#toggle-status').inner_text())
        page.locator('.demo-one .video-play').click()
        expect(page.locator('.demo-one .video-play')).to_have_attribute('aria-label', 'Play video 1')
        page.locator('#creator-one').evaluate('(video) => { video.play = () => Promise.reject(new Error("blocked")); }')
        page.locator('.demo-one .video-play').click()
        expect(page.locator('.demo-one .video-status')).to_have_text('The video could not be played. Please try again.')
        routes = [unquote(link.get_attribute('href')) for link in page.locator('[data-contact]').all()]
        self.assertIn('Brand or agency inquiry', routes[0])
        self.assertIn('Tell us about your campaign:', routes[0])
        self.assertIn('Creator inquiry', routes[1])
        self.assertIn('Tell us about your content:', routes[1])
        self.assertTrue(all('&body=' in route and not re.search(r'[\u0590-\u05ff]', route) for route in routes))
        page.locator('#copy-email').click()
        expect(page.locator('#copy-status')).to_have_text('Email address copied')
        self.assertEqual(page.evaluate('navigator.clipboard.readText()'), 'daniel@noizer.co.il')
        page.evaluate('() => { navigator.clipboard.writeText = () => Promise.reject(new Error("denied")); }')
        page.locator('#copy-email').click()
        expect(page.locator('#copy-status')).to_contain_text('Unable to copy automatically')
        self.assertEqual(errors, [])

    def test_english_intro_and_return_to_hebrew(self):
        page = self.page(viewport={'width': 390, 'height': 900})
        page.goto(test_site.URL + 'en/')
        page.wait_for_function("document.querySelector('#spray-art').classList.contains('spraying')")
        self.assertIn('Skip animation', page.locator('#skip-animation').inner_text())
        page.locator('#skip-animation').click()
        self.assertIn('Let’s make noise', page.evaluate('document.activeElement.textContent'))
        page.reload()
        self.assertFalse(page.locator('#skip-animation').is_visible())
        page.locator('.language-switch').click()
        self.assertEqual(page.url, test_site.URL)
        self.assertFalse(page.locator('#skip-animation').is_visible())

    def test_english_portable_preview_without_network(self):
        html = (Path(__file__).resolve().parents[1] / 'preview-en.html').read_text()
        page = self.page(viewport={'width': 390, 'height': 900}, reduced_motion='reduce')
        requests, errors = [], []
        page.on('request', lambda request: requests.append(request.url))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/*', lambda route: route.abort())
        page.set_content(html, wait_until='load')
        page.evaluate('document.fonts.ready')
        self.assertEqual(page.locator('html').get_attribute('lang'), 'en')
        self.assertEqual(page.locator('html').get_attribute('dir'), 'ltr')
        page.locator('#banner-toggle').click()
        self.assertEqual(page.locator('#toggle-label').inner_text(), 'Show the banner')
        self.assertEqual(requests, [])
        self.assertEqual(errors, [])

    def test_bilingual_responsive_pages_load_shared_assets(self):
        for path in ['', 'en/']:
            for width in [320, 390, 760, 768, 1024, 1440]:
                with self.subTest(path=path, width=width):
                    page = self.page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                    errors, bad_responses = [], []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('response', lambda response: bad_responses.append(response.url) if response.status >= 400 else None)
                    page.goto(test_site.URL + path, wait_until='networkidle')
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                    switch = page.locator('.language-switch')
                    self.assertTrue(switch.is_visible())
                    self.assertGreaterEqual(switch.bounding_box()['height'], 44)
                    self.assertEqual(errors, [])
                    self.assertEqual(bad_responses, [])
                    page.close()
