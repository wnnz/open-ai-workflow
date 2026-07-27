$env:HTTP_PROXY = "http://127.0.0.1:10808"
$env:HTTPS_PROXY = "http://127.0.0.1:10808"
$env:ALL_PROXY = "socks5h://127.0.0.1:10808"
$env:NO_PROXY = "localhost,127.0.0.1,postgres,redis,minio,api,worker,sandbox,document-worker"

Write-Host "Proxy enabled for this PowerShell process: $env:HTTP_PROXY"
