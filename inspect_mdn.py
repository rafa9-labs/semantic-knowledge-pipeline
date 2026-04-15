"""Quick script to inspect MDN page structure with Playwright."""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(
            "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function",
            wait_until="load",
            timeout=60000,
        )
        # Check what elements exist
        print("=== Checking selectors ===")
        for sel in ["article", "main", "main#content", ".content", "[role='main']", "#content", ".article"]:
            count = await page.locator(sel).count()
            print(f"  '{sel}': {count} found")

        # Get h1
        h1 = await page.locator("h1").first.text_content()
        print(f"\nH1 title: {h1}")

        # Try getting content from the most promising selector
        for sel in ["main#content", "main", "[role='main']", ".article"]:
            el = page.locator(sel).first
            count = await page.locator(sel).count()
            if count > 0:
                text = await el.inner_text()
                print(f"\n=== Content from '{sel}' ({len(text)} chars) ===")
                print(text[:300])
                break

        await browser.close()

asyncio.run(main())