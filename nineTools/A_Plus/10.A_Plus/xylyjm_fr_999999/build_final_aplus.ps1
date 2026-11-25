Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'

$base = $PSScriptRoot
$outDir = Join-Path $base 'photo\final'
$refs = Join-Path $base 'references'
$gen = 'C:\Users\xmzj\.codex\generated_images\01a123b0-7768-7160-8ce3-8e76df6cad1a'
$W = 1464
$H = 600
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$ink = [System.Drawing.Color]::FromArgb(255, 12, 5, 18)
$cream = [System.Drawing.Color]::FromArgb(255, 255, 239, 208)
$orange = [System.Drawing.Color]::FromArgb(255, 255, 139, 26)
$red = [System.Drawing.Color]::FromArgb(255, 239, 55, 50)
$yellow = [System.Drawing.Color]::FromArgb(255, 248, 199, 57)
$ice = [System.Drawing.Color]::FromArgb(255, 183, 221, 247)
$violet = [System.Drawing.Color]::FromArgb(255, 52, 20, 64)

function Set-Quality($g) {
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
}

function Draw-Cover($g, $path) {
    $im = [System.Drawing.Image]::FromFile($path)
    $scale = [Math]::Max($W / $im.Width, $H / $im.Height)
    $dw = [int]($im.Width * $scale)
    $dh = [int]($im.Height * $scale)
    $g.DrawImage($im, [int](($W - $dw) / 2), [int](($H - $dh) / 2), $dw, $dh)
    $im.Dispose()
}

function Draw-Contain($g, $path) {
    $im = [System.Drawing.Image]::FromFile($path)
    $scale = [Math]::Min($W / $im.Width, $H / $im.Height)
    $dw = [int]($im.Width * $scale)
    $dh = [int]($im.Height * $scale)
    $g.DrawImage($im, [int](($W - $dw) / 2), [int](($H - $dh) / 2), $dw, $dh)
    $im.Dispose()
}

function New-PhotoCanvas($source) {
    $bmp = [System.Drawing.Bitmap]::new($W, $H)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    Set-Quality $g
    Draw-Cover $g $source
    $shade = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(118, 7, 3, 14))
    $g.FillRectangle($shade, 0, 0, $W, $H)
    $shade.Dispose()
    Draw-Contain $g $source
    return [PSCustomObject]@{ Bitmap = $bmp; Graphics = $g }
}

function Save-Canvas($canvas, $name) {
    $canvas.Graphics.Dispose()
    $canvas.Bitmap.Save((Join-Path $outDir $name), [System.Drawing.Imaging.ImageFormat]::Jpeg)
    $canvas.Bitmap.Dispose()
}

function Draw-FitText($g, $text, $fontName, $maxSize, $minSize, $x, $y, $width, $color, $shadowColor) {
    $size = $maxSize
    do {
        $font = [System.Drawing.Font]::new($fontName, $size, [System.Drawing.FontStyle]::Regular)
        $measure = $g.MeasureString($text, $font)
        if ($measure.Width -le $width -or $size -le $minSize) { break }
        $font.Dispose()
        $size -= 2
    } while ($true)
    $shadow = [System.Drawing.SolidBrush]::new($shadowColor)
    $foreground = [System.Drawing.SolidBrush]::new($color)
    $g.DrawString($text, $font, $shadow, $x + 3, $y + 4)
    $g.DrawString($text, $font, $foreground, $x, $y)
    $shadow.Dispose()
    $foreground.Dispose()
    $font.Dispose()
}

function Draw-Note($g, $text, $x, $y, $width, $color) {
    $font = [System.Drawing.Font]::new('Segoe Print', 18, [System.Drawing.FontStyle]::Bold)
    $brush = [System.Drawing.SolidBrush]::new($color)
    $fmt = [System.Drawing.StringFormat]::new()
    $fmt.Trimming = [System.Drawing.StringTrimming]::Word
    $g.DrawString($text, $font, $brush, [System.Drawing.RectangleF]::new($x, $y, $width, 74), $fmt)
    $fmt.Dispose()
    $brush.Dispose()
    $font.Dispose()
}

