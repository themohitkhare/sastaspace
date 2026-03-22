rule JS_In_Image
{
    meta:
        description = "Detects JavaScript fragments embedded in image files"
    strings:
        $script = "<script" ascii nocase
        $eval = "eval(" ascii nocase
        $document = "document." ascii nocase
    condition:
        any of them
}

rule VBScript_In_Image
{
    meta:
        description = "Detects VBScript tags embedded in image files"
    strings:
        $vbs = "<vbscript" ascii nocase
    condition:
        any of them
}

rule SVG_Event_Handlers
{
    meta:
        description = "Detects event handler attributes commonly used in SVG-based XSS"
    strings:
        $onload = "onload=" ascii nocase
        $onerror = "onerror=" ascii nocase
        $onmouseover = "onmouseover=" ascii nocase
        $onclick = "onclick=" ascii nocase
    condition:
        any of them
}

rule Polyglot_File
{
    meta:
        description = "Detects polyglot files that masquerade as images but contain executable headers"
    strings:
        $pdf = "%PDF" ascii
        $elf = { 7f 45 4c 46 }
        $mz = "MZ" ascii
        $php = "<?php" ascii nocase
    condition:
        $pdf at 0 or $elf at 0 or $mz at 0 or $php at 0
}
