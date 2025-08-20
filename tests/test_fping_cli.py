import pytest
from unittest.mock import patch
from click.testing import CliRunner

from vaping.fping_cli import fping_cli, FpingCompat

# Check if vaping_fping is available
try:
    import vaping_fping  # noqa: F401

    RUST_FPING_AVAILABLE = True
except ImportError:
    RUST_FPING_AVAILABLE = False


@pytest.fixture
def runner():
    """Click test runner"""
    return CliRunner()


class TestFpingCompat:
    """Test the FpingCompat wrapper class"""

    def test_init_defaults(self):
        """Test FpingCompat initializes with correct defaults"""
        fping = FpingCompat()
        assert fping.show_alive is False
        assert fping.show_unreachable is False
        assert fping.quiet is False
        assert fping.stats is False
        assert fping.timeout == 1000
        assert fping.period == 1000
        assert fping.retry == 3
        assert fping.size == 56

    @pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
    def test_ping_hosts_calls_rust_implementation(self):
        """Test that ping_hosts calls the Rust implementation correctly"""
        fping = FpingCompat()
        fping.period = 2000

        # This will call the real implementation if available
        result = fping.ping_hosts(["127.0.0.1"], 1)

        # Basic validation that we got a result
        assert isinstance(result, list)
        if result:  # If localhost is reachable
            assert "host" in result[0]
            assert result[0]["host"] == "127.0.0.1"

    def test_ping_hosts_import_error(self):
        """Test that ping_hosts handles ImportError correctly"""
        # Mock the import to force an ImportError
        with patch.dict("sys.modules", {"vaping_fping": None}):
            fping = FpingCompat()
            with pytest.raises(SystemExit) as exc_info:
                fping.ping_hosts(["8.8.8.8"], 1)
            assert exc_info.value.code == 1


class TestFpingCliBasic:
    """Test basic fping CLI functionality"""

    def test_version_flag(self, runner):
        """Test --version flag displays version information"""
        result = runner.invoke(fping_cli, ["-v"])
        assert result.exit_code == 0
        assert "fping (vaping): version 1.5.4" in result.output
        assert "Rust-based implementation" in result.output

    def test_no_targets_error(self, runner):
        """Test that command fails when no targets specified"""
        result = runner.invoke(fping_cli, [])
        assert result.exit_code == 1
        assert "no targets specified" in result.output

    def test_help_displays_all_options(self, runner):
        """Test that --help displays all fping-compatible options"""
        result = runner.invoke(fping_cli, ["--help"])
        assert result.exit_code == 0

        # Check for key fping options
        expected_options = [
            "-c, --count",
            "-C, --vcount",
            "-a, --alive",
            "-u, --unreach",
            "-s, --stats",
            "-q, --quiet",
            "-D, --timestamp",
            "-e, --elapsed",
            "-p, --period",
            "-i, --interval",
            "-t, --timeout",
        ]

        for option in expected_options:
            assert option in result.output


class TestFpingCliWithRealModule:
    """Test fping CLI with real Rust module if available"""

    @pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
    def test_basic_alive_mode(self, runner):
        """Test basic mode shows 'is alive' for reachable hosts"""
        result = runner.invoke(fping_cli, ["127.0.0.1"])

        assert result.exit_code == 0
        assert "127.0.0.1 is alive" in result.output

    @pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
    def test_count_mode(self, runner):
        """Test count mode (-c) shows statistics"""
        result = runner.invoke(fping_cli, ["-c", "2", "127.0.0.1"])

        assert result.exit_code == 0
        assert "xmt/rcv/%loss" in result.output
        assert "min/avg/max" in result.output

    @pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
    def test_verbose_count_mode(self, runner):
        """Test verbose count mode (-C) shows individual pings"""
        result = runner.invoke(fping_cli, ["-C", "2", "127.0.0.1"])

        assert result.exit_code == 0
        assert "127.0.0.1 : [0]" in result.output
        assert "127.0.0.1 : [1]" in result.output
        assert "bytes" in result.output  # New format shows bytes
        assert "avg" in result.output  # New format shows running average

    @pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
    def test_stats_flag(self, runner):
        """Test -s flag shows final statistics"""
        result = runner.invoke(fping_cli, ["-s", "127.0.0.1"])

        assert result.exit_code == 0
        assert "1 targets" in result.output
        assert "alive" in result.output

    @pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
    def test_quiet_mode(self, runner):
        """Test -q flag suppresses normal output"""
        result = runner.invoke(fping_cli, ["-q", "127.0.0.1"])

        assert result.exit_code == 0
        assert result.output.strip() == ""  # Should be no output in quiet mode


