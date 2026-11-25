param(
    [Parameter(Mandatory = $true)][string]$HeroDesktop,
    [Parameter(Mandatory = $true)][string]$HeroMobile,
    [Parameter(Mandatory = $true)][string]$DetailsDesktop,
    [Parameter(Mandatory = $true)][string]$DetailsMobile,
    [Parameter(Mandatory = $true)][string]$ColorsDesktop,
    [Parameter(Mandatory = $true)][string]$ColorsMobile,
    [Parameter(Mandatory = $true)][string]$OccasionsDesktop,
    [Parameter(Mandatory = $true)][string]$OccasionsMobile,
    [Parameter(Mandatory = $true)][string]$SizeDesktop,
    [Parameter(Mandatory = $true)][string]$SizeMobile
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$outDir = Join-Path $PSScriptRoot 'output_v2_editorial'
$srcDir = Join-Path $PSScriptRoot 'source_v2_editorial'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $srcDir | Out-Null

$sources = [ordered]@{
    '01-hero-desktop-source.png' = $HeroDesktop
    '01-hero-mobile-source.png' = $HeroMobile
    '02-details-desktop-source.png' = $DetailsDesktop
    '02-details-mobile-source.png' = $DetailsMobile
    '03-colors-desktop-source.png' = $ColorsDesktop
    '03-colors-mobile-source.png' = $ColorsMobile
    '04-occasions-desktop-source.png' = $OccasionsDesktop
    '04-occasions-mobile-source.png' = $OccasionsMobile
    '05-size-desktop-source.png' = $SizeDesktop
    '05-size-mobile-source.png' = $SizeMobile
}

foreach ($entry in $sources.GetEnumerator()) {
    Copy-Item -LiteralPath $entry.Value -Destination (Join-Path $srcDir $entry.Key) -Force
}

function New-Canvas {
    param([int]$Width, [int]$Height)
    $bitmap = [System.Drawing.Bitmap]::new($Width, $Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $bitmap.SetResolution(96, 96)
    return $bitmap
}

function Set-Quality {
    param([System.Drawing.Graphics]$Graphics)
    $Graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $Graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $Graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
}

function Draw-Cover {
    param([System.Drawing.Graphics]$Graphics, [System.Drawing.Image]$Image, [int]$Width, [int]$Height)
    $sourceRatio = $Image.Width / $Image.Height
    $targetRatio = $Width / $Height
    if ($sourceRatio -gt $targetRatio) {
        $cropWidth = [int][Math]::Round($Image.Height * $targetRatio)
        $sourceRect = [System.Drawing.Rectangle]::new([int](($Image.Width - $cropWidth) / 2), 0, $cropWidth, $Image.Height)
    }
    else {
        $cropHeight = [int][Math]::Round($Image.Width / $targetRatio)
        $sourceRect = [System.Drawing.Rectangle]::new(0, [int](($Image.Height - $cropHeight) / 2), $Image.Width, $cropHeight)
    }
    $Graphics.DrawImage($Image, [System.Drawing.Rectangle]::new(0, 0, $Width, $Height), $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)
}

function New-Font {
    param([string]$Family, [float]$Size, [System.Drawing.FontStyle]$Style = [System.Drawing.FontStyle]::Regular)
    return [System.Drawing.Font]::new($Family, $Size, $Style, [System.Drawing.GraphicsUnit]::Pixel)
}

function Draw-Text {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Color]$Color,
        [System.Drawing.RectangleF]$Rect,
        [System.Drawing.StringAlignment]$Alignment = [System.Drawing.StringAlignment]::Near
    )
    $format = [System.Drawing.StringFormat]::new()
    $format.Alignment = $Alignment
    $format.LineAlignment = [System.Drawing.StringAlignment]::Near
    $brush = [System.Drawing.SolidBrush]::new($Color)
    $Graphics.DrawString($Text, $Font, $brush, $Rect, $format)
    $brush.Dispose()
    $format.Dispose()
}

