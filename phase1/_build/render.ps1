param([string]$Docx, [string]$Pdf)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $d = $word.Documents.Open($Docx, $false, $true)
    $d.SaveAs([ref]$Pdf, [ref]17)
    $d.Close([ref]0)
    "pdf ok"
} finally { $word.Quit() }