class TestFpingCliWithMockModule:
    """Test fping CLI with mocked results for specific scenarios"""

    def test_alive_flag_with_mixed_results(self, runner):
        """Test -a flag only shows alive hosts"""
        mock_results = [
            {
                "host": "8.8.8.8",
                "cnt": 1,
                "loss": 0.0,
                "data": [5.5],
                "min": 5.5,
                "max": 5.5,
                "avg": 5.5,
                "last": 5.5,
            },
            {
                "host": "192.0.2.1",
                "cnt": 1,
                "loss": 1.0,
                "data": [],
            },
        ]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            result = runner.invoke(fping_cli, ["-a", "8.8.8.8", "192.0.2.1"])

            assert result.exit_code == 0
            assert "8.8.8.8 is alive" in result.output
            assert "192.0.2.1" not in result.output

    def test_unreachable_flag_with_mixed_results(self, runner):
        """Test -u flag only shows unreachable hosts"""
        mock_results = [
            {
                "host": "8.8.8.8",
                "cnt": 1,
                "loss": 0.0,
                "data": [5.5],
                "min": 5.5,
                "max": 5.5,
                "avg": 5.5,
                "last": 5.5,
            },
            {
                "host": "192.0.2.1",
                "cnt": 1,
                "loss": 1.0,
                "data": [],
            },
        ]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            result = runner.invoke(fping_cli, ["-u", "8.8.8.8", "192.0.2.1"])

            assert result.exit_code == 0
            assert "8.8.8.8" not in result.output
            assert "192.0.2.1 is unreachable" in result.output

    def test_timestamp_mode(self, runner):
        """Test -D flag adds timestamps"""
        mock_results = [
            {"host": "8.8.8.8", "cnt": 1, "loss": 0.0, "data": [5.5], "avg": 5.5}
        ]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            with patch("vaping.fping_cli.time.strftime", return_value="[12:34:56]"):
                result = runner.invoke(fping_cli, ["-D", "8.8.8.8"])

        assert result.exit_code == 0
        assert "[12:34:56] 8.8.8.8 is alive" in result.output

    def test_elapsed_mode(self, runner):
        """Test -e flag shows elapsed time"""
        mock_results = [
            {"host": "8.8.8.8", "cnt": 1, "loss": 0.0, "data": [5.5], "avg": 5.5}
        ]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            result = runner.invoke(fping_cli, ["-e", "8.8.8.8"])

        assert result.exit_code == 0
        assert "8.8.8.8 is alive (5.50 ms)" in result.output


class TestFpingCliOptions:
    """Test fping CLI option handling"""

    @pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
    def test_file_input(self, runner):
        """Test reading targets from file (-f)"""
        with runner.isolated_filesystem():
            with open("hosts.txt", "w") as f:
                f.write("127.0.0.1\n# This is a comment\n")

            result = runner.invoke(fping_cli, ["-f", "hosts.txt"])

            assert result.exit_code == 0
            assert "127.0.0.1 is alive" in result.output

    def test_unsupported_options_warning(self, runner):
        """Test that unsupported options show warnings"""
        mock_results = [{"host": "8.8.8.8", "cnt": 1, "loss": 0.0, "data": [5.5]}]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            result = runner.invoke(fping_cli, ["-4", "-S", "1.2.3.4", "8.8.8.8"])

        assert result.exit_code == 0
        assert "warning: unsupported options ignored" in result.output
        assert "-4/--ipv4" in result.output
        assert "-S/--src" in result.output