function Draw-Web($g, $x, $y, $r, $color, $flip) {
    $pen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(160, $color.R, $color.G, $color.B), 2)
    $dir = if ($flip) { -1 } else { 1 }
    for ($i = 0; $i -le 5; $i++) {
        $angle = ($i * 14 + 10) * [Math]::PI / 180
        $g.DrawLine($pen, $x, $y, [int]($x + $dir * $r * [Math]::Cos($angle)), [int]($y + $r * [Math]::Sin($angle)))
    }
    for ($j = 1; $j -le 3; $j++) {
        $d = [int]($r * $j / 3)
        if ($flip) { $g.DrawArc($pen, $x - $d, $y, $d * 2, $d * 2, 0, 88) } else { $g.DrawArc($pen, $x - $d, $y, $d * 2, $d * 2, 92, 88) }
    }
    $pen.Dispose()
}

function Draw-Bats($g, $x, $y, $color, $scale) {
    $brush = [System.Drawing.SolidBrush]::new($color)
    foreach ($p in @(@(0,0), @(34,12), @(68,-6), @(106,19), @(150,4))) {
        $px = $x + $p[0] * $scale
        $py = $y + $p[1] * $scale
        $points = [System.Drawing.Point[]]@(
            [System.Drawing.Point]::new($px, $py + 6 * $scale),
            [System.Drawing.Point]::new($px + 7 * $scale, $py),
            [System.Drawing.Point]::new($px + 13 * $scale, $py + 8 * $scale),
            [System.Drawing.Point]::new($px + 19 * $scale, $py),
            [System.Drawing.Point]::new($px + 27 * $scale, $py + 6 * $scale),
            [System.Drawing.Point]::new($px + 14 * $scale, $py + 12 * $scale)
        )
        $g.FillPolygon($brush, $points)
    }
    $brush.Dispose()
}

function Draw-Pumpkin($g, $x, $y, $s) {
    $fill = [System.Drawing.SolidBrush]::new($orange)
    $dark = [System.Drawing.SolidBrush]::new($ink)
    $stem = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 96, 141, 39))
    $g.FillEllipse($fill, $x, $y + 5, $s, [int]($s * .82))
    $g.FillEllipse($fill, $x + [int]($s * .12), $y, [int]($s * .76), $s)
    $g.FillRectangle($stem, $x + [int]($s * .42), $y - [int]($s * .13), [int]($s * .18), [int]($s * .2))
    $g.FillPolygon($dark, [System.Drawing.Point[]]@([System.Drawing.Point]::new($x + [int]($s*.23),$y+[int]($s*.38)),[System.Drawing.Point]::new($x+[int]($s*.40),$y+[int]($s*.30)),[System.Drawing.Point]::new($x+[int]($s*.36),$y+[int]($s*.50))))
    $g.FillPolygon($dark, [System.Drawing.Point[]]@([System.Drawing.Point]::new($x + [int]($s*.62),$y+[int]($s*.30)),[System.Drawing.Point]::new($x+[int]($s*.79),$y+[int]($s*.38)),[System.Drawing.Point]::new($x+[int]($s*.65),$y+[int]($s*.50))))
    $pen = [System.Drawing.Pen]::new($dark, [int]([Math]::Max(2,$s*.07)))
    $g.DrawArc($pen, $x+[int]($s*.22), $y+[int]($s*.42), [int]($s*.56), [int]($s*.34), 5, 165)
    $pen.Dispose()
    $fill.Dispose(); $dark.Dispose(); $stem.Dispose()
}

function Draw-Sparkles($g, $x, $y, $count, $color) {
    $pen = [System.Drawing.Pen]::new($color, 2)
    for ($i = 0; $i -lt $count; $i++) {
        $px = $x + (($i * 47) % 260)
        $py = $y + (($i * 31) % 130)
        $r = 4 + (($i % 3) * 2)
        $g.DrawLine($pen, $px-$r, $py, $px+$r, $py)
        $g.DrawLine($pen, $px, $py-$r, $px, $py+$r)
    }
    $pen.Dispose()
}

function Draw-DiagonalRibbon($g, $text, $x, $y, $w, $color) {
    $points = [System.Drawing.Point[]]@([System.Drawing.Point]::new($x,$y+24),[System.Drawing.Point]::new($x+$w,$y),[System.Drawing.Point]::new($x+$w-25,$y+72),[System.Drawing.Point]::new($x,$y+96))
    $b = [System.Drawing.SolidBrush]::new($color)
    $g.FillPolygon($b, $points)
    $b.Dispose()
    Draw-FitText $g $text 'Bauhaus 93' 36 24 ($x+30) ($y+18) ($w-60) $ink ([System.Drawing.Color]::FromArgb(0,0,0,0))
}

