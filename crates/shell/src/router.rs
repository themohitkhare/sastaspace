//! Owns the stack of registered apps and dispatches actions to the current one.

use sastaspace_core::{App, AppResult};
use std::collections::HashMap;

pub struct Router {
    apps: HashMap<&'static str, Box<dyn App>>,
    current: &'static str,
}

impl Router {
    pub fn new(start: &'static str) -> Self {
        Self {
            apps: HashMap::new(),
            current: start,
        }
    }

    pub fn register(&mut self, app: Box<dyn App>) {
        self.apps.insert(app.id(), app);
    }

    pub fn current(&mut self) -> &mut dyn App {
        self.apps
            .get_mut(self.current)
            .expect("current app missing from router")
            .as_mut()
    }

    /// Returns true if the program should keep running.
    pub fn dispatch(&mut self, result: AppResult) -> bool {
        match result {
            AppResult::Continue => true,
            AppResult::SwitchTo(id) => {
                if self.apps.contains_key(id) {
                    self.current = id;
                }
                true
            }
            AppResult::Quit => false,
        }
    }
}
