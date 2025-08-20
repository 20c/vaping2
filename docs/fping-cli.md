## fping CLI Command

Vaping includes a built-in `fping` command that provides a drop-in replacement for the traditional `fping` utility. This command leverages vaping's high-performance Rust implementation to deliver fast, reliable network ping measurements.

!!! Tip "Rust Implementation Required"
    The `vaping fping` command requires the Rust implementation to be available. Install it with:

    ```sh
    pip install vaping[rust-fping]
    ```

## Basic Usage

The `vaping fping` command accepts the same arguments and options as the standard `fping` utility, making it a perfect drop-in replacement.

### Quick Examples

**Basic host checking:**
```sh
vaping fping 8.8.8.8 1.1.1.1
```
```
8.8.8.8 is alive
1.1.1.1 is alive
```

**Count mode with statistics:**
```sh
vaping fping -c 5 google.com
```
```
google.com : xmt/rcv/%loss = 5/5/0%, min/avg/max = 12.34/15.67/20.12
```

**Verbose count mode:**
```sh
vaping fping -C 5 google.com
```
```
google.com : [0], 56 bytes, 11.4 ms (11.4 avg, 0% loss)
google.com : [1], 56 bytes, 18.8 ms (15.1 avg, 0% loss)
google.com : [2], 56 bytes, 18.3 ms (16.2 avg, 0% loss)
google.com : [3], 56 bytes, 9.21 ms (14.4 avg, 0% loss)
google.com : [4], 56 bytes, 15.5 ms (14.7 avg, 0% loss)
```

## Command Line Options

The `vaping fping` command supports all major `fping` options for compatibility:

### Probing Options

- `-c, --count N` - Count mode: send N pings to each target
- `-C, --vcount N` - Same as `-c`, but with verbose output showing individual ping times
- `-p, --period MSEC` - Interval between ping packets to one target (in ms, default: 1000)
- `-t, --timeout MSEC` - Individual target timeout (in ms, default: 1000)
- `-i, --interval MSEC` - Interval between sending ping packets (in ms, default: 10)
- `-r, --retry N` - Number of retries (default: 3)
- `-b, --size BYTES` - Amount of ping data to send (default: 56)

### Output Options

- `-a, --alive` - Show targets that are alive
- `-u, --unreach` - Show targets that are unreachable
- `-s, --stats` - Print final statistics
- `-q, --quiet` - Quiet mode (don't show per-target results)
- `-D, --timestamp` - Print timestamp before each output line
- `-e, --elapsed` - Show elapsed time on return packets
- `-v, --version` - Show version information

### Input Options

- `-f, --file FILE` - Read list of targets from a file (use `-` for stdin)

## Advanced Usage

### Reading Targets from File

Create a file with one host per line:

```sh
echo -e "8.8.8.8\n1.1.1.1\ngoogle.com" > hosts.txt
vaping fping -f hosts.txt
```

Comments (lines starting with `#`) are ignored in input files.

### Statistics Mode

Use the `-s` flag to get a summary of results:

```sh
vaping fping -s 8.8.8.8 1.1.1.1 192.0.2.1
```
```
8.8.8.8 is alive
1.1.1.1 is alive
192.0.2.1 is unreachable

     3 targets
     2 alive
     1 unreachable
```

### Alive/Unreachable Filtering

Show only alive hosts:
```sh
vaping fping -a 8.8.8.8 192.0.2.1
```
```
8.8.8.8 is alive
```

Show only unreachable hosts:
```sh
vaping fping -u 8.8.8.8 192.0.2.1
```
```
192.0.2.1 is unreachable
```

### Timestamped Output

Add timestamps to output:
```sh
vaping fping -D -e 8.8.8.8
```
```
[14:23:45] 8.8.8.8 is alive (12.34 ms)
```

## Exit Codes

The `vaping fping` command follows standard `fping` exit code conventions:

- **0** - All hosts are reachable (or when using `-a`/`-u` flags and requested hosts are found)
- **1** - Some hosts are unreachable
- **130** - Interrupted by user (Ctrl+C)

## Performance Benefits

The Rust implementation provides several advantages over traditional `fping`:

- **Better Performance** - Optimized Rust code for faster execution
- **Improved Reliability** - Enhanced error handling and timeout management
- **Integration** - Seamless integration with vaping's monitoring ecosystem
- **Compatibility** - Drop-in replacement with identical command-line interface

## Limitations

Some advanced `fping` options are not yet supported but will be ignored with a warning:

- IPv4/IPv6 specific options (`-4`, `-6`)
- Network interface binding (`-I`)
- Source address specification (`-S`)
- TTL and TOS options (`-H`, `-O`)
- Don't fragment flag (`-M`)
- Target generation (`-g`)

!!! Note "Unsupported Options"
    When unsupported options are used, `vaping fping` will display a warning message but continue execution with the supported options. This ensures compatibility with existing scripts while providing clear feedback about unsupported features.

## Integration with Vaping

While `vaping fping` works as a standalone command-line utility, it's designed to complement vaping's monitoring capabilities. The same Rust implementation powers both the standalone command and vaping's `fping` plugin, ensuring consistent performance and results across your monitoring infrastructure.

For automated monitoring and graphing, consider using vaping's daemon mode with the `fping` plugin. For manual testing and troubleshooting, `vaping fping` provides a familiar command-line interface with enhanced performance.