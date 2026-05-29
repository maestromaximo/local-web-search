# Third-Party Notices

Local Web Search is licensed under the Apache License 2.0. It integrates with
several third-party projects that keep their own licenses and terms.

## Runtime and Optional Dependencies

- SearXNG is used as a separate local search service, typically through the
  `docker.io/searxng/searxng` container image. SearXNG is licensed under the
  GNU Affero General Public License v3.0 or later. Local Web Search does not
  copy SearXNG source code into this package, but users who run, modify, host,
  or redistribute SearXNG must comply with SearXNG's license.
- Crawl4AI is used to fetch and extract full page text. Crawl4AI is licensed
  under the Apache License 2.0.
- FastAPI, Uvicorn, OpenAI Agents SDK, httpx, pydantic, pytest, and ruff are
  used as runtime, optional, or development dependencies under their respective
  licenses.

## Web Search and Crawling Disclaimer

Search results come from the SearXNG instance you configure. Fetched page text
comes from Crawl4AI visiting the requested URL. You are responsible for
respecting robots.txt, website terms, copyright, authentication boundaries,
privacy rules, and rate limits when using this package.

This project is not affiliated with, endorsed by, or sponsored by SearXNG,
Crawl4AI, or any upstream search engine used by your SearXNG instance.
