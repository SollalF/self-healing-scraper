from self_healing_scraper.models import PageContent, ParserDefinition
from self_healing_scraper.runtime.executor import execute_parser


def test_execute_listing_parser(
    listing_page: PageContent, listing_definition: ParserDefinition
) -> None:
    items = execute_parser(listing_page, listing_definition, "listing")
    assert len(items) == 3
    assert items[0]["title"] == "Alpha Story"
    assert items[0]["url"] == "https://techcrunch.com/2026/07/25/alpha/"
    assert items[0]["source"] == "TechCrunch"
    assert items[1]["title"] == "Beta Story"


def test_execute_article_parser() -> None:
    html = """
    <html><body>
      <article>
        <h1 class="headline">Solo Piece</h1>
        <div class="body">Lots of article body text for readers.</div>
      </article>
    </body></html>
    """
    page = PageContent(url="https://example.com/a/1", html=html, success=True)
    definition = ParserDefinition(
        item_selector=None,
        source_name="Example",
        fields={
            "title": {"selector": "h1.headline", "attr": "text", "many": False},
            "content": {"selector": "div.body", "attr": "text", "many": False},
        },
    )
    items = execute_parser(page, definition, "article")
    assert len(items) == 1
    assert items[0]["title"] == "Solo Piece"
    assert items[0]["url"] == "https://example.com/a/1"
    assert "article body" in (items[0].get("content") or "")
