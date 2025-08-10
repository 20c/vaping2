import pytest
import vaping.plugins.fping
from vaping import plugin

# Check if Rust implementation is available
try:
    import vaping_fping
    RUST_FPING_AVAILABLE = True
except ImportError:
    RUST_FPING_AVAILABLE = False


@pytest.fixture
def fping_plugin():
    """Create an FPing plugin instance for testing"""
    config = {
        "interval": "5s",
        "count": 3,
        "period": 100,
        "use_rust": True,
    }
    return vaping.plugins.fping.FPing(config, None)


@pytest.fixture
def fping_plugin_fallback():
    """Create an FPing plugin instance that falls back to system fping"""
    config = {
        "interval": "5s",
        "count": 3,
        "period": 100,
        "use_rust": False,
        "command": "fping",
    }
    return vaping.plugins.fping.FPing(config, None)


def test_rust_fping_availability():
    """Test that we can detect Rust fping availability"""
    from vaping.plugins.fping import RUST_FPING_AVAILABLE as plugin_rust_available
    assert plugin_rust_available == RUST_FPING_AVAILABLE


@pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
def test_rust_fping_direct():
    """Test the Rust fping module directly"""
    import vaping_fping
    
    # Test with localhost (should always be available)
    results = vaping_fping.ping_hosts(["127.0.0.1"], 3, 100)
    assert len(results) == 1
    
    result = results[0]
    assert result["host"] == "127.0.0.1"
    assert result["cnt"] == 3
    assert "loss" in result
    assert "data" in result


@pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
def test_fping_plugin_rust_implementation(fping_plugin):
    """Test FPing plugin using Rust implementation"""
    assert fping_plugin.use_rust is True
    
    # Mock hosts_args to return localhost
    fping_plugin.hosts_args = lambda: ["127.0.0.1"]
    
    # Test the plugin
    data = fping_plugin._run_proc()
    assert isinstance(data, list)
    
    if data:  # If we got results (depends on network/permissions)
        result = data[0]
        assert "host" in result
        assert "cnt" in result
        assert "loss" in result


def test_fping_plugin_fallback_configuration():
    """Test that plugin correctly configures fallback mode"""
    # Test with use_rust=False
    config = {"use_rust": False, "command": "fping", "interval": "5s"}
    
    # This might raise RuntimeError if fping is not installed
    try:
        plugin = vaping.plugins.fping.FPing(config, None)
        assert plugin.use_rust is False
    except RuntimeError:
        # Expected if system fping is not available
        pytest.skip("System fping not available")


@pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
def test_fping_plugin_automatic_rust_selection():
    """Test that plugin automatically selects Rust when available"""
    config = {"use_rust": True, "interval": "5s"}  # Default is True
    plugin = vaping.plugins.fping.FPing(config, None)
    assert plugin.use_rust is True


def test_fping_schema_rust_option():
    """Test that the schema includes the use_rust option"""
    from vaping.plugins.fping import FPingSchema
    import confu.schema
    
    schema = FPingSchema()
    assert hasattr(schema, "use_rust")
    
    # Test default value
    config = {}
    confu.schema.apply_defaults(schema, config)
    assert config.get("use_rust", True) is True  # Should default to True


def test_hosts_args_deduplication(fping_plugin):
    """Test that hosts_args properly deduplicates hosts"""
    # Mock hosts with duplicates
    fping_plugin.hosts = [
        "8.8.8.8",
        {"host": "8.8.4.4"},
        "8.8.8.8",  # Duplicate
        {"host": "8.8.4.4"},  # Duplicate
    ]
    
    result = fping_plugin.hosts_args()
    assert len(result) == 2
    assert "8.8.8.8" in result
    assert "8.8.4.4" in result


@pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
def test_rust_fping_error_handling():
    """Test error handling in Rust fping"""
    import vaping_fping
    
    # Test with invalid hosts
    results = vaping_fping.ping_hosts(["invalid.nonexistent.domain"], 1, 100)
    assert len(results) == 1
    
    result = results[0]
    assert result["host"] == "invalid.nonexistent.domain"
    assert result["cnt"] == 0 or result["loss"] == 1.0  # Should show failure


@pytest.mark.skipif(not RUST_FPING_AVAILABLE, reason="Rust fping not available")
def test_rust_fping_multiple_hosts():
    """Test Rust fping with multiple hosts"""
    import vaping_fping
    
    hosts = ["127.0.0.1", "8.8.8.8"]
    results = vaping_fping.ping_hosts(hosts, 2, 100)
    
    assert len(results) == 2
    assert results[0]["host"] in hosts
    assert results[1]["host"] in hosts
    
    # Results should be in same order as input
    assert results[0]["host"] == hosts[0]
    assert results[1]["host"] == hosts[1]


def test_parse_verbose_compatibility():
    """Test that existing parse_verbose method still works for fallback"""
    fping = vaping.plugins.fping.FPing({"interval": "5s", "use_rust": False}, None)
    
    # Test with sample fping output
    test_cases = [
        "127.0.0.1 : 0.12 0.15 0.13",
        "example.com : 10.5 - 12.3",
        "unreachable.host : - - -",
    ]
    
    for line in test_cases:
        result = fping.parse_verbose(line)
        if "unreachable.host" not in line:
            assert result is not None
            assert "host" in result
            assert "cnt" in result
            assert "loss" in result