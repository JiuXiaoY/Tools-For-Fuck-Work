param(
    [Parameter(Mandatory = $true)]
    [string]$DesktopSource,

    [Parameter(Mandatory = $true)]
    [string]$MobileSource
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$outputDir = Join-Path $PSScriptRoot 'output'
$sourceDir = Join-Path $PSScriptRoot 'source'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $sourceDir | Out-Null

$desktopSourceCopy = Join-Path $sourceDir 'desktop-hero-generated.png'
$mobileSourceCopy = Join-Path $sourceDir 'mobile-hero-generated.png'
Copy-Item -LiteralPath $DesktopSource -Destination $desktopSourceCopy -Force
Copy-Item -LiteralPath $MobileSource -Destination $mobileSourceCopy -Force

function Get-FittedSourceRectangle {
    param(
        [int]$SourceWidth,
        [int]$SourceHeight,
        [int]$TargetWidth,
        [int]$TargetHeight
    )

    $sourceRatio = $SourceWidth / $SourceHeight
    $targetRatio = $TargetWidth / $TargetHeight

    if ($sourceRatio -gt $targetRatio) {
        $cropWidth = [int][Math]::Round($SourceHeight * $targetRatio)
        $x = [int][Math]::Round(($SourceWidth - $cropWidth) / 2)
        return [System.Drawing.Rectangle]::new($x, 0, $cropWidth, $SourceHeight)
    }

    $cropHeight = [int][Math]::Round($SourceWidth / $targetRatio)
    $y = [int][Math]::Round(($SourceHeight - $cropHeight) / 2)
    return [System.Drawing.Rectangle]::new(0, $y, $SourceWidth, $cropHeight)
}

function Save-Jpeg {
    param(
        [System.Drawing.Bitmap]$Bitmap,
        [string]$Path,
        [long]$Quality = 94
    )

    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
        Where-Object { $_.MimeType -eq 'image/jpeg' } |
        Select-Object -First 1
    $encoder = [System.Drawing.Imaging.Encoder]::Quality
    $parameters = [System.Drawing.Imaging.EncoderParameters]::new(1)
    $parameters.Param[0] = [System.Drawing.Imaging.EncoderParameter]::new($encoder, $Quality)
    try {
        $Bitmap.Save($Path, $codec, $parameters)
    }
    finally {
        $parameters.Dispose()
    }
}

function New-APlusImage {
    param(
        [string]$SourcePath,
        [string]$OutputPath,
        [int]$Width,
        [int]$Height,
        [bool]$IsMobile
    )

    $source = [System.Drawing.Image]::FromFile($SourcePath)
    $canvas = [System.Drawing.Bitmap]::new($Width, $Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $canvas.SetResolution(96, 96)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)

    try {
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

        $sourceRect = Get-FittedSourceRectangle -SourceWidth $source.Width -SourceHeight $source.Height -TargetWidth $Width -TargetHeight $Height
        $destinationRect = [System.Drawing.Rectangle]::new(0, 0, $Width, $Height)
        $graphics.DrawImage($source, $destinationRect, $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)

        if ($IsMobile) {
            $overlayWidth = [int]($Width * 0.66)
            $gradientRect = [System.Drawing.Rectangle]::new(0, 0, $overlayWidth, $Height)
            $gradient = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
                $gradientRect,
                [System.Drawing.Color]::FromArgb(188, 7, 14, 27),
                [System.Drawing.Color]::FromArgb(0, 7, 14, 27),
                [System.Drawing.Drawing2D.LinearGradientMode]::Horizontal
            )
            $graphics.FillRectangle($gradient, $gradientRect)
            $gradient.Dispose()

            $headlineFont = [System.Drawing.Font]::new('Bahnschrift', 27, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
            $subFont = [System.Drawing.Font]::new('Bahnschrift', 16, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
            $headlineRect = [System.Drawing.RectangleF]::new(34, 60, 300, 96)
            $subRect = [System.Drawing.RectangleF]::new(36, 174, 270, 70)
            $accentRect = [System.Drawing.RectangleF]::new(36, 158, 56, 3)
        }
        else {
            $overlayWidth = [int]($Width * 0.57)
            $gradientRect = [System.Drawing.Rectangle]::new(0, 0, $overlayWidth, $Height)
            $gradient = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
                $gradientRect,
                [System.Drawing.Color]::FromArgb(196, 7, 14, 27),
                [System.Drawing.Color]::FromArgb(0, 7, 14, 27),
                [System.Drawing.Drawing2D.LinearGradientMode]::Horizontal
            )
            $graphics.FillRectangle($gradient, $gradientRect)
            $gradient.Dispose()

            $headlineFont = [System.Drawing.Font]::new('Bahnschrift', 54, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
            $subFont = [System.Drawing.Font]::new('Bahnschrift', 23, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
            $headlineRect = [System.Drawing.RectangleF]::new(82, 155, 690, 140)
            $subRect = [System.Drawing.RectangleF]::new(86, 334, 610, 80)
            $accentRect = [System.Drawing.RectangleF]::new(86, 312, 92, 4)
        }

        $headlineBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
        $subBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(235, 240, 244, 250))
        $accentBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 190, 124, 71))
        $shadowBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(120, 0, 0, 0))
        $format = [System.Drawing.StringFormat]::new()
        $format.Alignment = [System.Drawing.StringAlignment]::Near
        $format.LineAlignment = [System.Drawing.StringAlignment]::Near

        $headline = "MARKANTER LOOK.`nENTSPANNT GETRAGEN."
        $subtitle = if ($IsMobile) {
            "Asymmetrisches Patchwork`nHalf-Zip · Lockere Passform"
        }
        else {
            'Asymmetrisches Patchwork  ·  Half-Zip  ·  Lockere Passform'
        }

        $shadowRect = [System.Drawing.RectangleF]::new($headlineRect.X + 2, $headlineRect.Y + 3, $headlineRect.Width, $headlineRect.Height)
        $graphics.DrawString($headline, $headlineFont, $shadowBrush, $shadowRect, $format)
        $graphics.DrawString($headline, $headlineFont, $headlineBrush, $headlineRect, $format)
        $graphics.FillRectangle($accentBrush, $accentRect)
        $graphics.DrawString($subtitle, $subFont, $subBrush, $subRect, $format)

        $headlineFont.Dispose()
        $subFont.Dispose()
        $headlineBrush.Dispose()
        $subBrush.Dispose()
        $accentBrush.Dispose()
        $shadowBrush.Dispose()
        $format.Dispose()

        Save-Jpeg -Bitmap $canvas -Path $OutputPath -Quality 94
    }
    finally {
        $graphics.Dispose()
        $canvas.Dispose()
        $source.Dispose()
    }
}

$desktopOutput = Join-Path $outputDir 'mirusen-premium-a-plus-desktop-1464x600.jpg'
$mobileOutput = Join-Path $outputDir 'mirusen-premium-a-plus-mobile-600x450.jpg'

New-APlusImage -SourcePath $desktopSourceCopy -OutputPath $desktopOutput -Width 1464 -Height 600 -IsMobile $false
New-APlusImage -SourcePath $mobileSourceCopy -OutputPath $mobileOutput -Width 600 -Height 450 -IsMobile $true

Get-ChildItem -LiteralPath $outputDir -Filter '*.jpg' | ForEach-Object {
    $check = [System.Drawing.Image]::FromFile($_.FullName)
    try {
        [PSCustomObject]@{
            File = $_.Name
            Width = $check.Width
            Height = $check.Height
            Bytes = $_.Length
        }
    }
    finally {
        $check.Dispose()
    }
} | Format-Table -AutoSize
