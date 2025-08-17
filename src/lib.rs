use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::process::Command;
use std::time::{Duration, Instant};

#[derive(Debug, Clone)]
pub struct PingResult {
    pub host: String,
    pub times: Vec<f64>,
    pub count: usize,
    pub loss: f64,
    pub min: Option<f64>,
    pub max: Option<f64>,
    pub avg: Option<f64>,
    pub last: Option<f64>,
}

impl PingResult {
    fn new(host: String) -> Self {
        Self {
            host,
            times: Vec::new(),
            count: 0,
            loss: 0.0,
            min: None,
            max: None,
            avg: None,
            last: None,
        }
    }

    fn add_time(&mut self, time: f64) {
        self.times.push(time);

        // Update statistics
        let times = &self.times;
        if !times.is_empty() {
            self.min = Some(times.iter().fold(f64::INFINITY, |a, &b| a.min(b)));
            self.max = Some(times.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b)));
            self.avg = Some(times.iter().sum::<f64>() / times.len() as f64);
            self.last = times.last().copied();
        }
    }

    fn set_loss(&mut self, sent: usize) {
        self.count = sent;
        if sent > 0 {
            self.loss = (sent - self.times.len()) as f64 / sent as f64;
        } else {
            self.loss = 0.0;
        }
    }
}

pub struct RustFping {
    count: usize,
    period_ms: u64,
    timeout_ms: u64,
}

impl RustFping {
    pub fn new(count: usize, period_ms: u64, timeout_ms: u64) -> Self {
        Self { count, period_ms, timeout_ms }
    }

    pub fn ping_hosts(&self, hosts: Vec<String>) -> Vec<PingResult> {
        let mut results = Vec::new();

        for host in hosts {
            let result = self.ping_host(&host);
            results.push(result);
        }

        results
    }

    fn ping_host(&self, host: &str) -> PingResult {
        let mut result = PingResult::new(host.to_string());

        // For this simplified version, we'll use the system ping command
        // This avoids raw socket permission issues while still providing
        // a Rust implementation that can be extended later

        let mut sent_count = 0;

        for _sequence in 0..self.count {
            let start_time = Instant::now();

            // Use system ping command with timeout
            // Convert milliseconds to seconds for ping -W option
            let timeout_seconds = (self.timeout_ms as f64 / 1000.0).to_string();
            let output = Command::new("ping")
                .args(&[
                    "-c", "1",              // Send only 1 ping
                    "-W", &timeout_seconds, // Use configured timeout in seconds
                    host
                ])
                .output();

            match output {
                Ok(output) if output.status.success() => {
                    sent_count += 1;
                    let elapsed = start_time.elapsed().as_secs_f64() * 1000.0;

                    // Try to parse the actual ping time from output if available
                    if let Ok(stdout) = String::from_utf8(output.stdout) {
                        if let Some(time) = self.parse_ping_time(&stdout) {
                            result.add_time(time);
                        } else {
                            // Fallback to elapsed time
                            result.add_time(elapsed);
                        }
                    } else {
                        result.add_time(elapsed);
                    }
                }
                Ok(_) => {
                    // Ping failed but command ran
                    sent_count += 1;
                }
                Err(_) => {
                    // Command failed to run - this is a system error
                    break;
                }
            }

            // Wait period between pings
            if _sequence < self.count - 1 {
                std::thread::sleep(Duration::from_millis(self.period_ms));
            }
        }

        result.set_loss(sent_count);
        result
    }

    fn parse_ping_time(&self, output: &str) -> Option<f64> {
        // Parse ping output to extract the actual ping time
        // Look for patterns like "time=1.23ms" or "time=1.23 ms"
        for line in output.lines() {
            if let Some(time_pos) = line.find("time=") {
                let time_str = &line[time_pos + 5..];
                if let Some(space_pos) = time_str.find(' ') {
                    let time_part = &time_str[..space_pos];
                    if let Ok(time) = time_part.parse::<f64>() {
                        return Some(time);
                    }
                } else if let Some(ms_pos) = time_str.find("ms") {
                    let time_part = &time_str[..ms_pos];
                    if let Ok(time) = time_part.parse::<f64>() {
                        return Some(time);
                    }
                }
            }
        }
        None
    }
}

/// Python interface
#[pyfunction]
#[pyo3(signature = (hosts, count, period, timeout=None))]
fn ping_hosts(hosts: Vec<String>, count: usize, period: u64, timeout: Option<u64>) -> PyResult<Vec<PyObject>> {
    let timeout_ms = timeout.unwrap_or(1000); // Default 1000ms timeout like original fping
    let fping = RustFping::new(count, period, timeout_ms);
    let results = fping.ping_hosts(hosts);

    Python::with_gil(|py| {
        let py_results = results.into_iter().map(|result| {
            let dict = PyDict::new_bound(py);
            dict.set_item("host", result.host)?;
            dict.set_item("cnt", result.count)?;
            dict.set_item("loss", result.loss)?;
            dict.set_item("data", result.times)?;

            if let Some(min) = result.min {
                dict.set_item("min", min)?;
            }
            if let Some(max) = result.max {
                dict.set_item("max", max)?;
            }
            if let Some(avg) = result.avg {
                dict.set_item("avg", avg)?;
            }
            if let Some(last) = result.last {
                dict.set_item("last", last)?;
            }

            Ok(dict.into())
        }).collect::<PyResult<Vec<PyObject>>>()?;

        Ok(py_results)
    })
}

#[pymodule]
fn vaping_fping(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ping_hosts, m)?)?;
    Ok(())
}