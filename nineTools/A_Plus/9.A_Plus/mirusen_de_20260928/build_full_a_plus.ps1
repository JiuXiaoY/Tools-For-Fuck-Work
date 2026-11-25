param(
    [Parameter(Mandatory = $true)]
    [string]$DetailSource,

    [Parameter(Mandatory = $true)]
    [string]$LifestyleSource
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$outputDir = Join-Path $PSScriptRoot 'output'
$sourceDir = Join-Path $PSScriptRoot 'source'
$referenceDir = Join-Path $PSScriptRoot 'references'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $sourceDir | Out-Null

$detailCopy = Join-Path $sourceDir 'module-02-detail-generated.png'
$lifestyleCopy = Join-Path $sourceDir 'module-03-lifestyle-generated.png'
Copy-Item -LiteralPath $DetailSource -Destination $detailCopy -Force
Copy-Item -LiteralPath $LifestyleSource -Destination $lifestyleCopy -Force

$heroDesktop = Join-Path $outputDir 'mirusen-premium-a-plus-desktop-1464x600.jpg'
$heroMobile = Join-Path $outputDir 'mirusen-premium-a-plus-mobile-600x450.jpg'
Copy-Item -LiteralPath $heroDesktop -Destination (Join-Path $outputDir '01-hero-desktop-1464x600.jpg') -Force
Copy-Item -LiteralPath $heroMobile -Destination (Join-Path $outputDir '01-hero-mobile-600x450.jpg') -Force

function Get-CoverSourceRectangle {
    param(
        [int]$SourceWidth,
        [int]$SourceHeight,
        [int]$TargetWidth,
        [int]$TargetHeight,
        [double]$HorizontalBias = 0.5,
        [double]$VerticalBias = 0.5
    )

    $sourceRatio = $SourceWidth / $SourceHeight
    $targetRatio = $TargetWidth / $TargetHeight
    $HorizontalBias = [Math]::Max(0, [Math]::Min(1, $HorizontalBias))
    $VerticalBias = [Math]::Max(0, [Math]::Min(1, $VerticalBias))

    if ($sourceRatio -gt $targetRatio) {
        $cropWidth = [int][Math]::Round($SourceHeight * $targetRatio)
        $x = [int][Math]::Round(($SourceWidth - $cropWidth) * $HorizontalBias)
        return [System.Drawing.Rectangle]::new($x, 0, $cropWidth, $SourceHeight)
    }

    $cropHeight = [int][Math]::Round($SourceWidth / $targetRatio)
    $y = [int][Math]::Round(($SourceHeight - $cropHeight) * $VerticalBias)
    return [System.Drawing.Rectangle]::new(0, $y, $SourceWidth, $cropHeight)
}

function New-Canvas {
    param([int]$Width, [int]$Height)

    $bitmap = [System.Drawing.Bitmap]::new($Width, $Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $bitmap.SetResolution(96, 96)
    return $bitmap
}

function Set-HighQuality {
    param([System.Drawing.Graphics]$Graphics)

    $Graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $Graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $Graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
}

function Draw-CoverImage {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.Image]$Image,
        [System.Drawing.Rectangle]$Destination,
        [double]$HorizontalBias = 0.5,
        [double]$VerticalBias = 0.5
    )

    $sourceRect = Get-CoverSourceRectangle -SourceWidth $Image.Width -SourceHeight $Image.Height -TargetWidth $Destination.Width -TargetHeight $Destination.Height -HorizontalBias $HorizontalBias -VerticalBias $VerticalBias
    $Graphics.DrawImage($Image, $Destination, $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)
}

function New-Font {
    param([float]$Size, [System.Drawing.FontStyle]$Style = [System.Drawing.FontStyle]::Regular)
    return [System.Drawing.Font]::new('Bahnschrift', $Size, $Style, [System.Drawing.GraphicsUnit]::Pixel)
}