function Fill-AlphaRect {
    param([System.Drawing.Graphics]$Graphics, [System.Drawing.RectangleF]$Rect, [System.Drawing.Color]$Color)
    $brush = [System.Drawing.SolidBrush]::new($Color)
    $Graphics.FillRectangle($brush, $Rect)
    $brush.Dispose()
}

function Draw-Accent {
    param([System.Drawing.Graphics]$Graphics, [float]$X, [float]$Y, [float]$Width, [float]$Height = 3)
    $brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 186, 133, 82))
    $Graphics.FillRectangle($brush, $X, $Y, $Width, $Height)
    $brush.Dispose()
}

function Save-Jpeg {
    param([System.Drawing.Bitmap]$Bitmap, [string]$Path)
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' } | Select-Object -First 1
    $parameters = [System.Drawing.Imaging.EncoderParameters]::new(1)
    $parameters.Param[0] = [System.Drawing.Imaging.EncoderParameter]::new([System.Drawing.Imaging.Encoder]::Quality, [long]95)
    try { $Bitmap.Save($Path, $codec, $parameters) }
    finally { $parameters.Dispose() }
}

function New-BaseImage {
    param([string]$Source, [int]$Width, [int]$Height)
    $image = [System.Drawing.Image]::FromFile($Source)
    $canvas = New-Canvas -Width $Width -Height $Height
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    Set-Quality -Graphics $graphics
    Draw-Cover -Graphics $graphics -Image $image -Width $Width -Height $Height
    $image.Dispose()
    return @{ Canvas = $canvas; Graphics = $graphics }
}

function New-Hero {
    param([string]$Source, [string]$Output, [int]$Width, [int]$Height, [bool]$Mobile)
    $base = New-BaseImage -Source $Source -Width $Width -Height $Height
    $canvas = $base.Canvas; $graphics = $base.Graphics
    try {
        $navy = [System.Drawing.Color]::FromArgb(255, 18, 43, 71)
        if ($Mobile) {
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(300, 20, 278, 112)) -Color ([System.Drawing.Color]::FromArgb(195, 250, 244, 234))
            $title = New-Font -Family 'Georgia' -Size 31 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 13 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text "HALF-ZIP`nPULLOVER" -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(318, 28, 245, 72))
            Draw-Accent -Graphics $graphics -X 321 -Y 104 -Width 62
            Draw-Text -Graphics $graphics -Text 'ASYMMETRISCHES PATCHWORK' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(320, 112, 242, 20))
        }
        else {
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(625, 34, 600, 150)) -Color ([System.Drawing.Color]::FromArgb(175, 250, 244, 234))
            $title = New-Font -Family 'Georgia' -Size 43 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 20 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text 'HALF-ZIP PULLOVER' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(655, 58, 560, 56))
            Draw-Accent -Graphics $graphics -X 866 -Y 124 -Width 82
            Draw-Text -Graphics $graphics -Text 'ASYMMETRISCHES PATCHWORK  ·  MARKANTER LOOK' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(650, 140, 555, 28)) -Alignment ([System.Drawing.StringAlignment]::Center)
        }
        $title.Dispose(); $sub.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $Output
    }
    finally { $graphics.Dispose(); $canvas.Dispose() }
}

