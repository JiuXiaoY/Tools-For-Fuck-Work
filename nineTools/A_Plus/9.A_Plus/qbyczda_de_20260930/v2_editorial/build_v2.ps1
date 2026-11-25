param()

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

if (-not ('WhiteCutout' -as [type])) {
    Add-Type -ReferencedAssemblies @('System.Drawing.Common','System.Drawing.Primitives','System.Private.Windows.GdiPlus','System.Private.Windows.Core','System.Runtime.InteropServices') -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class WhiteCutout {
    public static Bitmap Load(string path, byte threshold) {
        using (var source = new Bitmap(path)) {
            var bmp = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(bmp)) g.DrawImageUnscaled(source, 0, 0);
            var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
            var data = bmp.LockBits(rect, ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            int stride = data.Stride;
            byte[] px = new byte[stride * bmp.Height];
            Marshal.Copy(data.Scan0, px, 0, px.Length);
            bool[] seen = new bool[bmp.Width * bmp.Height];
            int[] queue = new int[bmp.Width * bmp.Height];
            int head = 0, tail = 0;

            Action<int,int> enqueue = (x,y) => {
                int id = y * bmp.Width + x;
                if (seen[id]) return;
                seen[id] = true;
                int p = y * stride + x * 4;
                int b = px[p], g = px[p+1], r = px[p+2];
                int max = Math.Max(r, Math.Max(g,b));
                int min = Math.Min(r, Math.Min(g,b));
                if (min >= threshold && max - min <= 22) queue[tail++] = id;
            };

            for (int x=0; x<bmp.Width; x++) { enqueue(x,0); enqueue(x,bmp.Height-1); }
            for (int y=0; y<bmp.Height; y++) { enqueue(0,y); enqueue(bmp.Width-1,y); }
            while (head < tail) {
                int id = queue[head++];
                int x = id % bmp.Width, y = id / bmp.Width;
                px[y * stride + x * 4 + 3] = 0;
                if (x > 0) enqueue(x-1,y);
                if (x+1 < bmp.Width) enqueue(x+1,y);
                if (y > 0) enqueue(x,y-1);
                if (y+1 < bmp.Height) enqueue(x,y+1);
            }
            Marshal.Copy(px, 0, data.Scan0, px.Length);
            bmp.UnlockBits(data);
            return bmp;
        }
    }

    public static Rectangle Bounds(Bitmap bmp) {
        var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
        var data = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        int stride = data.Stride;
        byte[] px = new byte[stride * bmp.Height];
        Marshal.Copy(data.Scan0, px, 0, px.Length);
        bmp.UnlockBits(data);
        int minX=bmp.Width, minY=bmp.Height, maxX=-1, maxY=-1;
        for (int y=0; y<bmp.Height; y++) for (int x=0; x<bmp.Width; x++) {
            if (px[y*stride+x*4+3] > 20) {
                if (x<minX) minX=x; if (x>maxX) maxX=x;
                if (y<minY) minY=y; if (y>maxY) maxY=y;
            }
        }
        return maxX < 0 ? rect : Rectangle.FromLTRB(minX,minY,maxX+1,maxY+1);
    }
}
"@
}

$Root = $PSScriptRoot
$APlusRoot = Split-Path (Split-Path $Root -Parent) -Parent
$SourceDir = Join-Path $APlusRoot 'enjinia_fr_20260922\enjinia\sources'
$GeneratedDir = Join-Path $Root '_generated'
$PreviewDir = Join-Path $Root '_preview'
$MobileDir = Join-Path $Root 'mobile_600x450'
New-Item -ItemType Directory -Path $PreviewDir -Force | Out-Null
New-Item -ItemType Directory -Path $MobileDir -Force | Out-Null

function C([string]$Hex, [int]$Alpha = 255) {
    $h = $Hex.TrimStart('#')
    [System.Drawing.Color]::FromArgb($Alpha, [Convert]::ToInt32($h.Substring(0,2),16), [Convert]::ToInt32($h.Substring(2,2),16), [Convert]::ToInt32($h.Substring(4,2),16))
}

function New-Canvas([int]$W, [int]$H, [string]$A, [string]$B, [string]$Mode='Horizontal') {
    $bmp = [System.Drawing.Bitmap]::new($W,$H)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $gm = if($Mode -eq 'Vertical'){[System.Drawing.Drawing2D.LinearGradientMode]::Vertical}else{[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal}
    $br = [System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,$W,$H),(C $A),(C $B),$gm)
    $g.FillRectangle($br,0,0,$W,$H); $br.Dispose()
    [pscustomobject]@{Bitmap=$bmp;Graphics=$g}
}

function FontStyle([string]$Style) {
    switch($Style){'Bold'{[System.Drawing.FontStyle]::Bold}'Italic'{[System.Drawing.FontStyle]::Italic}'BoldItalic'{[System.Drawing.FontStyle]::Bold -bor [System.Drawing.FontStyle]::Italic}default{[System.Drawing.FontStyle]::Regular}}
}

function Text($G,[string]$Value,[System.Drawing.RectangleF]$R,[float]$Size,[System.Drawing.Color]$Color,[string]$Family='Bahnschrift',[string]$Style='Regular',[string]$Align='Near',[string]$VAlign='Near') {
    $font=[System.Drawing.Font]::new($Family,$Size,(FontStyle $Style),[System.Drawing.GraphicsUnit]::Pixel)
    $br=[System.Drawing.SolidBrush]::new($Color)
    $sf=[System.Drawing.StringFormat]::new(); $sf.Trimming=[System.Drawing.StringTrimming]::EllipsisWord
    $sf.Alignment=switch($Align){'Center'{[System.Drawing.StringAlignment]::Center}'Far'{[System.Drawing.StringAlignment]::Far}default{[System.Drawing.StringAlignment]::Near}}
    $sf.LineAlignment=switch($VAlign){'Center'{[System.Drawing.StringAlignment]::Center}'Far'{[System.Drawing.StringAlignment]::Far}default{[System.Drawing.StringAlignment]::Near}}
    try{$G.DrawString($Value,$font,$br,$R,$sf)}finally{$sf.Dispose();$br.Dispose();$font.Dispose()}
}

function Fill($G,[System.Drawing.Rectangle]$R,[System.Drawing.Color]$Color){$b=[System.Drawing.SolidBrush]::new($Color);$G.FillRectangle($b,$R);$b.Dispose()}
function Rule($G,[int]$X1,[int]$Y1,[int]$X2,[int]$Y2,[System.Drawing.Color]$Color,[float]$Width=2){$p=[System.Drawing.Pen]::new($Color,$Width);$G.DrawLine($p,$X1,$Y1,$X2,$Y2);$p.Dispose()}

function Cover($G,[string]$Path,[System.Drawing.Rectangle]$Dest,[double]$FX=.5,[double]$FY=.5,[float]$Opacity=1) {
    $img=[System.Drawing.Image]::FromFile($Path)
    try{
        $scale=[Math]::Max($Dest.Width/$img.Width,$Dest.Height/$img.Height)
        $sw=$Dest.Width/$scale; $sh=$Dest.Height/$scale
        $sx=[Math]::Max(0,[Math]::Min($img.Width-$sw,($img.Width-$sw)*$FX)); $sy=[Math]::Max(0,[Math]::Min($img.Height-$sh,($img.Height-$sh)*$FY))
        $attrs=[System.Drawing.Imaging.ImageAttributes]::new()
        try{
            if($Opacity -lt 1){$m=[System.Drawing.Imaging.ColorMatrix]::new();$m.Matrix33=$Opacity;$attrs.SetColorMatrix($m)}
            $G.DrawImage($img,$Dest,[single]$sx,[single]$sy,[single]$sw,[single]$sh,[System.Drawing.GraphicsUnit]::Pixel,$attrs)
        }finally{$attrs.Dispose()}
    }finally{$img.Dispose()}
}