function Draw-TextBlock {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Color]$Color,
        [System.Drawing.RectangleF]$Rectangle,
        [bool]$Shadow = $false
    )

    $format = [System.Drawing.StringFormat]::new()
    $format.Alignment = [System.Drawing.StringAlignment]::Near
    $format.LineAlignment = [System.Drawing.StringAlignment]::Near
    if ($Shadow) {
        $shadowBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(130, 0, 0, 0))
        $shadowRect = [System.Drawing.RectangleF]::new($Rectangle.X + 2, $Rectangle.Y + 3, $Rectangle.Width, $Rectangle.Height)
        $Graphics.DrawString($Text, $Font, $shadowBrush, $shadowRect, $format)
        $shadowBrush.Dispose()
    }
    $brush = [System.Drawing.SolidBrush]::new($Color)
    $Graphics.DrawString($Text, $Font, $brush, $Rectangle, $format)
    $brush.Dispose()
    $format.Dispose()
}

function Fill-Gradient {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.Rectangle]$Rectangle,
        [System.Drawing.Color]$StartColor,
        [System.Drawing.Color]$EndColor,
        [System.Drawing.Drawing2D.LinearGradientMode]$Mode
    )

    $brush = [System.Drawing.Drawing2D.LinearGradientBrush]::new($Rectangle, $StartColor, $EndColor, $Mode)
    $Graphics.FillRectangle($brush, $Rectangle)
    $brush.Dispose()
}

function Save-Jpeg {
    param([System.Drawing.Bitmap]$Bitmap, [string]$Path, [long]$Quality = 94)

    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
        Where-Object { $_.MimeType -eq 'image/jpeg' } |
        Select-Object -First 1
    $parameters = [System.Drawing.Imaging.EncoderParameters]::new(1)
    $parameters.Param[0] = [System.Drawing.Imaging.EncoderParameter]::new([System.Drawing.Imaging.Encoder]::Quality, $Quality)
    try { $Bitmap.Save($Path, $codec, $parameters) }
    finally { $parameters.Dispose() }
}

function Add-AccentLine {
    param([System.Drawing.Graphics]$Graphics, [float]$X, [float]$Y, [float]$Width, [float]$Height = 4)

    $accent = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 190, 124, 71))
    $Graphics.FillRectangle($accent, $X, $Y, $Width, $Height)
    $accent.Dispose()
}

function New-DetailModule {
    param([string]$SourcePath, [string]$OutputPath, [int]$Width, [int]$Height, [bool]$Mobile)

    $source = [System.Drawing.Image]::FromFile($SourcePath)
    $canvas = New-Canvas -Width $Width -Height $Height
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    try {
        Set-HighQuality -Graphics $graphics
        Draw-CoverImage -Graphics $graphics -Image $source -Destination ([System.Drawing.Rectangle]::new(0, 0, $Width, $Height)) -HorizontalBias 0.5

        if ($Mobile) {
            $panel = [System.Drawing.Rectangle]::new(0, 278, $Width, 172)
            Fill-Gradient -Graphics $graphics -Rectangle $panel -StartColor ([System.Drawing.Color]::FromArgb(242, 8, 15, 29)) -EndColor ([System.Drawing.Color]::FromArgb(222, 18, 30, 47)) -Mode ([System.Drawing.Drawing2D.LinearGradientMode]::Vertical)
            $titleFont = New-Font -Size 28 -Style ([System.Drawing.FontStyle]::Bold)
            $labelFont = New-Font -Size 15 -Style ([System.Drawing.FontStyle]::Bold)
            $bodyFont = New-Font -Size 12
            Draw-TextBlock -Graphics $graphics -Text 'DETAILS, DIE DEN LOOK PRÄGEN.' -Font $titleFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new(28, 292, 545, 40))
            Add-AccentLine -Graphics $graphics -X 30 -Y 337 -Width 58 -Height 3
            $items = @(
                @('HALF-ZIP', 'Klarer Kragen-Look'),
                @('KONTRAST', 'Schulter & Ellbogen'),
                @('RIPPUNG', 'Ärmel & Saum')
            )
            for ($i = 0; $i -lt $items.Count; $i++) {
                $x = 30 + ($i * 190)
                Draw-TextBlock -Graphics $graphics -Text $items[$i][0] -Font $labelFont -Color ([System.Drawing.Color]::FromArgb(255, 215, 168, 126)) -Rectangle ([System.Drawing.RectangleF]::new($x, 352, 175, 24))
                Draw-TextBlock -Graphics $graphics -Text $items[$i][1] -Font $bodyFont -Color ([System.Drawing.Color]::FromArgb(238, 240, 244, 249)) -Rectangle ([System.Drawing.RectangleF]::new($x, 379, 170, 40))
            }
        }
        else {
            $panel = [System.Drawing.Rectangle]::new(780, 0, 684, $Height)
            Fill-Gradient -Graphics $graphics -Rectangle $panel -StartColor ([System.Drawing.Color]::FromArgb(0, 8, 15, 29)) -EndColor ([System.Drawing.Color]::FromArgb(240, 8, 15, 29)) -Mode ([System.Drawing.Drawing2D.LinearGradientMode]::Horizontal)
            $titleFont = New-Font -Size 44 -Style ([System.Drawing.FontStyle]::Bold)
            $labelFont = New-Font -Size 23 -Style ([System.Drawing.FontStyle]::Bold)
            $bodyFont = New-Font -Size 18
            Draw-TextBlock -Graphics $graphics -Text "DETAILS, DIE DEN`nLOOK PRÄGEN." -Font $titleFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new(940, 66, 455, 116)) -Shadow $true
            Add-AccentLine -Graphics $graphics -X 944 -Y 191 -Width 88
            $items = @(
                @('HALF-ZIP KRAGEN', 'Kurzer Reißverschluss für einen klaren Look'),
                @('KONTRASTBESATZ', 'Markante Schulter- und Ellbogenpartien'),
                @('RIPPABSCHLÜSSE', 'Sauberer Abschluss an Ärmeln und Saum')
            )
            for ($i = 0; $i -lt $items.Count; $i++) {
                $y = 232 + ($i * 112)
                Draw-TextBlock -Graphics $graphics -Text $items[$i][0] -Font $labelFont -Color ([System.Drawing.Color]::FromArgb(255, 215, 168, 126)) -Rectangle ([System.Drawing.RectangleF]::new(944, $y, 440, 32))
                Draw-TextBlock -Graphics $graphics -Text $items[$i][1] -Font $bodyFont -Color ([System.Drawing.Color]::FromArgb(238, 240, 244, 249)) -Rectangle ([System.Drawing.RectangleF]::new(944, $y + 38, 430, 52))
            }
        }

        $titleFont.Dispose(); $labelFont.Dispose(); $bodyFont.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $OutputPath
    }
    finally { $graphics.Dispose(); $canvas.Dispose(); $source.Dispose() }
}