function New-Details {
    param([string]$Source, [string]$Output, [int]$Width, [int]$Height, [bool]$Mobile)
    $base = New-BaseImage -Source $Source -Width $Width -Height $Height
    $canvas = $base.Canvas; $graphics = $base.Graphics
    try {
        $navy = [System.Drawing.Color]::FromArgb(255, 18, 43, 71)
        if ($Mobile) {
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(14, 10, 248, 54)) -Color ([System.Drawing.Color]::FromArgb(210, 250, 246, 238))
            $title = New-Font -Family 'Georgia' -Size 17 -Style ([System.Drawing.FontStyle]::Bold)
            $label = New-Font -Family 'Bahnschrift' -Size 9 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text "DESIGN MIT`nCHARAKTER" -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(24, 14, 230, 46))
            Draw-Text -Graphics $graphics -Text 'HALF-ZIP' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(270, 185, 145, 15)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'SCHULTERBESATZ' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(430, 185, 155, 15)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'SIGNATURE-DETAIL' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(271, 374, 103, 15)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'ELLBOGENPATCH' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(380, 374, 99, 15)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'RIPPABSCHLUSS' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(484, 374, 102, 15)) -Alignment ([System.Drawing.StringAlignment]::Center)
        }
        else {
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(24, 18, 520, 66)) -Color ([System.Drawing.Color]::FromArgb(206, 250, 246, 238))
            $title = New-Font -Family 'Georgia' -Size 32 -Style ([System.Drawing.FontStyle]::Bold)
            $label = New-Font -Family 'Bahnschrift' -Size 15 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text 'DESIGN MIT CHARAKTER' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(40, 31, 495, 40))
            Draw-Text -Graphics $graphics -Text 'HALF-ZIP KRAGEN' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(630, 247, 360, 22)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'KONTRAST-SCHULTER' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(1028, 247, 360, 22)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'SIGNATURE-DETAIL' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(608, 521, 255, 22)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'ELLBOGENPATCH' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(877, 521, 257, 22)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'RIPPABSCHLÜSSE' -Font $label -Color $navy -Rect ([System.Drawing.RectangleF]::new(1140, 521, 270, 22)) -Alignment ([System.Drawing.StringAlignment]::Center)
        }
        $title.Dispose(); $label.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $Output
    }
    finally { $graphics.Dispose(); $canvas.Dispose() }
}

function Draw-RotatedCropCard {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.Image]$Image,
        [float]$X, [float]$Y, [float]$Width, [float]$Height,
        [int]$SourceX, [int]$SourceY, [int]$SourceWidth, [int]$SourceHeight,
        [float]$Angle,
        [float]$BorderWidth = 2
    )
    $state = $Graphics.Save()
    $shadow = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(55, 18, 43, 71))
    $paper = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 252, 248, 239))
    $outline = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(210, 178, 123, 75), $BorderWidth)
    try {
        $Graphics.TranslateTransform($X + ($Width / 2), $Y + ($Height / 2))
        $Graphics.RotateTransform($Angle)
        $rect = [System.Drawing.RectangleF]::new(-$Width / 2, -$Height / 2, $Width, $Height)
        $shadowRect = [System.Drawing.RectangleF]::new((- $Width / 2) + 8, (- $Height / 2) + 10, $Width, $Height)
        $Graphics.FillRectangle($shadow, $shadowRect)
        $Graphics.FillRectangle($paper, $rect)
        $Graphics.DrawImage($Image, $rect, [System.Drawing.RectangleF]::new($SourceX, $SourceY, $SourceWidth, $SourceHeight), [System.Drawing.GraphicsUnit]::Pixel)
        $Graphics.DrawRectangle($outline, $rect.X, $rect.Y, $rect.Width, $rect.Height)
    }
    finally {
        $Graphics.Restore($state)
        $shadow.Dispose(); $paper.Dispose(); $outline.Dispose()
    }
}