function Crop($G,[string]$Path,[System.Drawing.Rectangle]$Dest,[System.Drawing.Rectangle]$Src){$i=[System.Drawing.Image]::FromFile($Path);try{$G.DrawImage($i,$Dest,$Src.X,$Src.Y,$Src.Width,$Src.Height,[System.Drawing.GraphicsUnit]::Pixel)}finally{$i.Dispose()}}

$Cutouts=@{}
function Get-Cutout([string]$Path){if(-not $Cutouts.ContainsKey($Path)){$Cutouts[$Path]=[WhiteCutout]::Load($Path,238)};$Cutouts[$Path]}
function Cutout($G,[string]$Path,[System.Drawing.Rectangle]$Dest,[float]$Rotate=0,[bool]$Shadow=$true) {
    $img=Get-Cutout $Path; $src=[WhiteCutout]::Bounds($img)
    $scale=[Math]::Min($Dest.Width/$src.Width,$Dest.Height/$src.Height);$w=[int]($src.Width*$scale);$h=[int]($src.Height*$scale)
    $cx=$Dest.X+[int]($Dest.Width/2);$cy=$Dest.Y+[int]($Dest.Height/2)
    if($Shadow){$eb=[System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(55,0,0,0));$G.FillEllipse($eb,$cx-[int]($w*.34),$Dest.Bottom-30,[int]($w*.68),22);$eb.Dispose()}
    $state=$G.Save();$G.TranslateTransform($cx,$cy);if($Rotate -ne 0){$G.RotateTransform($Rotate)}
    try{$G.DrawImage($img,[System.Drawing.Rectangle]::new(-[int]($w/2),-[int]($h/2),$w,$h),$src.X,$src.Y,$src.Width,$src.Height,[System.Drawing.GraphicsUnit]::Pixel)}finally{$G.Restore($state)}
}

function BrushBand($G,[System.Drawing.Point[]]$Pts,[System.Drawing.Color]$Color){$b=[System.Drawing.SolidBrush]::new($Color);$G.FillPolygon($b,$Pts);$b.Dispose()}
function Tag($G,[string]$Value,[System.Drawing.Rectangle]$R,[System.Drawing.Color]$Bg,[System.Drawing.Color]$Fg){Fill $G $R $Bg;Text $G $Value ([System.Drawing.RectangleF]::new($R.X+10,$R.Y,$R.Width-20,$R.Height)) 15 $Fg 'Bahnschrift SemiBold Condensed' 'Bold' 'Center' 'Center'}

function SkullIcon($G,[int]$X,[int]$Y,[int]$S,[System.Drawing.Color]$Color){
    $b=[System.Drawing.SolidBrush]::new($Color);$dark=[System.Drawing.SolidBrush]::new((C '#071726'))
    try{
        $G.FillEllipse($b,$X,$Y,$S,[int]($S*.72));$G.FillRectangle($b,$X+[int]($S*.20),$Y+[int]($S*.48),[int]($S*.60),[int]($S*.34))
        $G.FillEllipse($dark,$X+[int]($S*.18),$Y+[int]($S*.25),[int]($S*.22),[int]($S*.22));$G.FillEllipse($dark,$X+[int]($S*.60),$Y+[int]($S*.25),[int]($S*.22),[int]($S*.22))
        $nose=[System.Drawing.Point[]]@([System.Drawing.Point]::new($X+[int]($S*.50),$Y+[int]($S*.47)),[System.Drawing.Point]::new($X+[int]($S*.42),$Y+[int]($S*.60)),[System.Drawing.Point]::new($X+[int]($S*.58),$Y+[int]($S*.60)));$G.FillPolygon($dark,$nose)
        $p=[System.Drawing.Pen]::new((C '#071726'),1.5);for($i=1;$i-lt 4;$i++){$tx=$X+[int]($S*.20)+[int]($i*$S*.15);$G.DrawLine($p,$tx,$Y+[int]($S*.62),$tx,$Y+[int]($S*.80))};$p.Dispose()
    }finally{$dark.Dispose();$b.Dispose()}
}

function BatIcon($G,[int]$X,[int]$Y,[int]$S,[System.Drawing.Color]$Color){
    $pts=[System.Drawing.Point[]]@(
        [System.Drawing.Point]::new($X,$Y+[int]($S*.35)),[System.Drawing.Point]::new($X+[int]($S*.18),$Y+[int]($S*.08)),[System.Drawing.Point]::new($X+[int]($S*.36),$Y+[int]($S*.30)),
        [System.Drawing.Point]::new($X+[int]($S*.50),$Y),[System.Drawing.Point]::new($X+[int]($S*.64),$Y+[int]($S*.30)),[System.Drawing.Point]::new($X+[int]($S*.82),$Y+[int]($S*.08)),
        [System.Drawing.Point]::new($X+$S,$Y+[int]($S*.35)),[System.Drawing.Point]::new($X+[int]($S*.78),$Y+[int]($S*.72)),[System.Drawing.Point]::new($X+[int]($S*.50),$Y+[int]($S*.54)),
        [System.Drawing.Point]::new($X+[int]($S*.22),$Y+[int]($S*.72))
    );$b=[System.Drawing.SolidBrush]::new($Color);$G.FillPolygon($b,$pts);$b.Dispose()
}

function PumpkinIcon($G,[int]$X,[int]$Y,[int]$S,[System.Drawing.Color]$Color){
    $b=[System.Drawing.SolidBrush]::new($Color);$dark=[System.Drawing.SolidBrush]::new((C '#071726'));$stem=[System.Drawing.SolidBrush]::new((C '#D8A85D'))
    try{
        $G.FillRectangle($stem,$X+[int]($S*.43),$Y,[int]($S*.15),[int]($S*.18));$G.FillEllipse($b,$X,$Y+[int]($S*.12),$S,[int]($S*.75))
        $left=[System.Drawing.Point[]]@([System.Drawing.Point]::new($X+[int]($S*.20),$Y+[int]($S*.40)),[System.Drawing.Point]::new($X+[int]($S*.34),$Y+[int]($S*.31)),[System.Drawing.Point]::new($X+[int]($S*.35),$Y+[int]($S*.50)));$G.FillPolygon($dark,$left)
        $right=[System.Drawing.Point[]]@([System.Drawing.Point]::new($X+[int]($S*.80),$Y+[int]($S*.40)),[System.Drawing.Point]::new($X+[int]($S*.66),$Y+[int]($S*.31)),[System.Drawing.Point]::new($X+[int]($S*.65),$Y+[int]($S*.50)));$G.FillPolygon($dark,$right)
        $G.FillRectangle($dark,$X+[int]($S*.28),$Y+[int]($S*.62),[int]($S*.44),[int]($S*.08))
        $p=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(110,7,23,38),1);$G.DrawArc($p,$X+[int]($S*.21),$Y+[int]($S*.14),[int]($S*.30),[int]($S*.70),270,180);$G.DrawArc($p,$X+[int]($S*.49),$Y+[int]($S*.14),[int]($S*.30),[int]($S*.70),90,180);$p.Dispose()
    }finally{$stem.Dispose();$dark.Dispose();$b.Dispose()}
}

function SparkIcon($G,[int]$X,[int]$Y,[int]$S,[System.Drawing.Color]$Color){$p=[System.Drawing.Pen]::new($Color,2);$G.DrawLine($p,$X+[int]($S/2),$Y,$X+[int]($S/2),$Y+$S);$G.DrawLine($p,$X,$Y+[int]($S/2),$X+$S,$Y+[int]($S/2));$G.DrawLine($p,$X+[int]($S*.18),$Y+[int]($S*.18),$X+[int]($S*.82),$Y+[int]($S*.82));$G.DrawLine($p,$X+[int]($S*.82),$Y+[int]($S*.18),$X+[int]($S*.18),$Y+[int]($S*.82));$p.Dispose()}