function New-LifestyleModule {
    param([string]$SourcePath, [string]$OutputPath, [int]$Width, [int]$Height, [bool]$Mobile)

    $source = [System.Drawing.Image]::FromFile($SourcePath)
    $canvas = New-Canvas -Width $Width -Height $Height
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    try {
        Set-HighQuality -Graphics $graphics
        $bias = if ($Mobile) { 0.12 } else { 0.5 }
        Draw-CoverImage -Graphics $graphics -Image $source -Destination ([System.Drawing.Rectangle]::new(0, 0, $Width, $Height)) -HorizontalBias $bias

        if ($Mobile) {
            $panel = [System.Drawing.Rectangle]::new(0, 292, $Width, 158)
            Fill-Gradient -Graphics $graphics -Rectangle $panel -StartColor ([System.Drawing.Color]::FromArgb(235, 7, 14, 27)) -EndColor ([System.Drawing.Color]::FromArgb(215, 23, 34, 49)) -Mode ([System.Drawing.Drawing2D.LinearGradientMode]::Vertical)
            $titleFont = New-Font -Size 27 -Style ([System.Drawing.FontStyle]::Bold)
            $bodyFont = New-Font -Size 15
            $badgeFont = New-Font -Size 14 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-TextBlock -Graphics $graphics -Text 'VIELSEITIG DURCH DEN TAG.' -Font $titleFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new(30, 307, 540, 36))
            Draw-TextBlock -Graphics $graphics -Text 'Ein markanter Look für deine täglichen Wege.' -Font $bodyFont -Color ([System.Drawing.Color]::FromArgb(238, 240, 244, 249)) -Rectangle ([System.Drawing.RectangleF]::new(32, 352, 530, 28))
            $badges = @('ALLTAG', 'FREIZEIT', 'REISE')
            for ($i = 0; $i -lt $badges.Count; $i++) {
                $x = 32 + ($i * 178)
                $badgeBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(88, 255, 255, 255))
                $graphics.FillRectangle($badgeBrush, $x, 391, 152, 34)
                $badgeBrush.Dispose()
                Draw-TextBlock -Graphics $graphics -Text $badges[$i] -Font $badgeFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new($x + 14, 399, 130, 22))
            }
        }
        else {
            $panel = [System.Drawing.Rectangle]::new(820, 0, 644, $Height)
            Fill-Gradient -Graphics $graphics -Rectangle $panel -StartColor ([System.Drawing.Color]::FromArgb(0, 8, 15, 29)) -EndColor ([System.Drawing.Color]::FromArgb(225, 8, 15, 29)) -Mode ([System.Drawing.Drawing2D.LinearGradientMode]::Horizontal)
            $titleFont = New-Font -Size 48 -Style ([System.Drawing.FontStyle]::Bold)
            $bodyFont = New-Font -Size 22
            $badgeFont = New-Font -Size 18 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-TextBlock -Graphics $graphics -Text "VIELSEITIG`nDURCH DEN TAG." -Font $titleFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new(965, 118, 420, 120)) -Shadow $true
            Add-AccentLine -Graphics $graphics -X 968 -Y 251 -Width 90
            Draw-TextBlock -Graphics $graphics -Text 'Ein markanter Look für deine täglichen Wege.' -Font $bodyFont -Color ([System.Drawing.Color]::FromArgb(238, 240, 244, 249)) -Rectangle ([System.Drawing.RectangleF]::new(968, 280, 390, 62))
            $badges = @('ALLTAG', 'FREIZEIT', 'REISE')
            for ($i = 0; $i -lt $badges.Count; $i++) {
                $y = 372 + ($i * 54)
                $badgeBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(76, 255, 255, 255))
                $graphics.FillRectangle($badgeBrush, 968, $y, 250, 40)
                $badgeBrush.Dispose()
                Draw-TextBlock -Graphics $graphics -Text $badges[$i] -Font $badgeFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new(985, $y + 9, 220, 25))
            }
        }

        $titleFont.Dispose(); $bodyFont.Dispose(); $badgeFont.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $OutputPath
    }
    finally { $graphics.Dispose(); $canvas.Dispose(); $source.Dispose() }
}

