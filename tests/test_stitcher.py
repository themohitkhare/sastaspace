# tests/test_stitcher.py
from sastaspace.swarm.schemas import ColorPalette, SectionFragment
from sastaspace.swarm.stitcher import stitch_page


class TestStitcher:
    def _palette(self):
        return ColorPalette(
            primary="#1a1a2e",
            secondary="#16213e",
            accent="#e94560",
            background="#ffffff",
            text="#333333",
            headline_font="'Inter', sans-serif",
            body_font="'Source Sans 3', sans-serif",
            color_mode="light",
            roundness="8px",
        )

    def test_basic_stitching(self):
        fragments = [
            SectionFragment(section_name="hero", html="<section><h1>Hello</h1></section>"),
            SectionFragment(section_name="features", html="<section><h2>Features</h2></section>"),
        ]
        result = stitch_page(fragments, self._palette(), "Test Site")
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result
        assert "<h1>Hello</h1>" in result
        assert "<h2>Features</h2>" in result
        assert result.index("Hello") < result.index("Features")

    def test_includes_css_variables(self):
        fragments = [SectionFragment(section_name="hero", html="<section>Hi</section>")]
        result = stitch_page(fragments, self._palette(), "Test")
        assert "--color-primary: #1a1a2e" in result
        assert "--color-accent: #e94560" in result

    def test_includes_google_fonts(self):
        fragments = [SectionFragment(section_name="hero", html="<section>Hi</section>")]
        result = stitch_page(fragments, self._palette(), "Test")
        assert "fonts.googleapis.com" in result

    def test_merges_section_css(self):
        fragments = [
            SectionFragment(
                section_name="hero",
                html="<section class='hero'>Hi</section>",
                css=".hero { padding: 4rem; }",
            ),
        ]
        result = stitch_page(fragments, self._palette(), "Test")
        assert ".hero { padding: 4rem; }" in result

    def test_preserves_section_order(self):
        fragments = [
            SectionFragment(section_name="footer", html="<footer>End</footer>"),
            SectionFragment(section_name="hero", html="<section>Start</section>"),
        ]
        result = stitch_page(fragments, self._palette(), "Test")
        assert result.index("End") < result.index("Start")