function SaveJpg([System.Drawing.Bitmap]$Bmp,[string]$Path,[long]$Quality=94){$codec=[System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders()|Where-Object MimeType -eq 'image/jpeg'|Select-Object -First 1;$ep=[System.Drawing.Imaging.EncoderParameters]::new(1);$ep.Param[0]=[System.Drawing.Imaging.EncoderParameter]::new([System.Drawing.Imaging.Encoder]::Quality,$Quality);try{$Bmp.Save($Path,$codec,$ep)}finally{$ep.Param[0].Dispose();$ep.Dispose()}}
function Close($C){$C.Graphics.Dispose();$C.Bitmap.Dispose()}

$ivory=C '#F4EBDD';$ink=C '#101A22';$navy=C '#071726';$orange=C '#F36C2B';$gold=C '#D8A85D';$white=C '#FFF9F0';$muted=C '#C6CDD1';$burg=C '#6D1B29'
$front=Join-Path $SourceDir 'product-01-2.jpg';$back=Join-Path $SourceDir 'product-01-3.jpg'

# 01 — cinematic hero, expressive typography inspired by the supplied references
$m=New-Canvas 1464 600 '#07131E' '#29141C'
Cover $m.Graphics (Join-Path $GeneratedDir 'hero-base.png') ([System.Drawing.Rectangle]::new(0,0,1464,600)) .50 .45
$ov=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,1050,600),[System.Drawing.Color]::FromArgb(242,5,16,27),[System.Drawing.Color]::FromArgb(0,5,16,27),[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal);$m.Graphics.FillRectangle($ov,0,0,1050,600);$ov.Dispose()
BrushBand $m.Graphics @([System.Drawing.Point]::new(55,69),[System.Drawing.Point]::new(372,52),[System.Drawing.Point]::new(389,96),[System.Drawing.Point]::new(61,111)) ([System.Drawing.Color]::FromArgb(235,$orange.R,$orange.G,$orange.B))
Text $m.Graphics 'DIE NACHT GEHÖRT DIR' ([System.Drawing.RectangleF]::new(72,63,302,42)) 19 $white 'Brush Script MT' 'Italic' 'Center' 'Center'
Text $m.Graphics "HALLOWEEN / FESTIVAL /`nPARTYNACHT" ([System.Drawing.RectangleF]::new(71,132,650,102)) 36 ([System.Drawing.Color]::FromArgb(210,$orange.R,$orange.G,$orange.B)) 'Showcard Gothic'
Text $m.Graphics "HALLOWEEN / FESTIVAL /`nPARTYNACHT" ([System.Drawing.RectangleF]::new(67,128,650,102)) 36 $white 'Showcard Gothic'
Text $m.Graphics "FÜR AUFTRITTE`nMIT CHARAKTER" ([System.Drawing.RectangleF]::new(68,245,540,105)) 46 $white 'Franklin Gothic Demi Cond' 'Bold'
Rule $m.Graphics 72 377 224 377 $orange 5
Text $m.Graphics 'Ausdrucksstarke Motive. Klare Blazer-Silhouette. Gemacht für Nächte, an die man sich erinnert.' ([System.Drawing.RectangleF]::new(72,397,480,72)) 20 (C '#D9DEE2')
Rule $m.Graphics 72 522 105 522 $orange 2
SkullIcon $m.Graphics 122 502 38 $white
PumpkinIcon $m.Graphics 174 504 36 $orange
SparkIcon $m.Graphics 224 510 25 $gold
SkullIcon $m.Graphics 264 502 38 $orange
PumpkinIcon $m.Graphics 318 504 36 $white
SparkIcon $m.Graphics 368 510 25 $gold
SkullIcon $m.Graphics 410 502 38 $white
Rule $m.Graphics 463 522 508 522 $orange 2
SaveJpg $m.Bitmap (Join-Path $Root '01-hero-1464x600.jpg');Close $m

# 02 — bright fashion-gallery detail story
$m=New-Canvas 1464 600 '#F8F1E7' '#D9E2E2'
Cover $m.Graphics (Join-Path $GeneratedDir 'detail-gallery.png') ([System.Drawing.Rectangle]::new(0,0,1464,600)) .5 .48
Fill $m.Graphics ([System.Drawing.Rectangle]::new(0,0,465,600)) ([System.Drawing.Color]::FromArgb(218,249,243,234))
Text $m.Graphics 'Designstudie' ([System.Drawing.RectangleF]::new(52,44,360,65)) 52 $burg 'Old English Text MT'
Text $m.Graphics 'DETAILS, DIE DEN LOOK PRÄGEN' ([System.Drawing.RectangleF]::new(54,118,360,58)) 29 $ink 'Franklin Gothic Demi Cond' 'Bold'
Rule $m.Graphics 55 190 222 190 $orange 5
Text $m.Graphics 'Revers, Motivführung und präzise Konturen werden wie Exponate einer Galerie inszeniert.' ([System.Drawing.RectangleF]::new(55,217,340,110)) 20 (C '#33404A')
Tag $m.Graphics 'KLAR  ·  AUSDRUCKSSTARK  ·  DETAILREICH' ([System.Drawing.Rectangle]::new(54,486,350,42)) $ink $white
Cutout $m.Graphics $front ([System.Drawing.Rectangle]::new(430,24,540,555)) -2 $true
$circles=@(
    @{D=[System.Drawing.Rectangle]::new(1010,42,205,205);S=[System.Drawing.Rectangle]::new(430,60,720,650);T='REVERS'},
    @{D=[System.Drawing.Rectangle]::new(1215,205,185,185);S=[System.Drawing.Rectangle]::new(220,380,720,720);T='PUZZLE-LINIEN'},
    @{D=[System.Drawing.Rectangle]::new(990,368,220,220);S=[System.Drawing.Rectangle]::new(700,390,700,760);T='MOTIVDETAIL'}
)
foreach($mcr in $circles){$gp=[System.Drawing.Drawing2D.GraphicsPath]::new();$gp.AddEllipse($mcr.D);$st=$m.Graphics.Save();$m.Graphics.SetClip($gp);Crop $m.Graphics $front $mcr.D $mcr.S;$m.Graphics.Restore($st);$p=[System.Drawing.Pen]::new($orange,5);$m.Graphics.DrawEllipse($p,$mcr.D);$p.Dispose();$gp.Dispose();Tag $m.Graphics $mcr.T ([System.Drawing.Rectangle]::new($mcr.D.X+28,$mcr.D.Bottom-24,$mcr.D.Width-56,32)) $ink $white}
Rule $m.Graphics 942 174 1008 144 $burg 2;Rule $m.Graphics 968 310 1213 298 $burg 2;Rule $m.Graphics 912 462 988 468 $burg 2
SaveJpg $m.Bitmap (Join-Path $Root '02-design-details-1464x600.jpg');Close $m