function New-ColorModule {
    param([string]$ReferencePath, [string]$OutputPath, [int]$Width, [int]$Height, [bool]$Mobile)

    $reference = [System.Drawing.Image]::FromFile($ReferencePath)
    $canvas = New-Canvas -Width $Width -Height $Height
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    try {
        Set-HighQuality -Graphics $graphics
        $background = [System.Drawing.Rectangle]::new(0, 0, $Width, $Height)
        Fill-Gradient -Graphics $graphics -Rectangle $background -StartColor ([System.Drawing.Color]::FromArgb(255, 7, 14, 27)) -EndColor ([System.Drawing.Color]::FromArgb(255, 35, 48, 65)) -Mode ([System.Drawing.Drawing2D.LinearGradientMode]::Horizontal)

        $titleFont = New-Font -Size $(if ($Mobile) { 29 } else { 46 }) -Style ([System.Drawing.FontStyle]::Bold)
        $labelFont = New-Font -Size $(if ($Mobile) { 12 } else { 18 }) -Style ([System.Drawing.FontStyle]::Bold)
        $subFont = New-Font -Size $(if ($Mobile) { 14 } else { 20 })
        Draw-TextBlock -Graphics $graphics -Text 'DEIN LOOK. DEINE FARBE.' -Font $titleFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new($(if ($Mobile) { 28 } else { 62 }), $(if ($Mobile) { 28 } else { 42 }), $Width - 80, 60))
        Draw-TextBlock -Graphics $graphics -Text 'Fünf ausdrucksstarke Farbkombinationen.' -Font $subFont -Color ([System.Drawing.Color]::FromArgb(225, 232, 238, 246)) -Rectangle ([System.Drawing.RectangleF]::new($(if ($Mobile) { 30 } else { 65 }), $(if ($Mobile) { 72 } else { 102 }), $Width - 100, 34))

        $labels = @('BEIGE', 'ARMEEGRÜN', 'WEINROT', 'SCHWARZ', 'HIMMELBLAU')
        $sourceX = [int]($reference.Width * 0.80)
        $sourceWidth = $reference.Width - $sourceX
        $sourceHeight = [int]($reference.Height / 5)

        if ($Mobile) {
            $gap = 8; $cardWidth = 102; $cardHeight = 290; $startX = 29; $startY = 116
        }
        else {
            $gap = 18; $cardWidth = 250; $cardHeight = 412; $startX = 64; $startY = 150
        }

        for ($i = 0; $i -lt 5; $i++) {
            $x = $startX + ($i * ($cardWidth + $gap))
            $src = [System.Drawing.Rectangle]::new($sourceX, $i * $sourceHeight, $sourceWidth, $sourceHeight)
            $imageRect = [System.Drawing.Rectangle]::new($x, $startY, $cardWidth, $cardHeight - $(if ($Mobile) { 37 } else { 48 }))
            $graphics.DrawImage($reference, $imageRect, $src, [System.Drawing.GraphicsUnit]::Pixel)
            $lineBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 190, 124, 71))
            $graphics.FillRectangle($lineBrush, $x, $imageRect.Bottom, $cardWidth, 3)
            $lineBrush.Dispose()
            Draw-TextBlock -Graphics $graphics -Text $labels[$i] -Font $labelFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new($x + 4, $imageRect.Bottom + 10, $cardWidth - 8, 28))
        }

        $titleFont.Dispose(); $labelFont.Dispose(); $subFont.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $OutputPath
    }
    finally { $graphics.Dispose(); $canvas.Dispose(); $reference.Dispose() }
}

