#!/usr/bin/env python3

import sys
import time
from typing import List

import click


def format_time_ms(ms: float) -> str:
    """Format time in milliseconds like original fping"""
    return f"{ms:.2f}"


class FpingCompat:
    """fping-compatible wrapper for the Rust implementation"""

    def __init__(self):
        self.show_alive = False
        self.show_unreachable = False
        self.quiet = False
        self.stats = False
        self.timestamp = False
        self.elapsed = False
        self.count_mode = False
        self.verbose_count = False
        self.loop_mode = False
        self.timeout = 1000  # ms
        self.period = 1000  # ms between packets to same target
        self.interval = 10  # ms between packets in general
        self.retry = 3
        self.size = 56  # ping data size

    def ping_hosts(self, hosts: List[str], count: int) -> List[dict]:
        """Call the Rust fping implementation"""
        try:
            import vaping_fping

            return vaping_fping.ping_hosts(hosts, count, self.period, self.timeout)
        except ImportError:
            click.echo(
                "fping: Rust fping implementation not available. Install with: pip install vaping[rust-fping]",
                err=True,
            )
            sys.exit(1)

    def format_output(self, results: List[dict], hosts: List[str]) -> None:
        """Format output like original fping"""

        if self.count_mode or self.verbose_count:
            # Count mode output - show real-time ping results with cumulative stats
            for result in results:
                host = result["host"]
                count = result.get("cnt", 0)
                loss = result.get("loss", 1.0)
                times = result.get("data", [])
                size = self.size  # Use configured packet size

                if self.verbose_count:
                    # Verbose count mode (-C) shows individual pings with cumulative stats
                    running_sum = 0.0
                    received_count = 0

                    for i, ping_time in enumerate(times):
                        running_sum += ping_time
                        received_count += 1
                        running_avg = running_sum / received_count
                        current_loss = ((i + 1) - received_count) / (i + 1) * 100

                        if self.timestamp:
                            timestamp = time.strftime("[%H:%M:%S]")
                            click.echo(
                                f"{timestamp} {host} : [{i}], {size} bytes, {format_time_ms(ping_time)} ms ({format_time_ms(running_avg)} avg, {current_loss:.0f}% loss)"
                            )
                        else:
                            click.echo(
                                f"{host} : [{i}], {size} bytes, {format_time_ms(ping_time)} ms ({format_time_ms(running_avg)} avg, {current_loss:.0f}% loss)"
                            )

                    # Handle unreachable pings (if count > len(times))
                    for i in range(len(times), count):
                        current_loss = ((i + 1) - received_count) / (i + 1) * 100
                        if received_count > 0:
                            running_avg = running_sum / received_count
                            avg_str = f"{format_time_ms(running_avg)} avg"
                        else:
                            avg_str = "- avg"

                        if self.timestamp:
                            timestamp = time.strftime("[%H:%M:%S]")
                            click.echo(
                                f"{timestamp} {host} : [{i}], timed out ({avg_str}, {current_loss:.0f}% loss)"
                            )
                        else:
                            click.echo(
                                f"{host} : [{i}], timed out ({avg_str}, {current_loss:.0f}% loss)"
                            )
                else:
                    # Regular count mode (-c) - just show summary
                    if count > 0:
                        min_time = result.get("min", 0)
                        avg_time = result.get("avg", 0)
                        max_time = result.get("max", 0)
                        loss_pct = loss * 100
                        click.echo(
                            f"{host} : xmt/rcv/%loss = {count}/{len(times)}/{loss_pct:.0f}%, min/avg/max = {format_time_ms(min_time)}/{format_time_ms(avg_time)}/{format_time_ms(max_time)}"
                        )
                    else:
                        click.echo(f"{host} : xmt/rcv/%loss = 0/0/100%")
        else:
            # Standard mode - show alive/unreachable status
            for result in results:
                host = result["host"]
                loss = result.get("loss", 1.0)
                avg_time = result.get("avg")

                if loss < 1.0:  # Host is alive
                    if self.show_alive or (
                        not self.show_unreachable and not self.quiet
                    ):
                        if self.elapsed and avg_time is not None:
                            if self.timestamp:
                                timestamp = time.strftime("[%H:%M:%S]")
                                click.echo(
                                    f"{timestamp} {host} is alive ({format_time_ms(avg_time)} ms)"
                                )
                            else:
                                click.echo(
                                    f"{host} is alive ({format_time_ms(avg_time)} ms)"
                                )
                        else:
                            if self.timestamp:
                                timestamp = time.strftime("[%H:%M:%S]")
                                click.echo(f"{timestamp} {host} is alive")
                            else:
                                click.echo(f"{host} is alive")
                else:  # Host is unreachable
                    if self.show_unreachable or (
                        not self.show_alive and not self.quiet
                    ):
                        if self.timestamp:
                            timestamp = time.strftime("[%H:%M:%S]")
                            click.echo(f"{timestamp} {host} is unreachable")
                        else:
                            click.echo(f"{host} is unreachable")

        if self.stats:
            # Print final statistics
            total_hosts = len(results)
            alive_hosts = sum(1 for r in results if r.get("loss", 1.0) < 1.0)
            unreachable_hosts = total_hosts - alive_hosts

            click.echo()
            click.echo(f"     {total_hosts} targets")
            click.echo(f"     {alive_hosts} alive")
            click.echo(f"     {unreachable_hosts} unreachable")