# 03 — three different actions and environments
$trip=@(
    @{Img='scene-cocktail-toast.png';Out='03-01-cocktail-toast-488x600.jpg';No='01';Top='COCKTAIL';Head='AUF DIE NACHT';Body='Ein spontaner Toast zwischen Farbe, Licht und Bewegung.';A='#F0B44F';Mode=1;FX=.51;FY=.46},
    @{Img='scene-festival-walk.png';Out='03-02-festival-walk-488x600.jpg';No='02';Top='FESTIVAL';Head='FARBE IN BEWEGUNG';Body='Im Schritt eingefangen – lebendig, sonnig und selbstbewusst.';A='#F36C2B';Mode=2;FX=.48;FY=.47},
    @{Img='scene-backstage-cuff.png';Out='03-03-backstage-cuff-488x600.jpg';No='03';Top='BACKSTAGE';Head='DER LETZTE HANDGRIFF';Body='Seitlich sitzend, den Ärmel richten – kurz vor dem Auftritt.';A='#B64A45';Mode=3;FX=.5;FY=.43}
)
foreach($it in $trip){$c=New-Canvas 488 600 '#111820' '#030608' 'Vertical';Cover $c.Graphics (Join-Path $GeneratedDir $it.Img) ([System.Drawing.Rectangle]::new(0,0,488,600)) $it.FX $it.FY
    $ac=C $it.A
    if($it.Mode -eq 1){$shade=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,370,488,230),[System.Drawing.Color]::FromArgb(0,5,12,18),[System.Drawing.Color]::FromArgb(242,5,12,18),[System.Drawing.Drawing2D.LinearGradientMode]::Vertical);$c.Graphics.FillRectangle($shade,0,350,488,250);$shade.Dispose();BrushBand $c.Graphics @([System.Drawing.Point]::new(24,29),[System.Drawing.Point]::new(200,18),[System.Drawing.Point]::new(209,60),[System.Drawing.Point]::new(28,70)) ([System.Drawing.Color]::FromArgb(230,$ac.R,$ac.G,$ac.B))}
    elseif($it.Mode -eq 2){BrushBand $c.Graphics @([System.Drawing.Point]::new(0,405),[System.Drawing.Point]::new(488,340),[System.Drawing.Point]::new(488,600),[System.Drawing.Point]::new(0,600)) ([System.Drawing.Color]::FromArgb(225,100,28,13));BrushBand $c.Graphics @([System.Drawing.Point]::new(290,18),[System.Drawing.Point]::new(488,18),[System.Drawing.Point]::new(488,76),[System.Drawing.Point]::new(268,63)) ([System.Drawing.Color]::FromArgb(235,$ac.R,$ac.G,$ac.B))}
    else{Fill $c.Graphics ([System.Drawing.Rectangle]::new(0,0,62,600)) ([System.Drawing.Color]::FromArgb(205,75,10,21));$shade=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(62,390,426,210),[System.Drawing.Color]::FromArgb(0,4,7,14),[System.Drawing.Color]::FromArgb(238,4,7,14),[System.Drawing.Drawing2D.LinearGradientMode]::Vertical);$c.Graphics.FillRectangle($shade,62,360,426,240);$shade.Dispose()}
    Text $c.Graphics $it.No ([System.Drawing.RectangleF]::new(24,18,70,62)) 48 ([System.Drawing.Color]::FromArgb(180,255,255,255)) 'Old English Text MT'
    Text $c.Graphics $it.Top ([System.Drawing.RectangleF]::new(28,417,420,28)) 16 $ac 'Bahnschrift SemiBold Condensed' 'Bold'
    Text $c.Graphics $it.Head ([System.Drawing.RectangleF]::new(27,449,432,55)) 31 $white 'Franklin Gothic Demi Cond' 'Bold'
    Text $c.Graphics $it.Body ([System.Drawing.RectangleF]::new(28,514,425,64)) 16 (C '#EEE8E0')
    SaveJpg $c.Bitmap (Join-Path $Root $it.Out);Close $c
}

# 04 — four-color stage carousel; source models remain the product evidence
$slides=@(
    @{Worn='product-01-1.jpg';Front='product-01-2.jpg';Out='04-01-carousel-navy-1464x600.jpg';A='#D8A85D';Tint='#123B55';Color='VINTAGE NAVY';Head='EIN TOAST AUF MITTERNACHT';Body='Ruhig im Ton. Stark im Detail.';Tag='COCKTAIL  ·  DINNER  ·  NIGHT OUT';Rot=-2},
    @{Worn='product-05-1.jpg';Front='product-05-2.jpg';Out='04-02-carousel-orange-1464x600.jpg';A='#FFB13B';Tint='#A8411F';Color='FESTIVE ORANGE';Head='SCHRITT FÜR SCHRITT INS LICHT';Body='Wärme, Farbe und Festivalenergie.';Tag='HALLOWEEN  ·  PARADE  ·  PARTY';Rot=2},
    @{Worn='product-03-1.jpg';Front='product-03-2.jpg';Out='04-03-carousel-black-1464x600.jpg';A='#B64A45';Tint='#3C285A';Color='GOTHIC BLACK';Head='BACKSTAGE. BEREIT. LOS.';Body='Dunkle Basis, leuchtende Rosen.';Tag='CONCERT  ·  CLUB  ·  MASQUERADE';Rot=-3},
    @{Worn='product-11-1.jpg';Scene='scene-theatre-turn.png';Front='product-11-2.jpg';Out='04-04-carousel-burgundy-1464x600.jpg';A='#E0B36A';Tint='#6D1B29';Color='ROYAL BURGUNDY';Head='VORHANG AUF FÜR BORDEAUX';Body='Festliche Tiefe mit Bühnengefühl.';Tag='HOLIDAY  ·  THEATRE  ·  DINNER';Rot=2}
)
$n=0
foreach($it in $slides){$n++;$c=New-Canvas 1464 600 '#07121B' '#24171D';Cover $c.Graphics (Join-Path $GeneratedDir 'carousel-stage.png') ([System.Drawing.Rectangle]::new(0,0,1464,600)) .5 .54
    Fill $c.Graphics ([System.Drawing.Rectangle]::new(0,0,1464,600)) (C $it.Tint 72)
    $left=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,760,600),[System.Drawing.Color]::FromArgb(242,4,12,20),[System.Drawing.Color]::FromArgb(20,4,12,20),[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal);$c.Graphics.FillRectangle($left,0,0,790,600);$left.Dispose()
    $ac=C $it.A;BrushBand $c.Graphics @([System.Drawing.Point]::new(55,68),[System.Drawing.Point]::new(425,47),[System.Drawing.Point]::new(438,88),[System.Drawing.Point]::new(61,108)) ([System.Drawing.Color]::FromArgb(230,$ac.R,$ac.G,$ac.B))
    Text $c.Graphics ("0"+$n+'  /  FOUR MOODS') ([System.Drawing.RectangleF]::new(74,63,338,38)) 18 $ink 'Bahnschrift SemiBold Condensed' 'Bold' 'Center' 'Center'
    Text $c.Graphics $it.Color ([System.Drawing.RectangleF]::new(66,130,495,42)) 23 $ac 'Bahnschrift SemiBold Condensed' 'Bold'
    Text $c.Graphics $it.Head ([System.Drawing.RectangleF]::new(63,184,535,135)) 48 $white 'Franklin Gothic Demi Cond' 'Bold'
    Text $c.Graphics $it.Body ([System.Drawing.RectangleF]::new(68,334,450,50)) 22 (C '#DDE2E4')
    Rule $c.Graphics 68 407 227 407 $ac 4;Tag $c.Graphics $it.Tag ([System.Drawing.Rectangle]::new(67,468,430,40)) ([System.Drawing.Color]::FromArgb(175,7,15,21)) $white
    if($it.Scene){Cover $c.Graphics (Join-Path $GeneratedDir $it.Scene) ([System.Drawing.Rectangle]::new(575,12,600,575)) .48 .46;$sp=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(150,$ac.R,$ac.G,$ac.B),2);$c.Graphics.DrawRectangle($sp,[System.Drawing.Rectangle]::new(575,12,600,575));$sp.Dispose()}else{Cutout $c.Graphics (Join-Path $SourceDir $it.Worn) ([System.Drawing.Rectangle]::new(575,12,600,575)) $it.Rot $true}
    $arch=[System.Drawing.Drawing2D.GraphicsPath]::new();$arch.AddArc(1147,60,260,260,180,180);$arch.AddLine(1407,190,1407,540);$arch.AddLine(1407,540,1147,540);$arch.AddLine(1147,540,1147,190);$arch.CloseFigure();$b=[System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(205,238,232,220));$c.Graphics.FillPath($b,$arch);$b.Dispose();$p=[System.Drawing.Pen]::new($ac,3);$c.Graphics.DrawPath($p,$arch);$p.Dispose();Cutout $c.Graphics (Join-Path $SourceDir $it.Front) ([System.Drawing.Rectangle]::new(1160,78,232,448)) 0 $false;Text $c.Graphics 'ORIGINAL-DESIGN' ([System.Drawing.RectangleF]::new(1160,539,232,27)) 13 $ac 'Bahnschrift SemiBold Condensed' 'Bold' 'Center';$arch.Dispose()
    SaveJpg $c.Bitmap (Join-Path $Root $it.Out);Close $c
}

