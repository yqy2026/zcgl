# Chrome DevTools

Control a Chrome browser instance for automation, scraping, and debugging.

## Scope

- **Automated Browsing**: Navigate to pages, interact with elements, and fill forms.
- **Data Scraping**: Extract content, take screenshots, and read page source.
- **Debugging**: Analyze console logs, network requests, and performance metrics.
- **Headless Mode**: configured to launch a new controlled browser instance (headless).

## Guidelines

- **Tool Usage**: Use `navigate` to go to URLs, `click` and `type` for interaction.
- **Content Extraction**: Use `screenshot` for visual checks and `get_content` for text.
- **Performance**: Be mindful of navigation times; use `wait` if necessary for dynamic content.
- **Safety**: Avoid navigating to malicious sites or downloading untrusted files.

## Examples

- "Go to `example.com` and take a screenshot"
- "Scrape the main heading from `localhost:3000`"
- "Check console logs for errors on the current page"
