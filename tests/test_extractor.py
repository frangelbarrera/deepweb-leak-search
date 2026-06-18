"""Tests for the IOC extraction engine."""

import pytest
from app.core.extractor import extract_iocs


class TestIPv4:
    def test_single_ip(self):
        result = extract_iocs("192.168.1.1")
        assert {"type": "ipv4", "value": "192.168.1.1"} in result

    def test_multiple_ips(self):
        text = "10.0.0.1 and 172.16.0.1"
        iocs = extract_iocs(text)
        values = {ioc["value"] for ioc in iocs if ioc["type"] == "ipv4"}
        assert "10.0.0.1" in values
        assert "172.16.0.1" in values

    def test_ipv4_regex_matches_any_octet(self):
        """Regex matches any X.X.X.X pattern; octet-range validation is not performed."""
        result = extract_iocs("999.999.999.999")
        ipv4s = [ioc for ioc in result if ioc["type"] == "ipv4"]
        assert len(ipv4s) == 1  # matched by regex, even though invalid

    def test_deduplication(self):
        result = extract_iocs("1.2.3.4 1.2.3.4 1.2.3.4")
        ipv4s = [ioc for ioc in result if ioc["type"] == "ipv4"]
        assert len(ipv4s) == 1

    def test_openphish_format(self):
        text = "http://8.14.0.0/phish  http://45.33.32.156/login"
        result = extract_iocs(text)
        ipv4s = {ioc["value"] for ioc in result if ioc["type"] == "ipv4"}
        assert "8.14.0.0" in ipv4s
        assert "45.33.32.156" in ipv4s


class TestDomain:
    def test_simple_domain(self):
        result = extract_iocs("example.com")
        domains = {ioc["value"] for ioc in result if ioc["type"] == "domain"}
        assert "example.com" in domains

    def test_subdomain(self):
        result = extract_iocs("phishing.login.example.com")
        domains = [ioc for ioc in result if ioc["type"] == "domain"]
        assert len(domains) >= 1

    def test_openphish_domains(self):
        text = "graces-japan.com xyz-login.net secure-update.org"
        result = extract_iocs(text)
        domains = {ioc["value"] for ioc in result if ioc["type"] == "domain"}
        assert "graces-japan.com" in domains
        assert "xyz-login.net" in domains
        assert "secure-update.org" in domains

    def test_urls_yield_domains(self):
        text = "https://evil.com/phish?user=test"
        result = extract_iocs(text)
        domains = {ioc["value"] for ioc in result if ioc["type"] == "domain"}
        assert "evil.com" in domains


class TestMD5:
    def test_valid_md5(self):
        result = extract_iocs("7637c72493b5d7d70b702dbb9706d9d6")
        assert {"type": "md5", "value": "7637c72493b5d7d70b702dbb9706d9d6"} in result

    def test_invalid_length(self):
        result = extract_iocs("abc123")
        md5s = [ioc for ioc in result if ioc["type"] == "md5"]
        assert len(md5s) == 0

    def test_mixed_case(self):
        result = extract_iocs("AbC1234567890DeF1234567890aBcDeF")
        md5s = [ioc for ioc in result if ioc["type"] == "md5"]
        assert len(md5s) == 1


class TestSHA256:
    def test_valid_sha256(self):
        sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        result = extract_iocs(sha)
        assert {"type": "sha256", "value": sha} in result

    def test_not_md5_length(self):
        """64-char hex should be classified as sha256, not md5."""
        sha = "a" * 64
        result = extract_iocs(sha)
        types = {ioc["type"] for ioc in result}
        assert "sha256" in types


class TestEmail:
    def test_simple_email(self):
        result = extract_iocs("user@example.com")
        assert {"type": "email", "value": "user@example.com"} in result

    def test_plus_addressing(self):
        result = extract_iocs("user+tag@domain.co.uk")
        emails = [ioc for ioc in result if ioc["type"] == "email"]
        assert len(emails) == 1

    def test_not_a_domain(self):
        """Ensure emails are not double-counted as domains."""
        result = extract_iocs("admin@phish.net")
        domains = {ioc["value"] for ioc in result if ioc["type"] == "domain"}
        assert "admin@phish.net" not in domains  # shouldn't match as plain domain


class TestBTCWallet:
    def test_p2pkh(self):
        result = extract_iocs("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert {"type": "btc_wallet", "value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"} in result

    def test_p2sh(self):
        result = extract_iocs("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy")
        assert {"type": "btc_wallet", "value": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"} in result

    def test_bech32(self):
        result = extract_iocs("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        btc = [ioc for ioc in result if ioc["type"] == "btc_wallet"]
        assert len(btc) == 1


class TestXMRWallet:
    def test_valid_xmr(self):
        addr = "4AdUndXHH3zBqk3YqRXUJKqR88QhYKLn7NogH8bXWiEEPLUMJsLGJpBLqC7hPzQqW3MoBgqU8NpLCRVKNZ5cX4mcUWbhT3m"
        result = extract_iocs(addr)
        assert {"type": "xmr_wallet", "value": addr} in result

    def test_invalid_xmr(self):
        result = extract_iocs("4abc123")
        xmr = [ioc for ioc in result if ioc["type"] == "xmr_wallet"]
        assert len(xmr) == 0


class TestEdgeCases:
    def test_empty_string(self):
        assert extract_iocs("") == []

    def test_none_input(self):
        assert extract_iocs(None) == []  # type: ignore

    def test_plain_text_no_iocs(self):
        result = extract_iocs("Hello world! Nothing to see here.")
        assert result == []

    def test_firehol_netset_format(self):
        text = "# FireHOL Level 1\n10.0.0.0/8\n172.16.0.0/12\n192.168.0.0/16"
        result = extract_iocs(text)
        ipv4s = {ioc["value"] for ioc in result if ioc["type"] == "ipv4"}
        assert "10.0.0.0" in ipv4s
        assert "172.16.0.0" in ipv4s
        assert "192.168.0.0" in ipv4s