# 05 — tactile, diagonal macro composition
$m=New-Canvas 1464 600 '#F0E3D1' '#1A2632'
$diag=[System.Drawing.Drawing2D.GraphicsPath]::new();$diagPts=[System.Drawing.Point[]]@([System.Drawing.Point]::new(0,0),[System.Drawing.Point]::new(905,0),[System.Drawing.Point]::new(700,600),[System.Drawing.Point]::new(0,600));$diag.AddPolygon($diagPts);$st=$m.Graphics.Save();$m.Graphics.SetClip($diag);Crop $m.Graphics $front ([System.Drawing.Rectangle]::new(0,0,910,600)) ([System.Drawing.Rectangle]::new(250,90,1040,900));$m.Graphics.Restore($st);$diag.Dispose()
$shade=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,920,600),[System.Drawing.Color]::FromArgb(30,6,12,18),[System.Drawing.Color]::FromArgb(220,6,12,18),[System.Drawing.Drawing2D.LinearGradientMode]::Vertical);$m.Graphics.FillRectangle($shade,0,0,920,600);$shade.Dispose()
Text $m.Graphics 'Nahaufnahme' ([System.Drawing.RectangleF]::new(56,43,330,64)) 48 $orange 'Brush Script MT' 'Italic'
Text $m.Graphics "STRUKTUR, DIE`nMAN SEHEN KANN" ([System.Drawing.RectangleF]::new(55,110,570,112)) 46 $white 'Franklin Gothic Demi Cond' 'Bold'
Text $m.Graphics 'Motivkonturen, gerippte Oberfläche und klare Kanten im direkten Blick.' ([System.Drawing.RectangleF]::new(58,432,500,70)) 20 $white
Rule $m.Graphics 58 400 235 400 $orange 5
$mac=@(
    @{D=[System.Drawing.Rectangle]::new(850,48,245,245);S=[System.Drawing.Rectangle]::new(420,40,680,680);T='REVERS & KANTE'},
    @{D=[System.Drawing.Rectangle]::new(1160,34,250,250);S=[System.Drawing.Rectangle]::new(170,390,700,700);T='MOTIVKONTUREN'},
    @{D=[System.Drawing.Rectangle]::new(970,325,285,245);S=[System.Drawing.Rectangle]::new(480,430,760,640);T='RÜCKEN & ÄRMEL';P=$back}
)
foreach($x in $mac){$p2=if($x.P){$x.P}else{$front};$r=$x.D;$gp=[System.Drawing.Drawing2D.GraphicsPath]::new();$gp.AddEllipse($r);$st=$m.Graphics.Save();$m.Graphics.SetClip($gp);Crop $m.Graphics $p2 $r $x.S;$m.Graphics.Restore($st);$pen=[System.Drawing.Pen]::new($gold,5);$m.Graphics.DrawEllipse($pen,$r);$pen.Dispose();$gp.Dispose();Tag $m.Graphics $x.T ([System.Drawing.Rectangle]::new($r.X+22,$r.Bottom-21,$r.Width-44,34)) $ink $white}
SaveJpg $m.Bitmap (Join-Path $Root '05-material-craft-1464x600.jpg');Close $m

# 06 — three different evidence treatments, not one repeated card
$c=New-Canvas 488 600 '#071420' '#231117' 'Vertical';Cover $c.Graphics (Join-Path $SourceDir 'product-01-1.jpg') ([System.Drawing.Rectangle]::new(0,0,488,600)) .5 .42;BrushBand $c.Graphics @([System.Drawing.Point]::new(0,380),[System.Drawing.Point]::new(488,335),[System.Drawing.Point]::new(488,600),[System.Drawing.Point]::new(0,600)) ([System.Drawing.Color]::FromArgb(225,4,13,21));Text $c.Graphics 'In Bewegung' ([System.Drawing.RectangleF]::new(26,391,360,58)) 43 $orange 'Brush Script MT' 'Italic';Text $c.Graphics 'GETRAGEN' ([System.Drawing.RectangleF]::new(27,456,430,45)) 31 $white 'Franklin Gothic Demi Cond' 'Bold';Text $c.Graphics 'Silhouette und Länge im kompletten Styling.' ([System.Drawing.RectangleF]::new(28,515,420,55)) 17 (C '#E8E3DD');SaveJpg $c.Bitmap (Join-Path $Root '06-01-worn-look-488x600.jpg');Close $c

$c=New-Canvas 488 600 '#F6EDDF' '#DCE3DE' 'Vertical';Text $c.Graphics 'VORDERSEITE' ([System.Drawing.RectangleF]::new(24,25,260,36)) 22 $burg 'Franklin Gothic Demi Cond' 'Bold';Text $c.Graphics '01' ([System.Drawing.RectangleF]::new(370,10,95,70)) 50 (C '#D1A35E') 'Old English Text MT';Cutout $c.Graphics $front ([System.Drawing.Rectangle]::new(55,74,382,455)) 1 $true;Rule $c.Graphics 34 180 122 180 $orange 2;Text $c.Graphics 'REVERS' ([System.Drawing.RectangleF]::new(28,144,112,30)) 14 $ink 'Bahnschrift SemiBold Condensed' 'Bold';Rule $c.Graphics 362 330 454 330 $orange 2;Text $c.Graphics 'MOTIVFLÄCHE' ([System.Drawing.RectangleF]::new(348,295,120,30)) 14 $ink 'Bahnschrift SemiBold Condensed' 'Bold' 'Far';Fill $c.Graphics ([System.Drawing.Rectangle]::new(0,546,488,54)) $ink;Text $c.Graphics 'KLARE KONSTRUKTION  ·  MARKANTE FRONT' ([System.Drawing.RectangleF]::new(22,548,444,48)) 16 $white 'Bahnschrift SemiBold Condensed' 'Bold' 'Center' 'Center';SaveJpg $c.Bitmap (Join-Path $Root '06-02-front-view-488x600.jpg');Close $c

$c=New-Canvas 488 600 '#091623' '#233342' 'Vertical';Text $c.Graphics 'Rückansicht' ([System.Drawing.RectangleF]::new(28,18,300,58)) 42 $gold 'Old English Text MT';Cutout $c.Graphics $back ([System.Drawing.Rectangle]::new(42,76,405,444)) -1 $true;$rd=[System.Drawing.Rectangle]::new(310,335,150,150);$gp=[System.Drawing.Drawing2D.GraphicsPath]::new();$gp.AddEllipse($rd);$st=$c.Graphics.Save();$c.Graphics.SetClip($gp);Crop $c.Graphics $back $rd ([System.Drawing.Rectangle]::new(650,430,650,650));$c.Graphics.Restore($st);$pp=[System.Drawing.Pen]::new($orange,4);$c.Graphics.DrawEllipse($pp,$rd);$pp.Dispose();$gp.Dispose();Fill $c.Graphics ([System.Drawing.Rectangle]::new(0,533,488,67)) ([System.Drawing.Color]::FromArgb(230,91,20,28));Text $c.Graphics 'RUHIGE RÜCKENFLÄCHE`nAKZENTUIERTE ÄRMEL' ([System.Drawing.RectangleF]::new(22,540,444,54)) 17 $white 'Franklin Gothic Demi Cond' 'Bold' 'Center' 'Center';SaveJpg $c.Bitmap (Join-Path $Root '06-03-back-view-488x600.jpg');Close $c

