fn main() {
    let words = vec!["Pedigree", "native", "Rust"];
    let result = std::thread::spawn(move || words.join(" ")).join().unwrap();
    assert_eq!(result, "Pedigree native Rust");
    std::fs::write("/tmp/rust-native-result", &result).unwrap();
    assert_eq!(std::fs::read_to_string("/tmp/rust-native-result").unwrap(), result);
    std::fs::remove_file("/tmp/rust-native-result").unwrap();
    println!("RUST-NATIVE: PASS");
}