function New-SizeModule {
    param([string]$BackgroundPath, [string]$OutputPath, [int]$Width, [int]$Height, [bool]$Mobile)

    $backgroundImage = [System.Drawing.Image]::FromFile($BackgroundPath)
    $canvas = New-Canvas -Width $Width -Height $Height
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    try {
        Set-HighQuality -Graphics $graphics
        Draw-CoverImage -Graphics $graphics -Image $backgroundImage -Destination ([System.Drawing.Rectangle]::new(0, 0, $Width, $Height)) -HorizontalBias 0.35
        $overlay = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb($(if ($Mobile) { 230 } else { 208 }), 7, 14, 27))
        $graphics.FillRectangle($overlay, 0, 0, $Width, $Height)
        $overlay.Dispose()

        $titleFont = New-Font -Size $(if ($Mobile) { 27 } else { 44 }) -Style ([System.Drawing.FontStyle]::Bold)
        $subFont = New-Font -Size $(if ($Mobile) { 13 } else { 18 })
        $headerFont = New-Font -Size $(if ($Mobile) { 12 } else { 16 }) -Style ([System.Drawing.FontStyle]::Bold)
        $cellFont = New-Font -Size $(if ($Mobile) { 12 } else { 15 })
        Draw-TextBlock -Graphics $graphics -Text 'DIE PASSFORM FÜR DICH.' -Font $titleFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new($(if ($Mobile) { 22 } else { 60 }), $(if ($Mobile) { 22 } else { 36 }), $Width - 70, 58))
        Draw-TextBlock -Graphics $graphics -Text 'Maße am Kleidungsstück · Angaben in cm' -Font $subFont -Color ([System.Drawing.Color]::FromArgb(225, 232, 238, 246)) -Rectangle ([System.Drawing.RectangleF]::new($(if ($Mobile) { 24 } else { 64 }), $(if ($Mobile) { 66 } else { 94 }), $Width - 80, 30))

        $headers = @('GRÖSSE', 'BRUST', 'SCHULTER', 'ÄRMEL', 'LÄNGE')
        $rows = @(
            @('S', '112', '48', '63', '71'),
            @('M', '117', '49,5', '63,7', '72'),
            @('L', '122', '51', '64,4', '73'),
            @('XL', '127', '52,5', '65,1', '74'),
            @('XXL', '132', '54', '65,8', '75'),
            @('3XL', '137', '55,5', '66,5', '76'),
            @('4XL', '142', '57', '67,2', '77'),
            @('5XL', '147', '58,5', '67,9', '78')
        )

        if ($Mobile) {
            $tableX = 18; $tableY = 106; $tableWidth = 564; $rowHeight = 33; $columnWidths = @(72, 118, 132, 118, 124)
        }
        else {
            $tableX = 58; $tableY = 145; $tableWidth = 1030; $rowHeight = 43; $columnWidths = @(115, 225, 245, 220, 225)
        }

        $headerBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(238, 190, 124, 71))
        $rowBrushA = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(222, 241, 244, 248))
        $rowBrushB = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(212, 219, 226, 235))
        $gridPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(120, 7, 14, 27), 1)

        $x = $tableX
        for ($c = 0; $c -lt $headers.Count; $c++) {
            $rect = [System.Drawing.Rectangle]::new($x, $tableY, $columnWidths[$c], $rowHeight)
            $graphics.FillRectangle($headerBrush, $rect)
            $graphics.DrawRectangle($gridPen, $rect)
            Draw-TextBlock -Graphics $graphics -Text $headers[$c] -Font $headerFont -Color ([System.Drawing.Color]::White) -Rectangle ([System.Drawing.RectangleF]::new($x + 7, $tableY + $(if ($Mobile) { 9 } else { 12 }), $columnWidths[$c] - 12, 24))
            $x += $columnWidths[$c]
        }

        for ($r = 0; $r -lt $rows.Count; $r++) {
            $x = $tableX
            $y = $tableY + (($r + 1) * $rowHeight)
            $rowBrush = if (($r % 2) -eq 0) { $rowBrushA } else { $rowBrushB }
            for ($c = 0; $c -lt 5; $c++) {
                $rect = [System.Drawing.Rectangle]::new($x, $y, $columnWidths[$c], $rowHeight)
                $graphics.FillRectangle($rowBrush, $rect)
                $graphics.DrawRectangle($gridPen, $rect)
                $value = if ($c -eq 0) { $rows[$r][$c] } else { $rows[$r][$c] + ' cm' }
                Draw-TextBlock -Graphics $graphics -Text $value -Font $cellFont -Color ([System.Drawing.Color]::FromArgb(255, 31, 42, 56)) -Rectangle ([System.Drawing.RectangleF]::new($x + 7, $y + $(if ($Mobile) { 9 } else { 12 }), $columnWidths[$c] - 12, 22))
                $x += $columnWidths[$c]
            }
        }

        $noteY = $tableY + (($rows.Count + 1) * $rowHeight) + $(if ($Mobile) { 8 } else { 16 })
        Draw-TextBlock -Graphics $graphics -Text 'Vor der Auswahl bitte Brust, Schulter, Ärmel und Länge vergleichen.' -Font $subFont -Color ([System.Drawing.Color]::FromArgb(235, 240, 244, 249)) -Rectangle ([System.Drawing.RectangleF]::new($tableX, $noteY, $tableWidth, 35))

        $headerBrush.Dispose(); $rowBrushA.Dispose(); $rowBrushB.Dispose(); $gridPen.Dispose()
        $titleFont.Dispose(); $subFont.Dispose(); $headerFont.Dispose(); $cellFont.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $OutputPath
    }
    finally { $graphics.Dispose(); $canvas.Dispose(); $backgroundImage.Dispose() }
}