function Draw-ImageCircle($g, $path, $x, $y, $d, $sx, $sy, $sw, $sh, $edge) {
    $ring = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(210, $edge.R, $edge.G, $edge.B))
    $g.FillEllipse($ring, $x-7, $y-7, $d+14, $d+14)
    $ring.Dispose()
    $inside = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 54, 8, 20))
    $g.FillEllipse($inside, $x, $y, $d, $d)
    $inside.Dispose()
    $clip = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $clip.AddEllipse($x, $y, $d, $d)
    $state = $g.Save()
    $g.SetClip($clip)
    $im = [System.Drawing.Bitmap]::new($path)
    $im.MakeTransparent([System.Drawing.Color]::White)
    $g.DrawImage($im, [System.Drawing.Rectangle]::new($x,$y,$d,$d), $sx,$sy,$sw,$sh, [System.Drawing.GraphicsUnit]::Pixel)
    $im.Dispose()
    $g.Restore($state)
    $clip.Dispose()
}

# Opening poster
$hero = New-PhotoCanvas (Join-Path $gen 'exec-c30b7bac-648c-4230-8a65-94d6f7965040.png')
$g = $hero.Graphics
$dark = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(130, 3, 3, 12)); $g.FillRectangle($dark,0,0,670,600); $dark.Dispose()
Draw-Web $g 0 0 255 $orange $false
Draw-Bats $g 72 80 $orange 1
Draw-FitText $g 'ENTREZ' 'Showcard Gothic' 64 40 68 155 470 $orange $ink
Draw-FitText $g 'DANS LA NUIT' 'Chiller' 74 44 66 238 520 $cream $ink
Draw-Note $g "Des motifs qui réveillent l'instinct Halloween." 76 330 420 $cream
Draw-Pumpkin $g 470 414 74
Draw-Sparkles $g 72 435 6 $yellow
Save-Canvas $hero '01-entrez-dans-la-nuit.jpg'

# Graphic-heavy print poster
$print = New-PhotoCanvas (Join-Path $gen 'exec-9ba6ebb4-edfa-4b7e-b703-1054cc81b897.png')
$g = $print.Graphics
$smoke = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(115, 40, 1, 18)); $g.FillEllipse($smoke,760,-90,780,720); $smoke.Dispose()
Draw-Web $g 1445 0 230 $red $true
Draw-FitText $g 'BOO !' 'Jokerman' 76 46 860 60 420 $orange $ink
Draw-FitText $g 'IMPRIMÉE' 'Showcard Gothic' 44 28 855 150 425 $cream $ink
Draw-Note $g "Crânes, toiles et citrouilles : l'énergie est dans le motif." 862 214 405 $cream
Draw-Pumpkin $g 1228 405 90
Draw-Bats $g 875 360 $red 1
Save-Canvas $print '02-boo-imprimee.jpg'

# Collection poster: no color-count claim
$style = New-PhotoCanvas (Join-Path $gen 'exec-a01e855f-7093-4178-b815-007690471202.png')
$g = $style.Graphics
$fog = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(105, 17, 3, 25)); $g.FillRectangle($fog,0,450,1464,150); $fog.Dispose()
Draw-DiagonalRibbon $g 'CHOISIS TA VIBE' 80 440 650 $yellow
Draw-FitText $g "L'ALLURE" 'Ravie' 58 34 90 100 450 $cream $ink
Draw-FitText $g "D'HALLOWEEN" 'Showcard Gothic' 38 25 92 176 430 $orange $ink
Draw-Bats $g 82 270 $cream 1
Draw-Web $g 0 560 150 $yellow $false
Save-Canvas $style '03-choisis-ta-vibe.jpg'

# Carousel: each page uses a distinct typography position and accent system
$walk = New-PhotoCanvas (Join-Path $gen 'exec-4032a9ca-156e-4a34-8bed-3c58a6fa6d78.png')
$g = $walk.Graphics
Draw-FitText $g 'ÇA BOUGE !' 'Kristen ITC' 54 32 72 55 410 $cream $ink
$speed = [System.Drawing.Pen]::new($orange,4); $g.DrawLine($speed,74,137,305,112); $g.DrawLine($speed,82,150,255,132); $speed.Dispose()
Draw-Note $g 'Prêt à traverser la nuit sans ralentir.' 75 175 330 $orange
Draw-Bats $g 74 270 $orange 1
Draw-Pumpkin $g 345 418 56
Draw-Web $g 0 535 160 $orange $false
Draw-Sparkles $g 95 382 6 $orange
Save-Canvas $walk '04-carousel-pas-de-nuit.jpg'

