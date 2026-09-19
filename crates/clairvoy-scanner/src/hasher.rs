use std::fs::File;
use std::io::{self, Read};
use std::path::Path;
use xxhash_rust::xxh3::xxh3_64;

pub fn compute_quick_hash_4kb(path: &Path) -> io::Result<u64> {
    let mut file = File::open(path)?;
    let mut buffer = [0u8; 4096];
    let mut total = 0;
    while total < buffer.len() {
        let n = file.read(&mut buffer[total..])?;
        if n == 0 {
            break;
        }
        total += n;
    }
    Ok(xxh3_64(&buffer[..total]))
}