# 07 — light blueprint size guide using source chart data
$m=New-Canvas 1464 600 '#F8F1E5' '#DDE5E2'
Text $m.Graphics 'Passform' ([System.Drawing.RectangleF]::new(48,23,320,70)) 56 $burg 'Old English Text MT';Text $m.Graphics 'KLEIDUNGSMASSE  ·  CM / INCH' ([System.Drawing.RectangleF]::new(55,93,360,30)) 17 $ink 'Bahnschrift SemiBold Condensed' 'Bold';Rule $m.Graphics 56 131 357 131 $orange 5
Cutout $m.Graphics $front ([System.Drawing.Rectangle]::new(45,138,380,400)) 0 $true
$pen=[System.Drawing.Pen]::new($burg,2);$pen.DashStyle=[System.Drawing.Drawing2D.DashStyle]::Dash;$m.Graphics.DrawLine($pen,130,252,356,252);$m.Graphics.DrawLine($pen,111,194,111,452);$m.Graphics.DrawLine($pen,320,173,320,466);$pen.Dispose();Text $m.Graphics 'BRUST' ([System.Drawing.RectangleF]::new(210,220,90,28)) 13 $burg 'Bahnschrift SemiBold Condensed' 'Bold' 'Center';Text $m.Graphics 'LÄNGE' ([System.Drawing.RectangleF]::new(43,294,72,28)) 13 $burg 'Bahnschrift SemiBold Condensed' 'Bold';Text $m.Graphics 'ÄRMEL' ([System.Drawing.RectangleF]::new(321,300,70,28)) 13 $burg 'Bahnschrift SemiBold Condensed' 'Bold'

$rows=@(
    @('S','108 / 42,52','45 / 17,72','63,5 / 25,00','74 / 29,13'),@('M','113 / 44,49','46,5 / 18,31','64,2 / 25,28','75 / 29,53'),@('L','118 / 46,46','48 / 18,90','64,9 / 25,55','76 / 29,92'),@('XL','123 / 48,43','49,5 / 19,49','65,6 / 25,83','77 / 30,31'),@('XXL','128 / 50,39','51 / 20,08','66,3 / 26,10','78 / 30,71'),@('3XL','133 / 52,36','52,5 / 20,67','67 / 26,38','79 / 31,10'),@('4XL','138 / 54,33','54 / 21,26','67,7 / 26,65','80 / 31,50')
)
$headers=@('GRÖSSE','BRUST','SCHULTER','ÄRMEL','LÄNGE');$widths=@(90,185,185,185,185);$tx=486;$ty=108;$hh=44;$rh=54
$x=$tx;for($i=0;$i-lt 5;$i++){$r=[System.Drawing.Rectangle]::new($x,$ty,$widths[$i],$hh);Fill $m.Graphics $r $ink;Text $m.Graphics $headers[$i] ([System.Drawing.RectangleF]::new($r.X,$r.Y,$r.Width,$r.Height)) 14 $white 'Bahnschrift SemiBold Condensed' 'Bold' 'Center' 'Center';$x+=$widths[$i]}
for($j=0;$j-lt $rows.Count;$j++){$x=$tx;for($i=0;$i-lt 5;$i++){$r=[System.Drawing.Rectangle]::new($x,$ty+$hh+$j*$rh,$widths[$i],$rh);$bg=if($j%2-eq 0){C '#F8F1E7'}else{C '#E6DDD1'};Fill $m.Graphics $r $bg;$p=[System.Drawing.Pen]::new((C '#B9A98F'),1);$m.Graphics.DrawRectangle($p,$r);$p.Dispose();Text $m.Graphics $rows[$j][$i] ([System.Drawing.RectangleF]::new($r.X+3,$r.Y,$r.Width-6,$r.Height)) 13 $ink 'Bahnschrift' $(if($i-eq 0){'Bold'}else{'Regular'}) 'Center' 'Center';$x+=$widths[$i]}}
Tag $m.Graphics 'WERTE JEWEILS: CM / INCH' ([System.Drawing.Rectangle]::new(486,540,300,36)) $orange $white;Text $m.Graphics 'Tipp: Mit einem gut sitzenden Blazer vergleichen. Die Tabelle zeigt Kleidungsmaße; geringe Messabweichungen sind möglich.' ([System.Drawing.RectangleF]::new(812,535,500,52)) 14 (C '#39434B')
SaveJpg $m.Bitmap (Join-Path $Root '07-size-guide-de-1464x600.jpg');Close $m

# review composites
function Triptych([string[]]$Files,[string]$Out){$b=[System.Drawing.Bitmap]::new(1464,600);$g=[System.Drawing.Graphics]::FromImage($b);$g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic;try{for($i=0;$i-lt 3;$i++){$im=[System.Drawing.Image]::FromFile((Join-Path $Root $Files[$i]));try{$g.DrawImage($im,[System.Drawing.Rectangle]::new($i*488,0,488,600))}finally{$im.Dispose()}};SaveJpg $b $Out 92}finally{$g.Dispose();$b.Dispose()}}
Triptych @('03-01-cocktail-toast-488x600.jpg','03-02-festival-walk-488x600.jpg','03-03-backstage-cuff-488x600.jpg') (Join-Path $PreviewDir '03-triptych-preview-1464x600.jpg')
Triptych @('06-01-worn-look-488x600.jpg','06-02-front-view-488x600.jpg','06-03-back-view-488x600.jpg') (Join-Path $PreviewDir '06-triptych-preview-1464x600.jpg')

$overview=@('01-hero-1464x600.jpg','02-design-details-1464x600.jpg','_preview\03-triptych-preview-1464x600.jpg','04-01-carousel-navy-1464x600.jpg','04-02-carousel-orange-1464x600.jpg','04-03-carousel-black-1464x600.jpg','04-04-carousel-burgundy-1464x600.jpg','05-material-craft-1464x600.jpg','_preview\06-triptych-preview-1464x600.jpg','07-size-guide-de-1464x600.jpg')
$ob=[System.Drawing.Bitmap]::new(732,3000);$og=[System.Drawing.Graphics]::FromImage($ob);$og.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic;$og.Clear((C '#111418'));try{for($i=0;$i-lt $overview.Count;$i++){$im=[System.Drawing.Image]::FromFile((Join-Path $Root $overview[$i]));try{$og.DrawImage($im,[System.Drawing.Rectangle]::new(0,$i*300,732,300))}finally{$im.Dispose()}};SaveJpg $ob (Join-Path $PreviewDir '00-full-overview.jpg') 90}finally{$og.Dispose();$ob.Dispose()}

# Mobile assets — Amazon Premium A+ 600 x 450

# M01 hero
$m=New-Canvas 600 450 '#07131E' '#29141C';Cover $m.Graphics (Join-Path $GeneratedDir 'hero-base.png') ([System.Drawing.Rectangle]::new(0,0,600,450)) .64 .48
$mo=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,470,450),[System.Drawing.Color]::FromArgb(245,5,16,27),[System.Drawing.Color]::FromArgb(0,5,16,27),[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal);$m.Graphics.FillRectangle($mo,0,0,470,450);$mo.Dispose()
BrushBand $m.Graphics @([System.Drawing.Point]::new(24,25),[System.Drawing.Point]::new(245,17),[System.Drawing.Point]::new(252,48),[System.Drawing.Point]::new(28,55)) ([System.Drawing.Color]::FromArgb(235,$orange.R,$orange.G,$orange.B));Text $m.Graphics 'DIE NACHT GEHÖRT DIR' ([System.Drawing.RectangleF]::new(32,25,208,28)) 13 $white 'Brush Script MT' 'Italic' 'Center' 'Center'
Text $m.Graphics "HALLOWEEN / FESTIVAL /`nPARTYNACHT" ([System.Drawing.RectangleF]::new(28,76,330,72)) 22 $orange 'Showcard Gothic';Text $m.Graphics "FÜR AUFTRITTE`nMIT CHARAKTER" ([System.Drawing.RectangleF]::new(28,164,290,68)) 29 $white 'Franklin Gothic Demi Cond' 'Bold';Rule $m.Graphics 30 252 126 252 $orange 4;Text $m.Graphics 'Markante Motive. Klare Blazer-Silhouette.' ([System.Drawing.RectangleF]::new(30,269,265,48)) 15 (C '#E2E5E6')
SkullIcon $m.Graphics 32 360 30 $white;PumpkinIcon $m.Graphics 77 361 29 $orange;SparkIcon $m.Graphics 120 364 21 $gold;SkullIcon $m.Graphics 157 360 30 $orange
SaveJpg $m.Bitmap (Join-Path $MobileDir '01-hero-mobile-600x450.jpg');Close $m