$door = New-PhotoCanvas (Join-Path $gen 'exec-380f6f18-5ea9-4e27-871d-f4f7dc078044.png')
$g = $door.Graphics
$moon = [System.Drawing.SolidBrush]::new($ice); $g.FillEllipse($moon,1200,42,86,86); $moon.Dispose()
$moonCut = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255,8,8,19)); $g.FillEllipse($moonCut,1230,30,86,86); $moonCut.Dispose()
Draw-FitText $g 'MINUIT' 'Broadway' 48 30 958 182 350 $cream $ink
Draw-FitText $g 'SONNE' 'Chiller' 70 42 960 240 330 $ice $ink
Draw-Note $g 'Capuche en place. La sortie est lancée.' 970 344 335 $ice
Draw-Web $g 1460 545 135 $ice $true
Save-Canvas $door '05-carousel-minuit.jpg'

$market = New-PhotoCanvas (Join-Path $gen 'exec-2f71ef94-04d5-4ec4-a320-457eb1f7b2f8.png')
$g = $market.Graphics
Draw-Pumpkin $g 74 54 105
Draw-FitText $g 'ÉCLAT' 'Bauhaus 93' 60 34 207 73 360 $yellow $ink
Draw-FitText $g 'AMBRÉ' 'Freestyle Script' 66 38 208 140 370 $cream $ink
Draw-Sparkles $g 70 240 8 $yellow
Draw-Note $g 'Une citrouille à la main, la rue devient scène.' 74 376 390 $cream
Draw-Web $g 0 545 150 $yellow $false
Draw-Bats $g 90 520 $yellow 1
Save-Canvas $market '06-carousel-eclat-ambre.jpg'

$party = New-PhotoCanvas (Join-Path $gen 'exec-53175bff-eee0-4c80-b617-c68c3435bab2.png')
$g = $party.Graphics
$burst = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(185, 88, 8, 18)); $g.FillEllipse($burst,930,35,450,450); $burst.Dispose()
Draw-FitText $g 'FAIS-TOI' 'Showcard Gothic' 44 28 1002 100 350 $cream $ink
Draw-FitText $g 'VOIR' 'Jokerman' 66 42 1040 154 290 $red $ink
Draw-Bats $g 1005 275 $red 1
Draw-Sparkles $g 1040 370 7 $orange
Draw-Note $g 'Un demi-tour et la fête change de rythme.' 1007 448 350 $cream
Save-Canvas $party '07-carousel-fete.jpg'

$moon = New-PhotoCanvas (Join-Path $gen 'exec-abc670cf-1df3-4988-bcbe-a275bed5a10f.png')
$g = $moon.Graphics
$wash = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(120, 13, 28, 65)); $g.FillEllipse($wash,-180,310,760,420); $wash.Dispose()
Draw-FitText $g 'CLAIR' 'Mistral' 72 42 65 370 280 $ice $ink
Draw-FitText $g 'DE LUNE' 'Showcard Gothic' 42 28 190 420 340 $cream $ink
Draw-Note $g 'Une pause au bord de la brume.' 75 485 345 $ice
Draw-Web $g 0 0 180 $ice $false
Draw-Bats $g 78 285 $ice 1
Save-Canvas $moon '08-carousel-clair-de-lune.jpg'

# Red product and four true close-up crops without a screenshot-style product card
$detailBmp = [System.Drawing.Bitmap]::new($W,$H)
$dg = [System.Drawing.Graphics]::FromImage($detailBmp)
Set-Quality $dg
$detailGrad = [System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Point]::new(0,0),[System.Drawing.Point]::new($W,$H),[System.Drawing.Color]::FromArgb(255,23,6,18),[System.Drawing.Color]::FromArgb(255,92,12,19))
$dg.FillRectangle($detailGrad,0,0,$W,$H); $detailGrad.Dispose()
$rand = [System.Random]::new(17)
$splatter = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(140,245,66,39))
for($i=0;$i -lt 120;$i++){ $x=$rand.Next(10,1430); $y=$rand.Next(20,580); $s=$rand.Next(2,12); $dg.FillEllipse($splatter,$x,$y,$s,$s) }
$splatter.Dispose()
Draw-Web $dg 0 0 220 $orange $false
Draw-FitText $dg 'ZOOM MAGIQUE' 'Jokerman' 48 30 526 28 570 $cream $ink
Draw-Note $dg 'Rouge & noir : chaque détail raconte sa propre histoire.' 540 97 580 $orange
$product = [System.Drawing.Bitmap]::new((Join-Path $refs 'product-reference-01.jpg'))
$product.MakeTransparent([System.Drawing.Color]::White)
$dg.DrawImage($product,30,48,470,520)
$product.Dispose()
$hood = Join-Path $refs 'product-reference-05.jpg'
$pants = Join-Path $refs 'product-reference-06.jpg'
Draw-ImageCircle $dg $hood 565 166 168 450 35 750 650 $orange
Draw-ImageCircle $dg $hood 810 166 168 520 300 600 760 $yellow
Draw-ImageCircle $dg $pants 1055 166 168 420 400 550 600 $orange
Draw-ImageCircle $dg $pants 690 390 168 330 880 500 600 $yellow
Draw-Bats $dg 920 430 $cream 1
Draw-Pumpkin $dg 1190 386 72
$dg.Dispose()
$detailBmp.Save((Join-Path $outDir '09-zoom-magique.jpg'),[System.Drawing.Imaging.ImageFormat]::Jpeg)
$detailBmp.Dispose()

