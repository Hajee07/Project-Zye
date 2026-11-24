import subprocess

script = """
try {
    $events = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625} -MaxEvents 2 -ErrorAction Stop
    foreach ($e in $events) {
        $e.ToXml()
    }
} catch {
    Write-Host "ERROR:" $_.Exception.Message
}
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=10)
print("STDOUT:\n", res.stdout[:500])
print("STDERR:\n", res.stderr[:500])
