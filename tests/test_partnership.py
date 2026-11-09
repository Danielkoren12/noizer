"""Service navigation, static search content, contact and home isolation."""
import json
from pathlib import Path
import unittest
from urllib.parse import unquote
from playwright.sync_api import sync_playwright, expect
import test_site


class PartnershipTests(unittest.TestCase):
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

    def test_service_and_language_navigation_without_javascript(self):
        for language, path in [('he',''),('en','en/')]:
            with self.subTest(language=language):
                page = self.page(java_script_enabled=False, reduced_motion='reduce')
                page.goto(test_site.URL + path)
                page.locator('.service-nav').click()
                self.assertEqual(page.url, test_site.URL + path + 'partnership-ads/')
                self.assertEqual(page.locator('html').get_attribute('lang'), language)
                self.assertEqual(page.locator('h1').count(), 1)
                self.assertEqual(page.locator('.partnership-benefits li').count(), 3)
                self.assertEqual(page.locator('.partnership-timeline li').count(), 3)
                self.assertTrue(page.locator('.partnership-example-label').is_visible())
                self.assertIn('Meta', page.locator('.partnership-permission').text_content())
                canonical = 'https://noizer.co.il/' + path + 'partnership-ads/'
                self.assertEqual(page.locator('link[rel="canonical"]').get_attribute('href'), canonical)
                self.assertEqual(page.locator('meta[property="og:url"]').get_attribute('content'), canonical)
                graph = json.loads(page.locator('script[type="application/ld+json"]').inner_text())['@graph']
                self.assertEqual(graph[1]['@type'], 'Service')
                self.assertEqual(graph[1]['url'], canonical)
                self.assertEqual(graph[1]['provider']['@id'], graph[0]['@id'])
                self.assertEqual(graph[2]['inLanguage'], language)
                mail = unquote(page.locator('[data-contact="partnership"]').get_attribute('href'))
                self.assertIn('Partnership Ads', mail)
                self.assertIn('daniel@noizer.co.il', mail)
                self.assertIn('&body=', mail)
                if language == 'en':
                    self.assertNotRegex(page.locator('body').inner_text().replace('עברית',''), r'[\u0590-\u05ff]')
                    self.assertNotRegex(mail, r'[\u0590-\u05ff]')
                page.locator('.language-switch').click()
                other_path = 'en/partnership-ads/' if language == 'he' else 'partnership-ads/'
                self.assertEqual(page.url, test_site.URL + other_path)
                page.locator('.brand').click()
                self.assertEqual(page.url, test_site.URL + ('en/' if language == 'he' else ''))

    def test_service_runtime_contact_and_intro_not_consumed(self):
        page = self.page(permissions=['clipboard-read','clipboard-write'])
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(test_site.URL + 'partnership-ads/')
        self.assertIsNone(page.evaluate('sessionStorage.getItem("noizer:intro-seen")'))
        route = unquote(page.locator('[data-contact="partnership"]').get_attribute('href'))
        self.assertIn('פנייה בנושא Partnership Ads', route)
        page.locator('#copy-email').click()
        expect(page.locator('#copy-status')).to_contain_text('הועתקה')
        self.assertEqual(page.evaluate('navigator.clipboard.readText()'), 'daniel@noizer.co.il')
        page.locator('.language-switch').click()
        route = unquote(page.locator('[data-contact="partnership"]').get_attribute('href'))
        self.assertIn('NOIZER — Partnership Ads inquiry', route)
        self.assertIn('Tell us about your brief and campaign:', route)
        page.locator('#copy-email').click()
        expect(page.locator('#copy-status')).to_have_text('Email address copied')
        self.assertIsNone(page.evaluate('sessionStorage.getItem("noizer:intro-seen")'))
        page.locator('.brand').click()
        expect(page.locator('#skip-animation')).to_be_visible()
        page.locator('#skip-animation').click()
        self.assertEqual(errors, [])

    def test_both_service_pages_and_homes_fit_mobile_and_previews_work(self):
        for path in ['', 'en/', 'partnership-ads/', 'en/partnership-ads/']:
            for width in [320,390,768,1024,1440]:
                with self.subTest(path=path,width=width):
                    page = self.page(viewport={'width':width,'height':900}, reduced_motion='reduce')
                    errors, missing, requests = [], [], []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('response', lambda response: missing.append(response.url) if response.status >= 400 else None)
                    page.on('request',lambda request: requests.append(request.url))
                    page.goto(test_site.URL + path, wait_until='networkidle')
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                    self.assertTrue(page.locator('.service-nav').is_visible())
                    self.assertTrue(page.locator('.language-switch').is_visible())
                    self.assertEqual(errors, [])
                    self.assertEqual(missing, [])
                    if 'partnership' in path:
                        self.assertFalse(any('.mp4' in url for url in requests))
                    page.close()
        for filename in ['preview-partnership.html','preview-partnership-en.html']:
            page = self.page(viewport={'width':390,'height':900},reduced_motion='reduce')
            requests, errors = [], []
            page.on('request',lambda request: requests.append(request.url))
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.route('**/*',lambda route:route.abort())
            page.set_content((Path(__file__).resolve().parents[1]/filename).read_text(),wait_until='load')
            page.evaluate('document.fonts.ready')
            self.assertEqual(page.locator('.partnership-benefits li').count(),3)
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
            self.assertEqual(requests,[])
            self.assertEqual(errors,[])
            page.close()