# Group/lifestyle poster
$friends = New-PhotoCanvas (Join-Path $gen 'exec-ea0dd05f-8727-4b14-8f45-dc08187699e4.png')
$g = $friends.Graphics
$tape = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(225, 244, 133, 26))
$g.FillPolygon($tape,[System.Drawing.Point[]]@([System.Drawing.Point]::new(54,72),[System.Drawing.Point]::new(610,34),[System.Drawing.Point]::new(628,104),[System.Drawing.Point]::new(72,142)))
$tape.Dispose()
Draw-FitText $g 'ENTRE AMIS' 'Cooper Black' 46 30 82 69 470 $ink ([System.Drawing.Color]::FromArgb(0,0,0,0))
Draw-FitText $g 'UN SOIR À RACONTER' 'Showcard Gothic' 37 23 72 175 460 $cream $ink
Draw-Note $g "Des frissons, des sourires, et l'Halloween en grand." 75 276 410 $cream
Draw-Pumpkin $g 75 413 72
Draw-Sparkles $g 220 430 8 $orange
Save-Canvas $friends '10-entre-amis.jpg'

# Sizing guide: source chart treated as an editorial poster, not a screenshot card
$sizeBmp = [System.Drawing.Bitmap]::new($W,$H)
$sg = [System.Drawing.Graphics]::FromImage($sizeBmp)
Set-Quality $sg
$sizeGrad = [System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Point]::new(0,0),[System.Drawing.Point]::new($W,$H),[System.Drawing.Color]::FromArgb(255,18,7,27),[System.Drawing.Color]::FromArgb(255,72,18,46))
$sg.FillRectangle($sizeGrad,0,0,$W,$H); $sizeGrad.Dispose()
Draw-Web $sg 0 0 190 $orange $false
Draw-FitText $sg 'À VOS MESURES' 'Showcard Gothic' 48 30 67 42 650 $cream $ink
Draw-Note $sg 'Tableau de tailles du vêtement.' 70 104 630 $orange
$frame = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(230, 247, 143, 30))
$sg.FillPolygon($frame,[System.Drawing.Point[]]@([System.Drawing.Point]::new(42,160),[System.Drawing.Point]::new(1045,143),[System.Drawing.Point]::new(1064,555),[System.Drawing.Point]::new(34,570)))
$frame.Dispose()
$chart = [System.Drawing.Image]::FromFile((Join-Path $refs 'product-reference-04.jpg'))
$sg.DrawImage($chart,49,168,990,365)
$chart.Dispose()
$redProduct = [System.Drawing.Bitmap]::new((Join-Path $refs 'product-reference-01.jpg'))
$redProduct.MakeTransparent([System.Drawing.Color]::White)
$sg.DrawImage($redProduct,1080,103,325,435)
$redProduct.Dispose()
Draw-Pumpkin $sg 1260 450 70
Draw-Bats $sg 1150 56 $orange 1
$sg.Dispose()
$sizeBmp.Save((Join-Path $outDir '11-a-vos-mesures.jpg'),[System.Drawing.Imaging.ImageFormat]::Jpeg)
$sizeBmp.Dispose()

Get-ChildItem -LiteralPath $outDir -Filter '*.jpg' | Sort-Object Name | ForEach-Object {
    $image = [System.Drawing.Image]::FromFile($_.FullName)
    [PSCustomObject]@{ Name = $_.Name; Dimensions = "$($image.Width)×$($image.Height)"; Bytes = $_.Length }
    $image.Dispose()
} | Format-Table -AutoSize