class TestFpingCliExitCodes:
    """Test fping CLI exit code behavior"""

    def test_exit_code_all_alive(self, runner):
        """Test exit code 0 when all hosts are alive"""
        mock_results = [{"host": "8.8.8.8", "cnt": 1, "loss": 0.0, "data": [5.5]}]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            result = runner.invoke(fping_cli, ["8.8.8.8"])
        assert result.exit_code == 0

    def test_exit_code_some_unreachable(self, runner):
        """Test exit code 1 when some hosts are unreachable"""
        mock_results = [
            {"host": "8.8.8.8", "cnt": 1, "loss": 0.0, "data": [5.5]},
            {"host": "192.0.2.1", "cnt": 1, "loss": 1.0, "data": []},
        ]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            result = runner.invoke(fping_cli, ["8.8.8.8", "192.0.2.1"])
        assert result.exit_code == 1

    def test_exit_code_alive_mode(self, runner):
        """Test exit code in -a mode (exit 0 if any alive hosts found)"""
        mock_results = [
            {"host": "8.8.8.8", "cnt": 1, "loss": 0.0, "data": [5.5]},
            {"host": "192.0.2.1", "cnt": 1, "loss": 1.0, "data": []},
        ]

        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", return_value=mock_results
        ):
            result = runner.invoke(fping_cli, ["-a", "8.8.8.8", "192.0.2.1"])
        assert result.exit_code == 0  # Should be 0 because at least one host is alive


class TestFpingCliErrorHandling:
    """Test fping CLI error handling"""

    def test_import_error_handling(self, runner):
        """Test graceful handling when Rust implementation not available"""
        # Mock the import to force an ImportError
        with patch.dict("sys.modules", {"vaping_fping": None}):
            result = runner.invoke(fping_cli, ["8.8.8.8"])

            assert result.exit_code == 1
            assert "Rust fping implementation not available" in result.output
            assert "pip install vaping[rust-fping]" in result.output

    def test_keyboard_interrupt_handling(self, runner):
        """Test graceful handling of KeyboardInterrupt"""
        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts", side_effect=KeyboardInterrupt()
        ):
            result = runner.invoke(fping_cli, ["8.8.8.8"])

            assert result.exit_code == 130
            assert "interrupted" in result.output

    def test_general_exception_handling(self, runner):
        """Test graceful handling of general exceptions"""
        with patch(
            "vaping.fping_cli.FpingCompat.ping_hosts",
            side_effect=Exception("Test error"),
        ):
            result = runner.invoke(fping_cli, ["8.8.8.8"])

            assert result.exit_code == 1
            assert "Test error" in result.output


class TestFpingFormatters:
    """Test output formatting functions"""

    def test_format_time_ms(self):
        """Test time formatting function"""
        from vaping.fping_cli import format_time_ms

        assert format_time_ms(5.555) == "5.55"  # Rounds to 2 decimal places
        assert format_time_ms(10.1) == "10.10"
        assert format_time_ms(0.123) == "0.12"

    def test_format_output_packet_loss(self):
        """Test output formatting for hosts with packet loss"""
        fping = FpingCompat()
        fping.count_mode = True

        results = [
            {
                "host": "192.0.2.1",
                "cnt": 3,
                "loss": 1.0,  # 100% loss
                "data": [],
            }
        ]

        # Capture output
        import io
        import sys

        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            fping.format_output(results, ["192.0.2.1"])
            output = captured_output.getvalue()
        finally:
            sys.stdout = original_stdout

        assert "xmt/rcv/%loss = 3/0/100%" in output