$referenceProduct = Join-Path $referenceDir 'product-reference-01.jpg'
$heroSource = Join-Path $sourceDir 'desktop-hero-generated.png'

New-DetailModule -SourcePath $detailCopy -OutputPath (Join-Path $outputDir '02-details-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-DetailModule -SourcePath $detailCopy -OutputPath (Join-Path $outputDir '02-details-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true

New-LifestyleModule -SourcePath $lifestyleCopy -OutputPath (Join-Path $outputDir '03-lifestyle-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-LifestyleModule -SourcePath $lifestyleCopy -OutputPath (Join-Path $outputDir '03-lifestyle-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true

New-ColorModule -ReferencePath $referenceProduct -OutputPath (Join-Path $outputDir '04-colors-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-ColorModule -ReferencePath $referenceProduct -OutputPath (Join-Path $outputDir '04-colors-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true

New-SizeModule -BackgroundPath $heroSource -OutputPath (Join-Path $outputDir '05-size-guide-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-SizeModule -BackgroundPath $heroSource -OutputPath (Join-Path $outputDir '05-size-guide-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true

Get-ChildItem -LiteralPath $outputDir -Filter '0*.jpg' | Sort-Object Name | ForEach-Object {
    $image = [System.Drawing.Image]::FromFile($_.FullName)
    try {
        [PSCustomObject]@{ File = $_.Name; Width = $image.Width; Height = $image.Height; Bytes = $_.Length }
    }
    finally { $image.Dispose() }
} | Format-Table -AutoSize
