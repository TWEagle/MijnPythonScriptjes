# PowerShell-script om Raspberry Pi CT-domeinscan uit te voeren via SSH
# Gebruik: Rechterklik > "Run with PowerShell"

$PemPath = "C:\d\OneDrive - TWEagle\downloads\dns-keypairs.pem"
$PiUser = "ubuntu"
$PiIP = "192.168.1.120"   # <-- pas aan naar jouw Pi IP-adres

Write-Host "🚀 Verbinden met Raspberry Pi ($PiUser@$PiIP)..."
ssh -i "$PemPath" $PiUser@$PiIP "cd ~/ct-scanner && source venv/bin/activate && python3 get_ct_domains.py"