# M02 bright detail gallery
$m=New-Canvas 600 450 '#F8F1E7' '#D9E2E2';Cover $m.Graphics (Join-Path $GeneratedDir 'detail-gallery.png') ([System.Drawing.Rectangle]::new(0,0,600,450)) .5 .5;Fill $m.Graphics ([System.Drawing.Rectangle]::new(0,0,255,450)) ([System.Drawing.Color]::FromArgb(225,249,243,234));Text $m.Graphics 'Designstudie' ([System.Drawing.RectangleF]::new(25,24,215,44)) 34 $burg 'Old English Text MT';Text $m.Graphics "DETAILS, DIE`nDEN LOOK PRÄGEN" ([System.Drawing.RectangleF]::new(26,76,218,66)) 25 $ink 'Franklin Gothic Demi Cond' 'Bold';Rule $m.Graphics 28 154 145 154 $orange 4;Text $m.Graphics 'Revers, Motivführung und klare Konturen im direkten Blick.' ([System.Drawing.RectangleF]::new(28,170,190,76)) 15 (C '#33404A');Cutout $m.Graphics $front ([System.Drawing.Rectangle]::new(220,16,285,418)) -2 $true
$d1=[System.Drawing.Rectangle]::new(478,38,106,106);$gp=[System.Drawing.Drawing2D.GraphicsPath]::new();$gp.AddEllipse($d1);$st=$m.Graphics.Save();$m.Graphics.SetClip($gp);Crop $m.Graphics $front $d1 ([System.Drawing.Rectangle]::new(430,60,720,650));$m.Graphics.Restore($st);$p=[System.Drawing.Pen]::new($orange,4);$m.Graphics.DrawEllipse($p,$d1);$p.Dispose();$gp.Dispose();Tag $m.Graphics 'REVERS' ([System.Drawing.Rectangle]::new(491,127,80,25)) $ink $white
$d2=[System.Drawing.Rectangle]::new(466,272,116,116);$gp=[System.Drawing.Drawing2D.GraphicsPath]::new();$gp.AddEllipse($d2);$st=$m.Graphics.Save();$m.Graphics.SetClip($gp);Crop $m.Graphics $front $d2 ([System.Drawing.Rectangle]::new(700,390,700,760));$m.Graphics.Restore($st);$p=[System.Drawing.Pen]::new($orange,4);$m.Graphics.DrawEllipse($p,$d2);$p.Dispose();$gp.Dispose();Tag $m.Graphics 'MOTIV' ([System.Drawing.Rectangle]::new(482,374,84,25)) $ink $white
SaveJpg $m.Bitmap (Join-Path $MobileDir '02-design-details-mobile-600x450.jpg');Close $m

# M03 three actions stacked vertically for mobile readability
$m=New-Canvas 600 450 '#08111A' '#26161A' 'Vertical';$mobileScenes=@(
    @{Img='scene-cocktail-toast.png';Y=0;FX=.52;FY=.44;No='01';Title='COCKTAIL  ·  AUF DIE NACHT';A='#F0B44F'},
    @{Img='scene-festival-walk.png';Y=150;FX=.47;FY=.46;No='02';Title='FESTIVAL  ·  FARBE IN BEWEGUNG';A='#F36C2B'},
    @{Img='scene-backstage-cuff.png';Y=300;FX=.50;FY=.42;No='03';Title='BACKSTAGE  ·  LETZTER HANDGRIFF';A='#B64A45'}
);foreach($s in $mobileScenes){Cover $m.Graphics (Join-Path $GeneratedDir $s.Img) ([System.Drawing.Rectangle]::new(0,$s.Y,600,150)) $s.FX $s.FY;$fade=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,$s.Y,390,150),[System.Drawing.Color]::FromArgb(225,4,12,18),[System.Drawing.Color]::FromArgb(0,4,12,18),[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal);$m.Graphics.FillRectangle($fade,0,$s.Y,410,150);$fade.Dispose();$ac=C $s.A;Text $m.Graphics $s.No ([System.Drawing.RectangleF]::new(20,$s.Y+18,44,40)) 30 $ac 'Old English Text MT';Text $m.Graphics $s.Title ([System.Drawing.RectangleF]::new(68,$s.Y+30,315,44)) 20 $white 'Franklin Gothic Demi Cond' 'Bold';Rule $m.Graphics 68 ($s.Y+82) 170 ($s.Y+82) $ac 3};Rule $m.Graphics 0 150 600 150 $white 2;Rule $m.Graphics 0 300 600 300 $white 2
SaveJpg $m.Bitmap (Join-Path $MobileDir '03-scenes-triptych-mobile-600x450.jpg');Close $m

# M04 four carousel panels
$slideNo=0
foreach($it in $slides){$slideNo++;$c=New-Canvas 600 450 '#07121B' '#24171D';Cover $c.Graphics (Join-Path $GeneratedDir 'carousel-stage.png') ([System.Drawing.Rectangle]::new(0,0,600,450)) .5 .55;Fill $c.Graphics ([System.Drawing.Rectangle]::new(0,0,600,450)) (C $it.Tint 70);$left=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,390,450),[System.Drawing.Color]::FromArgb(245,4,12,20),[System.Drawing.Color]::FromArgb(0,4,12,20),[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal);$c.Graphics.FillRectangle($left,0,0,410,450);$left.Dispose();$ac=C $it.A;BrushBand $c.Graphics @([System.Drawing.Point]::new(22,28),[System.Drawing.Point]::new(210,18),[System.Drawing.Point]::new(217,50),[System.Drawing.Point]::new(26,58)) ([System.Drawing.Color]::FromArgb(230,$ac.R,$ac.G,$ac.B));Text $c.Graphics (("0"+$slideNo)+' / FOUR MOODS') ([System.Drawing.RectangleF]::new(31,27,177,30)) 13 $ink 'Bahnschrift SemiBold Condensed' 'Bold' 'Center' 'Center';Text $c.Graphics $it.Color ([System.Drawing.RectangleF]::new(28,80,260,28)) 17 $ac 'Bahnschrift SemiBold Condensed' 'Bold';Text $c.Graphics $it.Head ([System.Drawing.RectangleF]::new(27,121,310,98)) 30 $white 'Franklin Gothic Demi Cond' 'Bold';Text $c.Graphics $it.Body ([System.Drawing.RectangleF]::new(29,235,255,44)) 16 (C '#E0E3E5');Rule $c.Graphics 29 299 145 299 $ac 3;Text $c.Graphics $it.Tag ([System.Drawing.RectangleF]::new(29,322,285,42)) 12 $white 'Bahnschrift SemiBold Condensed' 'Bold'
    if($it.Scene){Cover $c.Graphics (Join-Path $GeneratedDir $it.Scene) ([System.Drawing.Rectangle]::new(315,10,275,430)) .48 .46;Cutout $c.Graphics (Join-Path $SourceDir $it.Front) ([System.Drawing.Rectangle]::new(470,250,108,176)) 0 $false}else{Cutout $c.Graphics (Join-Path $SourceDir $it.Worn) ([System.Drawing.Rectangle]::new(300,18,292,416)) $it.Rot $true}
    SaveJpg $c.Bitmap (Join-Path $MobileDir ($it.Out -replace '1464x600','mobile-600x450'));Close $c
}

