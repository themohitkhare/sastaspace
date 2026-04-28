//! Single source of truth for colors and text styles.

use ratatui::style::{Color, Modifier, Style};

/// The default sastaspace palette. Inspired by the existing landing-page
/// design tokens (warm amber accents, neutral grays). One theme for v1.
pub struct Theme {
    pub fg: Color,
    pub bg: Color,
    pub muted: Color,
    pub accent: Color,
    pub success: Color,
    pub warn: Color,
    pub error: Color,
    pub border: Color,
}

impl Theme {
    pub const fn default_dark() -> Self {
        Self {
            fg: Color::Rgb(230, 230, 230),
            bg: Color::Rgb(16, 16, 20),
            muted: Color::Rgb(120, 120, 128),
            accent: Color::Rgb(255, 184, 0),
            success: Color::Rgb(100, 200, 120),
            warn: Color::Rgb(240, 180, 80),
            error: Color::Rgb(240, 100, 100),
            border: Color::Rgb(64, 64, 72),
        }
    }

    pub fn header(&self) -> Style {
        Style::default()
            .fg(self.accent)
            .add_modifier(Modifier::BOLD)
    }

    pub fn body(&self) -> Style {
        Style::default().fg(self.fg)
    }

    pub fn muted(&self) -> Style {
        Style::default().fg(self.muted)
    }

    pub fn focused(&self) -> Style {
        Style::default().fg(self.bg).bg(self.accent)
    }
}