function New-Colors {
    param([string]$Source, [string]$Output, [int]$Width, [int]$Height, [bool]$Mobile)
    $base = New-BaseImage -Source $Source -Width $Width -Height $Height
    $canvas = $base.Canvas; $graphics = $base.Graphics
    $fullFrame = [System.Drawing.Bitmap]$canvas.Clone()
    $backgroundFile = if ($Mobile) { 'source_v2_editorial\03-colors-outdoor-background-mobile.png' } else { 'source_v2_editorial\03-colors-outdoor-background-desktop.png' }
    $backgroundPath = Join-Path $PSScriptRoot $backgroundFile
    $background = [System.Drawing.Image]::FromFile($backgroundPath)
    try {
        $navy = [System.Drawing.Color]::FromArgb(255, 18, 43, 71)
        $cognac = [System.Drawing.Color]::FromArgb(255, 178, 123, 75)
        $graphics.Clear([System.Drawing.Color]::White)
        Draw-Cover -Graphics $graphics -Image $background -Width $Width -Height $Height
        Set-Quality -Graphics $graphics
        $sceneBorder = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(230, 252, 248, 239), $(if ($Mobile) { 3 } else { 5 }))

        if ($Mobile) {
            # Soft text panel, upper left.
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(12, 12, 264, 76)) -Color ([System.Drawing.Color]::FromArgb(215, 252, 248, 239))
            $title = New-Font -Family 'Georgia' -Size 26 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 11 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text 'FÜNF FARBEN' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(22, 20, 246, 32))
            Draw-Accent -Graphics $graphics -X 22 -Y 57 -Width 58 -Height 3
            Draw-Text -Graphics $graphics -Text 'EIN SIGNATURE-LOOK' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(22, 66, 242, 18))

            # Two editorial lifestyle panels on the left.
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(23, 105, 122, 330)) -Color ([System.Drawing.Color]::FromArgb(50, 18, 43, 71))
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(153, 105, 122, 330)) -Color ([System.Drawing.Color]::FromArgb(50, 18, 43, 71))
            $graphics.DrawImage($fullFrame, [System.Drawing.Rectangle]::new(18, 100, 122, 330), [System.Drawing.Rectangle]::new(8, 0, 104, 278), [System.Drawing.GraphicsUnit]::Pixel)
            $graphics.DrawImage($fullFrame, [System.Drawing.Rectangle]::new(148, 100, 122, 330), [System.Drawing.Rectangle]::new(248, 0, 104, 278), [System.Drawing.GraphicsUnit]::Pixel)
            $graphics.DrawRectangle($sceneBorder, [System.Drawing.Rectangle]::new(18, 100, 122, 330))
            $graphics.DrawRectangle($sceneBorder, [System.Drawing.Rectangle]::new(148, 100, 122, 330))

            # Frosted outdoor display zone with graphic depth.
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(286, 16, 302, 420)) -Color ([System.Drawing.Color]::FromArgb(105, 252, 248, 239))
            $circleBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(35, 18, 43, 71))
            $graphics.FillEllipse($circleBrush, 370, 88, 180, 180)
            $circleBrush.Dispose()

            # Five equal-ratio cards overlap in a shallow fan.
            $order = @(0, 4, 1, 3, 2)
            $xs = @(288, 335, 382, 429, 476)
            $ys = @(158, 124, 100, 124, 158)
            $angles = @(-8, 8, -4, 4, 0)
            foreach ($idx in $order) {
                $srcX = ($idx * 120) + 12
                Draw-RotatedCropCard -Graphics $graphics -Image $fullFrame -X $xs[$idx] -Y $ys[$idx] -Width 104 -Height 188 -SourceX $srcX -SourceY 278 -SourceWidth 96 -SourceHeight 172 -Angle $angles[$idx] -BorderWidth 1.2
            }
        }
        else {
            # Soft text panel, upper left.
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(28, 22, 652, 118)) -Color ([System.Drawing.Color]::FromArgb(210, 252, 248, 239))
            $title = New-Font -Family 'Georgia' -Size 42 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 18 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text 'FÜNF FARBEN' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(46, 34, 620, 54))
            Draw-Accent -Graphics $graphics -X 48 -Y 96 -Width 84 -Height 4
            Draw-Text -Graphics $graphics -Text 'EIN SIGNATURE-LOOK FÜR JEDEN TAG' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(46, 110, 630, 25))

            # Two editorial lifestyle panels on the left.
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(47, 163, 310, 410)) -Color ([System.Drawing.Color]::FromArgb(50, 18, 43, 71))
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(373, 163, 310, 410)) -Color ([System.Drawing.Color]::FromArgb(50, 18, 43, 71))
            $graphics.DrawImage($fullFrame, [System.Drawing.Rectangle]::new(40, 154, 310, 410), [System.Drawing.Rectangle]::new(0, 0, 293, 385), [System.Drawing.GraphicsUnit]::Pixel)
            $graphics.DrawImage($fullFrame, [System.Drawing.Rectangle]::new(366, 154, 310, 410), [System.Drawing.Rectangle]::new(586, 0, 293, 385), [System.Drawing.GraphicsUnit]::Pixel)
            $graphics.DrawRectangle($sceneBorder, [System.Drawing.Rectangle]::new(40, 154, 310, 410))
            $graphics.DrawRectangle($sceneBorder, [System.Drawing.Rectangle]::new(366, 154, 310, 410))

            # Frosted outdoor display zone with graphic depth.
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(695, 50, 735, 505)) -Color ([System.Drawing.Color]::FromArgb(105, 252, 248, 239))
            $circleBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(32, 18, 43, 71))
            $graphics.FillEllipse($circleBrush, 1015, 88, 330, 330)
            $circleBrush.Dispose()
            $arcPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(115, 178, 123, 75), 3)
            $graphics.DrawArc($arcPen, 760, 95, 560, 410, 205, 125)
            $arcPen.Dispose()

            # Five equal-ratio cards overlap in a shallow fan.
            $order = @(0, 4, 1, 3, 2)
            $xs = @(720, 845, 970, 1095, 1220)
            $ys = @(230, 182, 150, 182, 230)
            $angles = @(-7, 7, -3.5, 3.5, 0)
            foreach ($idx in $order) {
                $srcX = ($idx * 293) + 58
                Draw-RotatedCropCard -Graphics $graphics -Image $fullFrame -X $xs[$idx] -Y $ys[$idx] -Width 190 -Height 232 -SourceX $srcX -SourceY 385 -SourceWidth 176 -SourceHeight 215 -Angle $angles[$idx] -BorderWidth 2
            }
        }

        $sceneBorder.Dispose(); $title.Dispose(); $sub.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $Output
    }
    finally { $background.Dispose(); $fullFrame.Dispose(); $graphics.Dispose(); $canvas.Dispose() }
}

