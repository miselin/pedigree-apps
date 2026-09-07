use std::collections::HashMap;
use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::process::{Command, Stdio};
use std::sync::{mpsc, Arc, Condvar, Mutex};
use std::thread;
use std::time::{Duration, Instant};

thread_local! { static LOCAL: std::cell::Cell<u32> = const { std::cell::Cell::new(0) }; }

fn main() {
    let phase = std::env::args().nth(1).expect("phase argument");
    println!("RUST-PROBE: START {phase}");
    match phase.as_str() {
        "basic" => {
            let mut values = HashMap::new();
            for i in 0..1024 { values.insert(format!("key-{i}"), i * i); }
            assert_eq!(values["key-31"], 961);
            let start = Instant::now();
            thread::sleep(Duration::from_millis(10));
            assert!(start.elapsed() >= Duration::from_millis(10));
            assert!(std::time::SystemTime::now() > std::time::UNIX_EPOCH);
        }
        "fs" => {
            let dir = format!("/tmp/rust-probe-{}", std::process::id());
            fs::create_dir(&dir).unwrap();
            fs::write(format!("{dir}/first"), b"Pedigree Rust filesystem\n").unwrap();
            fs::rename(format!("{dir}/first"), format!("{dir}/second")).unwrap();
            assert_eq!(fs::read_to_string(format!("{dir}/second")).unwrap(),
                       "Pedigree Rust filesystem\n");
            assert_eq!(fs::read_dir(&dir).unwrap().count(), 1);
            assert_eq!(fs::metadata(format!("{dir}/second")).unwrap().len(), 25);
            fs::remove_dir_all(&dir).unwrap();
        }
        "threads" => {
            let state = Arc::new((Mutex::new(false), Condvar::new()));
            let (send, recv) = mpsc::channel();
            let mut joins = Vec::new();
            LOCAL.with(|v| v.set(99));
            for n in 1..=4 {
                let state = Arc::clone(&state);
                let send = send.clone();
                joins.push(thread::spawn(move || {
                    LOCAL.with(|v| { assert_eq!(v.get(), 0); v.set(n); });
                    let (lock, cond) = &*state;
                    let mut ready = lock.lock().unwrap();
                    while !*ready { ready = cond.wait(ready).unwrap(); }
                    send.send(LOCAL.with(|v| v.get())).unwrap();
                }));
            }
            let (lock, cond) = &*state;
            *lock.lock().unwrap() = true;
            cond.notify_all();
            drop(send);
            assert_eq!(recv.iter().sum::<u32>(), 10);
            for join in joins { join.join().unwrap(); }
            LOCAL.with(|v| assert_eq!(v.get(), 99));
        }
        "current-exe" => {
            assert!(std::env::current_exe().unwrap().is_absolute());
        }
        "process" => {
            let executable = std::env::args().next().unwrap();
            let mut child = Command::new(executable).arg("child")
                .env("PEDIGREE_RUST_CHILD", "inherited")
                .stdin(Stdio::piped()).stdout(Stdio::piped()).spawn().unwrap();
            child.stdin.take().unwrap().write_all(b"input through pipe").unwrap();
            let output = child.wait_with_output().unwrap();
            assert!(output.status.success());
            assert!(String::from_utf8(output.stdout).unwrap().contains("RUST-CHILD: PASS"));
        }
        "child" => {
            assert_eq!(std::env::var("PEDIGREE_RUST_CHILD").unwrap(), "inherited");
            let mut input = String::new();
            std::io::stdin().read_to_string(&mut input).unwrap();
            assert_eq!(input, "input through pipe");
            println!("RUST-CHILD: PASS");
        }
        "network" => {
            let listener = TcpListener::bind("127.0.0.1:0").unwrap();
            let addr = listener.local_addr().unwrap();
            let join = thread::spawn(move || {
                let (mut stream, _) = listener.accept().unwrap();
                let mut bytes = [0; 4];
                stream.read_exact(&mut bytes).unwrap();
                assert_eq!(&bytes, b"ping");
                stream.write_all(b"pong").unwrap();
            });
            let mut stream = TcpStream::connect(addr).unwrap();
            stream.write_all(b"ping").unwrap();
            let mut bytes = [0; 4];
            stream.read_exact(&mut bytes).unwrap();
            assert_eq!(&bytes, b"pong");
            join.join().unwrap();
        }
        _ => panic!("unknown phase {phase}"),
    }
    println!("RUST-PROBE: PASS {phase}");
}
