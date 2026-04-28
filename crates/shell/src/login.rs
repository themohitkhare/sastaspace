//! Magic-link login modal. Two states:
//!   1. EnterEmail — single-line text field; enter triggers `auth::magic_link::request`
//!   2. EnterToken — single-line text field; enter triggers `verify`, stores bearer in keychain
//!
//! Renders centered over whatever app is below. Esc dismisses.

use auth::{
    keychain::{TokenKind, TokenStore},
    magic_link::{self, MagicLinkConfig, MagicLinkError},
};
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::Style,
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph},
    Frame,
};
use sastaspace_core::theme::Theme;
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoginState {
    EnterEmail,
    Sending,
    EnterToken,
    Verifying,
    Success,
    Failure,
}

pub struct LoginModal {
    state: LoginState,
    email_buf: String,
    token_buf: String,
    error: Option<String>,
    cfg: MagicLinkConfig,
    store: Arc<dyn TokenStore>,
    theme: Theme,
}

pub enum LoginOutcome {
    KeepOpen,
    Closed,
}

impl LoginModal {
    pub fn new(cfg: MagicLinkConfig, store: Arc<dyn TokenStore>) -> Self {
        Self {
            state: LoginState::EnterEmail,
            email_buf: String::new(),
            token_buf: String::new(),
            error: None,
            cfg,
            store,
            theme: Theme::default_dark(),
        }
    }

    pub fn render(&self, frame: &mut Frame, area: Rect) {
        let modal = centered_rect(60, 30, area);
        frame.render_widget(Clear, modal);

        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.accent))
            .title(" sign in ");

        let inner = block.inner(modal);
        frame.render_widget(block, modal);

        let layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(2),
                Constraint::Length(3),
                Constraint::Length(2),
                Constraint::Min(0),
            ])
            .split(inner);

        let prompt: Vec<Line> = match self.state {
            LoginState::EnterEmail => vec![Line::from(Span::styled(
                "enter your email; we'll send a token",
                self.theme.body(),
            ))],
            LoginState::Sending => {
                vec![Line::from(Span::styled("sending\u{2026}", self.theme.muted()))]
            }
            LoginState::EnterToken => vec![Line::from(Span::styled(
                "check your email and paste the token below",
                self.theme.body(),
            ))],
            LoginState::Verifying => {
                vec![Line::from(Span::styled("verifying\u{2026}", self.theme.muted()))]
            }
            LoginState::Success => {
                vec![Line::from(Span::styled("signed in \u{2713}", self.theme.body()))]
            }
            LoginState::Failure => vec![Line::from(Span::styled(
                self.error.as_deref().unwrap_or("error").to_string(),
                Style::default().fg(self.theme.error),
            ))],
        };
        frame.render_widget(
            Paragraph::new(prompt).alignment(Alignment::Center),
            layout[0],
        );

        let buf = match self.state {
            LoginState::EnterEmail | LoginState::Sending => self.email_buf.as_str(),
            LoginState::EnterToken | LoginState::Verifying => self.token_buf.as_str(),
            _ => "",
        };
        let field = Paragraph::new(format!(" {buf}_"))
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(self.theme.border)),
            )
            .alignment(Alignment::Left);
        frame.render_widget(field, layout[1]);

        let help = Paragraph::new(vec![Line::from(Span::styled(
            "enter to confirm  \u{00b7}  esc to cancel",
            self.theme.muted(),
        ))])
        .alignment(Alignment::Center);
        frame.render_widget(help, layout[2]);
    }

    /// Returns `Closed` when the modal should be dismissed (success or cancel).
    pub async fn handle_key(&mut self, key: KeyEvent) -> LoginOutcome {
        if matches!(key.code, KeyCode::Esc) {
            return LoginOutcome::Closed;
        }
        match self.state {
            LoginState::EnterEmail => match key.code {
                KeyCode::Enter => self.submit_email().await,
                KeyCode::Backspace => {
                    self.email_buf.pop();
                }
                KeyCode::Char(c) => self.email_buf.push(c),
                _ => {}
            },
            LoginState::EnterToken => match key.code {
                KeyCode::Enter => self.submit_token().await,
                KeyCode::Backspace => {
                    self.token_buf.pop();
                }
                KeyCode::Char(c) => self.token_buf.push(c),
                _ => {}
            },
            LoginState::Failure => {
                self.error = None;
                self.state = if self.token_buf.is_empty() {
                    LoginState::EnterEmail
                } else {
                    LoginState::EnterToken
                };
            }
            LoginState::Success => return LoginOutcome::Closed,
            _ => {}
        }
        LoginOutcome::KeepOpen
    }

    async fn submit_email(&mut self) {
        self.state = LoginState::Sending;
        match magic_link::request(&self.cfg, self.email_buf.trim()).await {
            Ok(()) => {
                self.state = LoginState::EnterToken;
            }
            Err(MagicLinkError::InvalidEmail) => {
                self.state = LoginState::Failure;
                self.error = Some("invalid email".into());
            }
            Err(e) => {
                self.state = LoginState::Failure;
                self.error = Some(format!("{e}"));
            }
        }
    }

    async fn submit_token(&mut self) {
        self.state = LoginState::Verifying;
        match magic_link::verify(&self.cfg, self.token_buf.trim(), "").await {
            Ok(bearer) => {
                if let Err(e) = self.store.set(TokenKind::Auth, &bearer) {
                    self.state = LoginState::Failure;
                    self.error = Some(format!("keychain: {e}"));
                } else {
                    self.state = LoginState::Success;
                }
            }
            Err(e) => {
                self.state = LoginState::Failure;
                self.error = Some(format!("{e}"));
            }
        }
    }
}

fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);
    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup[1])[1]
}
