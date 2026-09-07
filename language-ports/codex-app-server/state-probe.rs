use codex_state::{SqliteConfig, StateRuntime};
use std::fs;
use std::os::unix::fs::{DirBuilderExt, MetadataExt};
use std::path::Path;
use std::process::ExitCode;
use std::time::Duration;

fn identity(label: &str, metadata: fs::Metadata) -> (u64, u64) {
    let value = (metadata.dev(), metadata.ino());
    println!("CODEX-STATE: ID {label} dev={} ino={}", value.0, value.1);
    value
}

fn require(condition: bool, message: &str) -> std::io::Result<()> {
    if condition {
        Ok(())
    } else {
        Err(std::io::Error::other(message))
    }
}

fn identity_preflight(home: &Path) -> std::io::Result<()> {
    let a_path = home.join("identity-a");
    let b_path = home.join("identity-b");
    let renamed = home.join("identity-renamed");
    let a = fs::File::create_new(&a_path)?;
    let b = fs::File::create_new(&b_path)?;
    let a_id = identity("a-fd", a.metadata()?);
    let b_id = identity("b-fd", b.metadata()?);
    require(a_id != b_id, "distinct fresh files share one identity")?;
    require(identity("a-path", fs::metadata(&a_path)?) == a_id, "a stat/fstat mismatch")?;
    require(identity("b-path", fs::metadata(&b_path)?) == b_id, "b stat/fstat mismatch")?;

    let reopened = fs::File::open(&a_path)?;
    require(identity("a-reopened", reopened.metadata()?) == a_id, "reopen changed identity")?;
    fs::rename(&a_path, &renamed)?;
    require(!a_path.try_exists()?, "rename left the old path present")?;
    require(identity("renamed-path", fs::metadata(&renamed)?) == a_id, "rename changed path identity")?;
    require(identity("renamed-fd", a.metadata()?) == a_id, "rename changed open-file identity")?;

    fs::remove_file(&renamed)?;
    require(!renamed.try_exists()?, "unlink left the path present")?;
    require(identity("unlinked-fd", a.metadata()?) == a_id, "unlink changed open-file identity")?;
    let replacement = fs::File::create_new(&renamed)?;
    let replacement_id = identity("replacement-fd", replacement.metadata()?);
    require(replacement_id != a_id && replacement_id != b_id, "replacement reused a live file identity")?;
    require(identity("replacement-path", fs::metadata(&renamed)?) == replacement_id, "replacement stat/fstat mismatch")?;
    require(identity("unlinked-after-replacement", a.metadata()?) == a_id, "replacement changed unlinked-file identity")?;
    println!("CODEX-STATE: PASS identity preflight");
    Ok(())
}

fn probe(home: &Path) -> std::io::Result<bool> {
    if let Err(error) = identity_preflight(home) {
        eprintln!("CODEX-STATE: FAIL identity preflight: {error:#}");
        return Ok(false);
    }
    let sqlite = SqliteConfig::from_sqlite_home(
        home.to_path_buf().try_into().expect("absolute probe path"),
    );
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(2)
        .enable_all()
        .build()?;
    println!("CODEX-STATE: RUN init {}", home.display());
    let passed = match runtime.block_on(StateRuntime::init(sqlite, "openai".into())) {
        Ok(state) => {
            runtime.block_on(state.close());
            true
        }
        Err(error) => {
            eprintln!("CODEX-STATE: FAIL init: {error:#}");
            false
        }
    };
    runtime.shutdown_timeout(Duration::from_secs(2));
    Ok(passed)
}

fn main() -> ExitCode {
    let home = Path::new("/tmp").join(format!("codex-state-probe-{}", std::process::id()));
    if let Err(error) = fs::DirBuilder::new().mode(0o700).create(&home) {
        eprintln!("CODEX-STATE: FAIL create private directory: {error:#}");
        return ExitCode::FAILURE;
    }
    let mut passed = match probe(&home) {
        Ok(passed) => passed,
        Err(error) => {
            eprintln!("CODEX-STATE: FAIL runtime: {error:#}");
            false
        }
    };
    if let Err(error) = fs::remove_dir_all(&home) {
        eprintln!("CODEX-STATE: FAIL cleanup: {error:#}");
        passed = false;
    }
    if passed {
        println!("CODEX-STATE: PASS");
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
