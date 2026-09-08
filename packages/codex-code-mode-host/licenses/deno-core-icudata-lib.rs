#[repr(C, align(16))]
struct IcuData<T: ?Sized>(T);

static ICU_DATA_RAW: &'static IcuData<[u8]> = &IcuData(*include_bytes!("icudtl.dat"));

/// Raw ICU data.
pub static ICU_DATA: &[u8] = &ICU_DATA_RAW.0;
