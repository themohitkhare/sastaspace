//! Optional audio playback via `rodio`. Gated on the `audio` feature.
//!
//! When the `audio` feature is not compiled (e.g. Linux CI without ALSA),
//! the public API still exists but `play_file` returns `Err("audio not compiled in")`.
//! Saving WAVs to disk is always available in `download.rs` regardless.

#[cfg(feature = "audio")]
pub fn play_file(path: &std::path::Path) -> Result<(), String> {
    use rodio::{Decoder, OutputStream, Sink};
    use std::fs::File;
    use std::io::BufReader;

    let (_stream, stream_handle) =
        OutputStream::try_default().map_err(|e| format!("audio output: {e}"))?;
    let sink = Sink::try_new(&stream_handle).map_err(|e| format!("audio sink: {e}"))?;

    let file = File::open(path).map_err(|e| format!("open {}: {e}", path.display()))?;
    let source = Decoder::new(BufReader::new(file)).map_err(|e| format!("decode audio: {e}"))?;

    sink.append(source);
    sink.sleep_until_end();
    Ok(())
}

#[cfg(not(feature = "audio"))]
pub fn play_file(_path: &std::path::Path) -> Result<(), String> {
    Err("audio playback not compiled in (build with --features audio or default features)".into())
}