function New-Occasions {
    param([string]$Source, [string]$Output, [int]$Width, [int]$Height, [bool]$Mobile)
    $base = New-BaseImage -Source $Source -Width $Width -Height $Height
    $canvas = $base.Canvas; $graphics = $base.Graphics
    try {
        $navy = [System.Drawing.Color]::FromArgb(255, 18, 43, 71)
        if ($Mobile) {
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(0, 0, 600, 72)) -Color ([System.Drawing.Color]::FromArgb(244, 251, 247, 239))
            $title = New-Font -Family 'Georgia' -Size 28 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 12 -Style ([System.Drawing.FontStyle]::Bold)
            $tag = New-Font -Family 'Bahnschrift' -Size 12 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text 'VOM BÜRO BIS ZUM WOCHENENDE' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(18, 8, 564, 34)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'EIN LOOK  ·  VIELE MOMENTE' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(40, 45, 520, 18)) -Alignment ([System.Drawing.StringAlignment]::Center)
            $tagXs = @(34, 226, 420); $tags = @('BÜRO', 'STADT', 'WOCHENENDE')
            for ($i = 0; $i -lt 3; $i++) {
                Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new($tagXs[$i], 407, 145, 28)) -Color ([System.Drawing.Color]::FromArgb(170, 18, 43, 71))
                Draw-Text -Graphics $graphics -Text $tags[$i] -Font $tag -Color ([System.Drawing.Color]::White) -Rect ([System.Drawing.RectangleF]::new($tagXs[$i], 413, 145, 18)) -Alignment ([System.Drawing.StringAlignment]::Center)
            }
        }
        else {
            Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new(0, 0, 1464, 82)) -Color ([System.Drawing.Color]::FromArgb(244, 251, 247, 239))
            $title = New-Font -Family 'Georgia' -Size 43 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 17 -Style ([System.Drawing.FontStyle]::Bold)
            $tag = New-Font -Family 'Bahnschrift' -Size 16 -Style ([System.Drawing.FontStyle]::Bold)
            Draw-Text -Graphics $graphics -Text 'VOM BÜRO BIS ZUM WOCHENENDE' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(150, 7, 1164, 50)) -Alignment ([System.Drawing.StringAlignment]::Center)
            Draw-Text -Graphics $graphics -Text 'EIN LOOK  ·  VIELE MOMENTE' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(350, 55, 764, 22)) -Alignment ([System.Drawing.StringAlignment]::Center)
            $tagXs = @(85, 570, 1055); $tags = @('BÜRO', 'STADT', 'WOCHENENDE')
            for ($i = 0; $i -lt 3; $i++) {
                Fill-AlphaRect -Graphics $graphics -Rect ([System.Drawing.RectangleF]::new($tagXs[$i], 548, 250, 34)) -Color ([System.Drawing.Color]::FromArgb(170, 18, 43, 71))
                Draw-Text -Graphics $graphics -Text $tags[$i] -Font $tag -Color ([System.Drawing.Color]::White) -Rect ([System.Drawing.RectangleF]::new($tagXs[$i], 556, 250, 22)) -Alignment ([System.Drawing.StringAlignment]::Center)
            }
        }
        $title.Dispose(); $sub.Dispose(); $tag.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $Output
    }
    finally { $graphics.Dispose(); $canvas.Dispose() }
}