# M05 tactile macro
$m=New-Canvas 600 450 '#101923' '#35231F';Crop $m.Graphics $front ([System.Drawing.Rectangle]::new(0,0,600,450)) ([System.Drawing.Rectangle]::new(260,80,1040,900));$shade=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,600,450),[System.Drawing.Color]::FromArgb(228,4,12,18),[System.Drawing.Color]::FromArgb(30,4,12,18),[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal);$m.Graphics.FillRectangle($shade,0,0,600,450);$shade.Dispose();Text $m.Graphics 'Nahaufnahme' ([System.Drawing.RectangleF]::new(26,24,230,44)) 33 $orange 'Brush Script MT' 'Italic';Text $m.Graphics "STRUKTUR, DIE`nMAN SEHEN KANN" ([System.Drawing.RectangleF]::new(27,75,300,80)) 31 $white 'Franklin Gothic Demi Cond' 'Bold';Text $m.Graphics 'Motivkonturen und gerippte Oberfläche im direkten Blick.' ([System.Drawing.RectangleF]::new(28,176,250,66)) 15 $white
$mc1=[System.Drawing.Rectangle]::new(356,36,158,158);$gp=[System.Drawing.Drawing2D.GraphicsPath]::new();$gp.AddEllipse($mc1);$st=$m.Graphics.Save();$m.Graphics.SetClip($gp);Crop $m.Graphics $front $mc1 ([System.Drawing.Rectangle]::new(420,40,680,680));$m.Graphics.Restore($st);$p=[System.Drawing.Pen]::new($gold,4);$m.Graphics.DrawEllipse($p,$mc1);$p.Dispose();$gp.Dispose();$mc2=[System.Drawing.Rectangle]::new(396,244,172,172);$gp=[System.Drawing.Drawing2D.GraphicsPath]::new();$gp.AddEllipse($mc2);$st=$m.Graphics.Save();$m.Graphics.SetClip($gp);Crop $m.Graphics $back $mc2 ([System.Drawing.Rectangle]::new(480,430,760,640));$m.Graphics.Restore($st);$p=[System.Drawing.Pen]::new($orange,4);$m.Graphics.DrawEllipse($p,$mc2);$p.Dispose();$gp.Dispose();Tag $m.Graphics 'REVERS & RÜCKEN' ([System.Drawing.Rectangle]::new(375,205,170,30)) $ink $white
SaveJpg $m.Bitmap (Join-Path $MobileDir '05-material-craft-mobile-600x450.jpg');Close $m

# M06 fit evidence stacked vertically
$m=New-Canvas 600 450 '#071420' '#F4EBDD' 'Vertical';Cover $m.Graphics (Join-Path $SourceDir 'product-01-1.jpg') ([System.Drawing.Rectangle]::new(0,0,600,150)) .5 .40;$fade=[System.Drawing.Drawing2D.LinearGradientBrush]::new([System.Drawing.Rectangle]::new(0,0,360,150),[System.Drawing.Color]::FromArgb(225,4,12,18),[System.Drawing.Color]::FromArgb(0,4,12,18),[System.Drawing.Drawing2D.LinearGradientMode]::Horizontal);$m.Graphics.FillRectangle($fade,0,0,380,150);$fade.Dispose();Text $m.Graphics '01  GETRAGEN' ([System.Drawing.RectangleF]::new(22,38,235,36)) 23 $white 'Franklin Gothic Demi Cond' 'Bold';Text $m.Graphics 'Silhouette im Styling' ([System.Drawing.RectangleF]::new(23,82,210,28)) 14 $orange
Fill $m.Graphics ([System.Drawing.Rectangle]::new(0,150,600,150)) (C '#F5EBDD');Text $m.Graphics '02  VORDERSEITE' ([System.Drawing.RectangleF]::new(22,188,230,36)) 23 $burg 'Franklin Gothic Demi Cond' 'Bold';Text $m.Graphics 'Revers · Knöpfe · Motive' ([System.Drawing.RectangleF]::new(23,232,240,28)) 14 $ink;Cutout $m.Graphics $front ([System.Drawing.Rectangle]::new(330,157,235,136)) 0 $false
Fill $m.Graphics ([System.Drawing.Rectangle]::new(0,300,600,150)) (C '#0A1926');Text $m.Graphics '03  RÜCKSEITE' ([System.Drawing.RectangleF]::new(22,337,230,36)) 23 $gold 'Franklin Gothic Demi Cond' 'Bold';Text $m.Graphics 'Ruhige Fläche · Ärmelakzente' ([System.Drawing.RectangleF]::new(23,381,250,28)) 14 $white;Cutout $m.Graphics $back ([System.Drawing.Rectangle]::new(330,307,235,136)) 0 $false;Rule $m.Graphics 0 150 600 150 $orange 2;Rule $m.Graphics 0 300 600 300 $orange 2
SaveJpg $m.Bitmap (Join-Path $MobileDir '06-fit-triptych-mobile-600x450.jpg');Close $m

# M07 readable mobile size table
$m=New-Canvas 600 450 '#F8F1E5' '#E0E7E3';Text $m.Graphics 'Passform' ([System.Drawing.RectangleF]::new(22,11,185,43)) 34 $burg 'Old English Text MT';Text $m.Graphics 'KLEIDUNGSMASSE  ·  CM / INCH' ([System.Drawing.RectangleF]::new(216,21,286,24)) 14 $ink 'Bahnschrift SemiBold Condensed' 'Bold';SkullIcon $m.Graphics 540 13 30 $orange
$mh=@('GRÖSSE','BRUST','SCHULTER','ÄRMEL','LÄNGE');$mw=@(62,124,124,124,124);$mx=21;$my=66;$mhh=34;$mrh=45;$x=$mx;for($i=0;$i-lt 5;$i++){$r=[System.Drawing.Rectangle]::new($x,$my,$mw[$i],$mhh);Fill $m.Graphics $r $ink;Text $m.Graphics $mh[$i] ([System.Drawing.RectangleF]::new($r.X,$r.Y,$r.Width,$r.Height)) 10 $white 'Bahnschrift SemiBold Condensed' 'Bold' 'Center' 'Center';$x+=$mw[$i]};for($j=0;$j-lt $rows.Count;$j++){$x=$mx;for($i=0;$i-lt 5;$i++){$r=[System.Drawing.Rectangle]::new($x,$my+$mhh+$j*$mrh,$mw[$i],$mrh);$bg=if($j%2-eq 0){C '#FBF5EC'}else{C '#E8DED1'};Fill $m.Graphics $r $bg;$p=[System.Drawing.Pen]::new((C '#B9A98F'),1);$m.Graphics.DrawRectangle($p,$r);$p.Dispose();Text $m.Graphics $rows[$j][$i] ([System.Drawing.RectangleF]::new($r.X+2,$r.Y,$r.Width-4,$r.Height)) 9.5 $ink 'Bahnschrift' $(if($i-eq 0){'Bold'}else{'Regular'}) 'Center' 'Center';$x+=$mw[$i]}};Text $m.Graphics 'Mit einem gut sitzenden Blazer vergleichen · geringe Messabweichungen möglich.' ([System.Drawing.RectangleF]::new(24,420,550,22)) 11 (C '#39434B') 'Bahnschrift' 'Regular' 'Center'
SaveJpg $m.Bitmap (Join-Path $MobileDir '07-size-guide-mobile-600x450.jpg');Close $m

# Mobile contact sheet
$mobileFiles=@('01-hero-mobile-600x450.jpg','02-design-details-mobile-600x450.jpg','03-scenes-triptych-mobile-600x450.jpg','04-01-carousel-navy-mobile-600x450.jpg','04-02-carousel-orange-mobile-600x450.jpg','04-03-carousel-black-mobile-600x450.jpg','04-04-carousel-burgundy-mobile-600x450.jpg','05-material-craft-mobile-600x450.jpg','06-fit-triptych-mobile-600x450.jpg','07-size-guide-mobile-600x450.jpg')
$mob=[System.Drawing.Bitmap]::new(300,2250);$mg=[System.Drawing.Graphics]::FromImage($mob);$mg.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic;$mg.Clear((C '#111418'));try{for($i=0;$i-lt $mobileFiles.Count;$i++){$im=[System.Drawing.Image]::FromFile((Join-Path $MobileDir $mobileFiles[$i]));try{$mg.DrawImage($im,[System.Drawing.Rectangle]::new(0,$i*225,300,225))}finally{$im.Dispose()}};SaveJpg $mob (Join-Path $PreviewDir '00-mobile-overview.jpg') 91}finally{$mg.Dispose();$mob.Dispose()}

foreach($kv in $Cutouts.GetEnumerator()){$kv.Value.Dispose()}
Write-Output 'V2 complete: 14 desktop assets + 10 mobile assets + 4 review previews.'
