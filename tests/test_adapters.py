from net_troubleshooter.core.adapters import Diagnostics


def test_default_gateway_parser_finds_gateway():
    output = "default via 192.168.1.1 dev wlan0 proto dhcp metric 600\n192.168.1.0/24 dev wlan0 proto kernel"
    assert Diagnostics.default_gateway_from_output(output) == "192.168.1.1"


def test_default_gateway_parser_handles_missing_gateway():
    assert Diagnostics.default_gateway_from_output("192.168.1.0/24 dev wlan0 proto kernel") is None
