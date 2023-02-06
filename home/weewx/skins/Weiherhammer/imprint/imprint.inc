#errorCatcher Echo
#encoding UTF-8
<div class="entry-content about-outer" itemprop="text">

    <!-- Impressum bereitgestellt von eRecht24 -->
    <div class="row"  style="padding-top:15px;">
        <div class="col-sm-12">
            <h1>Impressum</h1>

            <h2>Angaben gem&auml;&szlig; &sect; 5 TMG</h2>
            <p>Henry Ott<br />
            Kirchstr. 12<br />
            92729 Weiherhammer</p>

            <h2>Kontakt</h2>
            <p>Telefon: +49 (0) 9605 6694010<br />
            Telefax: +49 (0) 9605 6694064<br />
            E-Mail: postmaster@weiherhammer-wetter.de</p>

            <h2>Redaktionell verantwortlich</h2>
            <p>Henry Ott<br />
            Kirchstr. 12<br />
            92729 Weiherhammer</p>

            <p>Quelle: <a href="https://www.e-recht24.de">e-recht24.de</a></p>
        </div>
    </div>

    <!-- Allgemeine Hinweise des Betreibers-->
    <div class="row"  style="padding-top:15px;">
        <div class="col-sm-12">
            #set $file = "general/general_notes.inc"
            #if os.path.exists($file)
            <!-- Begin $file -->
            #include $file
            <!-- End $file -->
            #end if
        </div>
    </div>

</div>
