param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $CliArgs
)

$supabaseExe = Join-Path $PSScriptRoot ".tools\supabase\supabase.exe"

if (-not (Test-Path -LiteralPath $supabaseExe)) {
    throw "Supabase CLI is not installed at $supabaseExe"
}

& $supabaseExe @CliArgs
exit $LASTEXITCODE
