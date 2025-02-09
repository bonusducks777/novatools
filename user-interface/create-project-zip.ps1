$source = $PSScriptRoot
$destination = Join-Path -Path $PSScriptRoot -ChildPath "crypto-ai-suite.zip"

$exclude = @(
    '*.zip',
    'node_modules',
    '.next',
    '.git',
    '*.log',
    '*.tmp'
)

if (Test-Path $destination) {
    Remove-Item $destination -Force
}

$files = Get-ChildItem -Path $source -Exclude $exclude -Recurse

try {
    $files | Compress-Archive -DestinationPath $destination -CompressionLevel Fastest
    Write-Host "Project has been successfully zipped to $destination"
} catch {
    Write-Host "An error occurred while creating the zip file: $_"
}

# Verify the contents of the zip file
Write-Host "`nVerifying zip contents:"
try {
    $zipEntries = (Get-ChildItem $destination).BaseName | ForEach-Object { 
        (Expand-Archive -Path $destination -DestinationPath "$env:TEMP\temp-extract" -Force -PassThru).FullName 
    }
    Get-ChildItem "$env:TEMP\temp-extract" -Recurse | ForEach-Object { $_.FullName.Replace("$env:TEMP\temp-extract\", "") }
    Remove-Item "$env:TEMP\temp-extract" -Recurse -Force
} catch {
    Write-Host "An error occurred while verifying the zip contents: $_"
}