function New-SizeGuide {
    param([string]$Source, [string]$Output, [int]$Width, [int]$Height, [bool]$Mobile)
    $base = New-BaseImage -Source $Source -Width $Width -Height $Height
    $canvas = $base.Canvas; $graphics = $base.Graphics
    try {
        $navy = [System.Drawing.Color]::FromArgb(255, 18, 43, 71)
        $rows = @(
            @('S', '112', '48', '63', '71'), @('M', '117', '49,5', '63,7', '72'),
            @('L', '122', '51', '64,4', '73'), @('XL', '127', '52,5', '65,1', '74'),
            @('XXL', '132', '54', '65,8', '75'), @('3XL', '137', '55,5', '66,5', '76'),
            @('4XL', '142', '57', '67,2', '77'), @('5XL', '147', '58,5', '67,9', '78')
        )
        $headers = @('GRÖSSE', 'BRUST', 'SCHULTER', 'ÄRMEL', 'LÄNGE')
        if ($Mobile) {
            $title = New-Font -Family 'Georgia' -Size 25 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 12
            $head = New-Font -Family 'Bahnschrift' -Size 9 -Style ([System.Drawing.FontStyle]::Bold)
            $cell = New-Font -Family 'Bahnschrift' -Size 9
            Draw-Text -Graphics $graphics -Text 'GRÖSSENTABELLE' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(32, 18, 360, 34))
            Draw-Text -Graphics $graphics -Text 'Maße am Kleidungsstück · Angaben in cm' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(34, 52, 350, 20))
            $tableX = 16; $tableY = 108; $rowH = 28; $colWidths = @(56, 76, 88, 76, 76)
        }
        else {
            $title = New-Font -Family 'Georgia' -Size 43 -Style ([System.Drawing.FontStyle]::Bold)
            $sub = New-Font -Family 'Bahnschrift' -Size 17
            $head = New-Font -Family 'Bahnschrift' -Size 14 -Style ([System.Drawing.FontStyle]::Bold)
            $cell = New-Font -Family 'Bahnschrift' -Size 14
            Draw-Text -Graphics $graphics -Text 'GRÖSSENTABELLE' -Font $title -Color $navy -Rect ([System.Drawing.RectangleF]::new(75, 34, 760, 54))
            Draw-Accent -Graphics $graphics -X 77 -Y 95 -Width 75
            Draw-Text -Graphics $graphics -Text 'Maße am Kleidungsstück · Angaben in cm' -Font $sub -Color $navy -Rect ([System.Drawing.RectangleF]::new(77, 108, 780, 24))
            $tableX = 47; $tableY = 160; $rowH = 41; $colWidths = @(105, 185, 200, 185, 175)
        }
        $headerBrush = [System.Drawing.SolidBrush]::new($navy)
        $rowA = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(238, 252, 249, 243))
        $rowB = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(230, 239, 231, 219))
        $grid = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(90, 18, 43, 71), 1)
        $x = $tableX
        for ($c = 0; $c -lt 5; $c++) {
            $rect = [System.Drawing.Rectangle]::new($x, $tableY, $colWidths[$c], $rowH)
            $graphics.FillRectangle($headerBrush, $rect); $graphics.DrawRectangle($grid, $rect)
            Draw-Text -Graphics $graphics -Text $headers[$c] -Font $head -Color ([System.Drawing.Color]::White) -Rect ([System.Drawing.RectangleF]::new($x + 4, $tableY + $(if ($Mobile) { 8 } else { 12 }), $colWidths[$c] - 8, 20)) -Alignment ([System.Drawing.StringAlignment]::Center)
            $x += $colWidths[$c]
        }
        for ($r = 0; $r -lt $rows.Count; $r++) {
            $x = $tableX; $y = $tableY + (($r + 1) * $rowH); $brush = if (($r % 2) -eq 0) { $rowA } else { $rowB }
            for ($c = 0; $c -lt 5; $c++) {
                $rect = [System.Drawing.Rectangle]::new($x, $y, $colWidths[$c], $rowH)
                $graphics.FillRectangle($brush, $rect); $graphics.DrawRectangle($grid, $rect)
                $value = if ($c -eq 0) { $rows[$r][$c] } else { $rows[$r][$c] + ' cm' }
                Draw-Text -Graphics $graphics -Text $value -Font $cell -Color $navy -Rect ([System.Drawing.RectangleF]::new($x + 3, $y + $(if ($Mobile) { 8 } else { 12 }), $colWidths[$c] - 6, 20)) -Alignment ([System.Drawing.StringAlignment]::Center)
                $x += $colWidths[$c]
            }
        }
        $headerBrush.Dispose(); $rowA.Dispose(); $rowB.Dispose(); $grid.Dispose()
        $title.Dispose(); $sub.Dispose(); $head.Dispose(); $cell.Dispose()
        Save-Jpeg -Bitmap $canvas -Path $Output
    }
    finally { $graphics.Dispose(); $canvas.Dispose() }
}