@click.command(
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True)
)
@click.argument("targets", nargs=-1)
@click.option("-4", "--ipv4", is_flag=True, help="only ping IPv4 addresses")
@click.option("-6", "--ipv6", is_flag=True, help="only ping IPv6 addresses")
@click.option("-a", "--alive", is_flag=True, help="show targets that are alive")
@click.option("-A", "--addr", is_flag=True, help="show targets by address")
@click.option(
    "-b",
    "--size",
    type=int,
    default=56,
    help="amount of ping data to send, in bytes (default: 56)",
)
@click.option(
    "-B",
    "--backoff",
    type=float,
    default=1.5,
    help="set exponential backoff factor to N (default: 1.5)",
)
@click.option("-c", "--count", type=int, help="count mode: send N pings to each target")
@click.option(
    "-C", "--vcount", type=int, help="same as -c, report results in verbose format"
)
@click.option(
    "-d", "--rdns", is_flag=True, help="show targets by name (force reverse-DNS lookup)"
)
@click.option(
    "-D", "--timestamp", is_flag=True, help="print timestamp before each output line"
)
@click.option(
    "-e", "--elapsed", is_flag=True, help="show elapsed time on return packets"
)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    help="read list of targets from a file ( - means stdin)",
)
@click.option("-g", "--generate", is_flag=True, help="generate target list")
@click.option("-H", "--ttl", type=int, help="set the IP TTL value (Time To Live hops)")
@click.option(
    "-i",
    "--interval",
    type=int,
    default=10,
    help="interval between sending ping packets (default: 10 ms)",
)
@click.option("-I", "--iface", help="bind to a particular interface")
@click.option("-l", "--loop", is_flag=True, help="loop mode: send pings forever")
@click.option(
    "-m",
    "--all",
    is_flag=True,
    help="use all IPs of provided hostnames (e.g. IPv4 and IPv6), use with -A",
)
@click.option("-M", "--dontfrag", is_flag=True, help="set the Don't Fragment flag")
@click.option(
    "-n",
    "--name",
    is_flag=True,
    help="show targets by name (reverse-DNS lookup for target IPs)",
)
@click.option(
    "-N",
    "--netdata",
    is_flag=True,
    help="output compatible for netdata (-l -Q are required)",
)
@click.option(
    "-o",
    "--outage",
    is_flag=True,
    help="show the accumulated outage time (lost packets * packet interval)",
)
@click.option(
    "-O",
    "--tos",
    type=int,
    help="set the type of service (tos) flag on the ICMP packets",
)
@click.option(
    "-p",
    "--period",
    type=int,
    default=1000,
    help="interval between ping packets to one target (in ms)",
)
@click.option(
    "-q", "--quiet", is_flag=True, help="quiet (don't show per-target/per-ping results)"
)
@click.option(
    "-Q",
    "--squiet",
    type=int,
    help="same as -q, but add interval summary every SECS seconds",
)
@click.option(
    "-r", "--retry", type=int, default=3, help="number of retries (default: 3)"
)
@click.option(
    "-R",
    "--random",
    is_flag=True,
    help="random packet data (to foil link data compression)",
)
@click.option("-s", "--stats", is_flag=True, help="print final stats")
@click.option("-S", "--src", help="set source address")
@click.option(
    "-t",
    "--timeout",
    type=int,
    default=1000,
    help="individual target initial timeout (default: 1000 ms)",
)
@click.option("-u", "--unreach", is_flag=True, help="show targets that are unreachable")
@click.option("-v", "--version", is_flag=True, help="show version")
@click.option(
    "-x", "--reachable", type=int, help="shows if >=N hosts are reachable or not"
)
def fping_cli(targets, **kwargs):
    """Fast ping multiple hosts using Rust implementation.

    This is a drop-in replacement for fping that uses vaping's Rust implementation.
    Most fping options are supported for compatibility.
    """

    if kwargs.get("version"):
        click.echo("fping (vaping): version 1.5.4")
        click.echo("Rust-based implementation for improved performance")
        return

    # Handle file input
    host_list = list(targets)
    if kwargs.get("file"):
        for line in kwargs["file"]:
            line = line.strip()
            if line and not line.startswith("#"):
                host_list.append(line)

    if not host_list:
        click.echo("fping: no targets specified", err=True)
        sys.exit(1)

    # Set up fping compatibility wrapper
    fping = FpingCompat()
    fping.show_alive = kwargs.get("alive", False)
    fping.show_unreachable = kwargs.get("unreach", False)
    fping.quiet = kwargs.get("quiet", False)
    fping.stats = kwargs.get("stats", False)
    fping.timestamp = kwargs.get("timestamp", False)
    fping.elapsed = kwargs.get("elapsed", False)
    fping.period = kwargs.get("period", 1000)
    fping.interval = kwargs.get("interval", 10)
    fping.timeout = kwargs.get("timeout", 1000)
    fping.retry = kwargs.get("retry", 3)
    fping.size = kwargs.get("size", 56)

    # Determine mode and count
    count = kwargs.get("count")
    vcount = kwargs.get("vcount")
    loop_mode = kwargs.get("loop", False)

    if vcount:
        fping.verbose_count = True
        fping.count_mode = True
        count = vcount
    elif count:
        fping.count_mode = True
    elif loop_mode:
        fping.loop_mode = True
        count = 1  # For now, just do one ping in loop mode
    else:
        # Default mode - single ping
        count = 1

    # Warn about unsupported options
    unsupported = []
    if kwargs.get("ipv4"):
        unsupported.append("-4/--ipv4")
    if kwargs.get("ipv6"):
        unsupported.append("-6/--ipv6")
    if kwargs.get("generate"):
        unsupported.append("-g/--generate")
    if kwargs.get("ttl"):
        unsupported.append("-H/--ttl")
    if kwargs.get("iface"):
        unsupported.append("-I/--iface")
    if kwargs.get("dontfrag"):
        unsupported.append("-M/--dontfrag")
    if kwargs.get("tos"):
        unsupported.append("-O/--tos")
    if kwargs.get("random"):
        unsupported.append("-R/--random")
    if kwargs.get("src"):
        unsupported.append("-S/--src")

    if unsupported and not fping.quiet:
        click.echo(
            f"fping: warning: unsupported options ignored: {', '.join(unsupported)}",
            err=True,
        )

    try:
        results = fping.ping_hosts(host_list, count)
        fping.format_output(results, host_list)

        # Exit code logic like original fping
        if fping.show_alive or fping.show_unreachable:
            # In alive/unreachable mode, exit 0 if any requested hosts found
            if fping.show_alive:
                alive_count = sum(1 for r in results if r.get("loss", 1.0) < 1.0)
                sys.exit(0 if alive_count > 0 else 1)
            else:
                unreachable_count = sum(1 for r in results if r.get("loss", 1.0) >= 1.0)
                sys.exit(0 if unreachable_count > 0 else 1)
        else:
            # Normal mode - exit 0 if all hosts reachable, 1 if any unreachable
            unreachable_count = sum(1 for r in results if r.get("loss", 1.0) >= 1.0)
            sys.exit(1 if unreachable_count > 0 else 0)

    except KeyboardInterrupt:
        click.echo("\nfping: interrupted", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"fping: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    fping_cli()
