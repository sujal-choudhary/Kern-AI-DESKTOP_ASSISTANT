from core.powershell_mode import PowerShellConfirmManager, PendingPowerShell, confirm_allowed, is_risky_powershell


def test_risky_detection():
    assert is_risky_powershell("Remove-Item C:\\temp\\x.txt") is True
    assert is_risky_powershell("Get-Process | Select -First 1") is False


def test_confirm_allowed_normal_command():
    pending = PendingPowerShell(command="Get-Process", risky=False, created_at=0.0)
    allowed, _ = confirm_allowed(pending, passphrase="")
    assert allowed is True


def test_manager_creates_pending():
    mgr = PowerShellConfirmManager()
    nonce, pending = mgr.create_pending("Get-Process")
    assert len(nonce) == 24
    assert pending.command == "Get-Process"
    assert mgr.get(nonce) is not None