New-Hero -Source (Join-Path $srcDir '01-hero-desktop-source.png') -Output (Join-Path $outDir '01-hero-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-Hero -Source (Join-Path $srcDir '01-hero-mobile-source.png') -Output (Join-Path $outDir '01-hero-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true
New-Details -Source (Join-Path $srcDir '02-details-desktop-source.png') -Output (Join-Path $outDir '02-details-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-Details -Source (Join-Path $srcDir '02-details-mobile-source.png') -Output (Join-Path $outDir '02-details-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true
New-Colors -Source (Join-Path $srcDir '03-colors-desktop-source.png') -Output (Join-Path $outDir '03-colors-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-Colors -Source (Join-Path $srcDir '03-colors-mobile-source.png') -Output (Join-Path $outDir '03-colors-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true
New-Occasions -Source (Join-Path $srcDir '04-occasions-desktop-source.png') -Output (Join-Path $outDir '04-occasions-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-Occasions -Source (Join-Path $srcDir '04-occasions-mobile-source.png') -Output (Join-Path $outDir '04-occasions-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true
New-SizeGuide -Source (Join-Path $srcDir '05-size-desktop-source.png') -Output (Join-Path $outDir '05-size-guide-desktop-1464x600.jpg') -Width 1464 -Height 600 -Mobile $false
New-SizeGuide -Source (Join-Path $srcDir '05-size-mobile-source.png') -Output (Join-Path $outDir '05-size-guide-mobile-600x450.jpg') -Width 600 -Height 450 -Mobile $true

Get-ChildItem -LiteralPath $outDir -Filter '*.jpg' | Sort-Object Name | ForEach-Object {
    $check = [System.Drawing.Image]::FromFile($_.FullName)
    try { [PSCustomObject]@{ File = $_.Name; Width = $check.Width; Height = $check.Height; Bytes = $_.Length } }
    finally { $check.Dispose() }
} | Format-Table -AutoSize
