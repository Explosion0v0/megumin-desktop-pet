<!DOCTYPE html>
<html lang="en">

  <head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>VOSK Models</title>

  <!-- Begin Jekyll SEO tag v2.8.0 -->
<meta name="generator" content="Jekyll v3.9.0" />
<meta property="og:title" content="VOSK Models" />
<meta property="og:locale" content="en_US" />
<meta name="description" content="Accurate speech recognition for Android, iOS, Raspberry Pi and servers with Python, Java, C#, Swift and Node." />
<meta property="og:description" content="Accurate speech recognition for Android, iOS, Raspberry Pi and servers with Python, Java, C#, Swift and Node." />
<link rel="canonical" href="https://alphacephei.com/vosk/models" />
<meta property="og:url" content="https://alphacephei.com/vosk/models" />
<meta property="og:site_name" content="VOSK Offline Speech Recognition API" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary" />
<meta property="twitter:title" content="VOSK Models" />
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebPage","description":"Accurate speech recognition for Android, iOS, Raspberry Pi and servers with Python, Java, C#, Swift and Node.","headline":"VOSK Models","url":"https://alphacephei.com/vosk/models"}</script>
<!-- End Jekyll SEO tag -->


  <!-- CSS -->
  <link rel="stylesheet" href="/css/bootstrap.min.css">
  <link rel="stylesheet" href="/css/style.css">

  <!--link rel="stylesheet" href="/vosk/assets/main.css"-->
  <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Raleway:400,400i,700">

  <!-- Favicon -->
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico">

  <!-- RSS -->
  <link type="application/atom+xml" rel="alternate" href="https://alphacephei.com/vosk/feed.xml" title="VOSK Offline Speech Recognition API" />

  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-V3NP4163XP"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());

    gtag('config', 'G-V3NP4163XP');
  </script>

</head>


  <body>

    <div class="container-fluid">

        <nav class="navbar navbar-expand-md navbar-light fixed-top bg-light" id="mainNav">
    <div class="container-fluid">
        <a class="navbar-brand" href="/vosk">
        <img alt="Logo" src="/img/logo.png">
    </a>
    <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbar-collapsed" aria-controls="navbar-collapsed" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbar-collapsed">
                 <ul class="navbar-nav ms-auto">
                     <li class="nav-item"><a class="nav-link" href="/en">Alpha Cephei</a></li>
                     <li class="nav-item"><a class="nav-link" href="https://github.com/alphacep/vosk-api">GitHub</a></li>
                     <li class="nav-item"><a class="nav-link" href="https://alphacephei.com/nsh/">Research</a></li>
                 </ul>
     </div>
    </div>
</nav>



        <div class="row m-4">
            <div class="col-xs-12 col-sm-2">
                 <ul>
    
         <li><a href="/vosk/">Introduction</a></li>
    
         <li><a href="install">Installation</a></li>
    
         <li><a href="integrations">Integrations</a></li>
    
         <li><a href="accuracy">Accuracy</a></li>
    
         <li><a href="adaptation">Adaptation</a></li>
    
         <li><a href="models">Models</a></li>
    
         <li><a href="android">Android Demo</a></li>
    
         <li><a href="unity">Unity</a></li>
    
         <li><a href="server">Vosk Server</a></li>
    
         <li><a href="lm">LM adaptation</a></li>
    
         <li><a href="faq">FAQ</a></li>
    
</ul>

            </div>
            <div class="col-xs-12 col-sm-10">
                  <main>
                      <h1 id="models">Models</h1>

<p>We have two types of models - big and small, small models are ideal for
some limited task on mobile applications. They can run on smartphones,
Raspberry Pi’s. They are also recommended for desktop applications. Small
model typically is around 50Mb in size and requires about 300Mb of memory
in runtime. Big models are for the high-accuracy transcription on the
server. Big models require up to 16Gb in memory since they apply advanced
AI algorithms. Ideally you run them on some high-end servers like i7 or
latest AMD Ryzen. On AWS you can take a look on c5a machines and similar
machines in other clouds.</p>

<p>Most small model allow dynamic vocabulary reconfiguration. Big models are
static the vocabulary can not be modified in runtime.</p>

<h2 id="model-list">Model list</h2>

<p>This is the list of models compatible with Vosk-API.</p>

<p>To add a new model here create an issue on Github.</p>

<table class="table table-bordered">
  <thead>
    <tr>
      <th>Model</th>
      <th>Size</th>
      <th>Word error rate/Speed</th>
      <th>Notes</th>
      <th>License</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>English</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip">vosk-model-small-en-us-0.15</a></td>
      <td>40M</td>
      <td>9.85 (librispeech test-clean) 10.38 (tedlium)</td>
      <td>Lightweight wideband model for Android and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip">vosk-model-en-us-0.22</a></td>
      <td>1.8G</td>
      <td>5.69 (librispeech test-clean) 6.05 (tedlium) 29.78(callcenter)</td>
      <td>Accurate generic US English model</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip">vosk-model-en-us-0.22-lgraph</a></td>
      <td>128M</td>
      <td>7.82 (librispeech) 8.20 (tedlium)</td>
      <td>Big US English model with dynamic graph</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip">vosk-model-en-us-0.42-gigaspeech</a></td>
      <td>2.3G</td>
      <td>5.64 (librispeech test-clean) 6.24 (tedlium) 30.17 (callcenter)</td>
      <td>Accurate generic US English model trained by Kaldi on <a href="http://kaldi-asr.org/models/m14">Gigaspeech</a>. Mostly for podcasts, not for telephony</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>English Other</strong></td>
      <td> </td>
      <td><strong>Older Models</strong></td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-daanzu-20200905.zip">vosk-model-en-us-daanzu-20200905</a></td>
      <td>1.0G</td>
      <td>7.08 (librispeech test-clean)  8.25 (tedlium)</td>
      <td>Wideband model for dictation from <a href="https://github.com/daanzu/kaldi-active-grammar">Kaldi-active-grammar</a> project</td>
      <td>AGPL</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-daanzu-20200905-lgraph.zip">vosk-model-en-us-daanzu-20200905-lgraph</a></td>
      <td>129M</td>
      <td>8.20 (librispeech test-clean) 9.28 (tedlium)</td>
      <td>Wideband model for dictation from <a href="https://github.com/daanzu/kaldi-active-grammar">Kaldi-active-grammar</a> project with configurable graph</td>
      <td>AGPL</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-librispeech-0.2.zip">vosk-model-en-us-librispeech-0.2</a></td>
      <td>845M</td>
      <td>TBD</td>
      <td>Repackaged Librispeech model from <a href="https://kaldi-asr.org/models/m13">Kaldi</a>, not very accurate</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-en-us-zamia-0.5.zip">vosk-model-small-en-us-zamia-0.5</a></td>
      <td>49M</td>
      <td>11.55 (librispeech test-clean) 12.64 (tedlium)</td>
      <td>Repackaged Zamia model f_250, mainly for research</td>
      <td>LGPL-3.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-aspire-0.2.zip">vosk-model-en-us-aspire-0.2</a></td>
      <td>1.4G</td>
      <td>13.64 (librispeech test-clean) 12.89 (tedlium) 33.82(callcenter)</td>
      <td>Kaldi original ASPIRE model, not very accurate</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-us-0.21.zip">vosk-model-en-us-0.21</a></td>
      <td>1.6G</td>
      <td>5.43 (librispeech test-clean) 6.42 (tedlium) 40.63(callcenter)</td>
      <td>Wideband model previous generation</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Indian English</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip">vosk-model-en-in-0.5</a></td>
      <td>1G</td>
      <td>36.12 (NPTEL Pure)</td>
      <td>Generic Indian English model for telecom and broadcast</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip">vosk-model-small-en-in-0.4</a></td>
      <td>36M</td>
      <td>49.05 (NPTEL Pure)</td>
      <td>Lightweight Indian English model for mobile applications</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Chinese</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip">vosk-model-small-cn-0.22</a></td>
      <td>42M</td>
      <td>23.54 (SpeechIO-02) 38.29 (SpeechIO-06) 17.15 (THCHS)</td>
      <td>Lightweight model for Android and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip">vosk-model-cn-0.22</a></td>
      <td>1.3G</td>
      <td>13.98 (SpeechIO-02) 27.30 (SpeechIO-06) 7.43 (THCHS)</td>
      <td>Big generic Chinese model for server processing</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Chinese Other</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-cn-kaldi-multicn-0.15.zip">vosk-model-cn-kaldi-multicn-0.15</a></td>
      <td>1.5G</td>
      <td>17.44 (SpeechIO-02) 9.56 (THCHS)</td>
      <td>Original Wideband Kaldi multi-cn model from <a href="https://kaldi-asr.org/models/m11">Kaldi</a> with Vosk LM</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Russian</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip">vosk-model-ru-0.42</a></td>
      <td>1.8G</td>
      <td>4.5 (our audiobooks) 11.1 (open_stt audiobooks) 19.5 (open_stt youtube) 36.0 (openstt calls) 4.4 (golos crowd) 17.9 (sova devices)</td>
      <td>Big mixed band Russian model for servers</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip">vosk-model-small-ru-0.22</a></td>
      <td>45M</td>
      <td>22.71 (openstt audiobooks) 31.97 (openstt youtube) 29.89 (sova devices) 11.79 (golos crowd)</td>
      <td>Lightweight wideband model for Android/iOS and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Russian Other</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ru-0.22.zip">vosk-model-ru-0.22</a></td>
      <td>1.5G</td>
      <td>5.74 (our audiobooks) 13.35 (open_stt audiobooks) 20.73 (open_stt youtube) 37.38 (openstt calls) 8.65 (golos crowd) 19.71 (sova devices)</td>
      <td>Big mixed band Russian model for servers</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ru-0.10.zip">vosk-model-ru-0.10</a></td>
      <td>2.5G</td>
      <td>5.71 (our audiobooks) 16.26 (open_stt audiobooks) 26.20 (public_youtube_700_val open_stt) 40.15 (asr_calls_2_val open_stt)</td>
      <td>Big narrowband Russian model for servers</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>French</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip">vosk-model-small-fr-0.22</a></td>
      <td>41M</td>
      <td>23.95 (cv test) 19.30 (mtedx) 27.25 (podcast)</td>
      <td>Lightweight wideband model for Android/iOS and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip">vosk-model-fr-0.22</a></td>
      <td>1.4G</td>
      <td>14.72 (cv test) 11.64 (mls) 13.10 (mtedx) 21.61 (podcast) 13.22 (voxpopuli)</td>
      <td>Big accurate model for servers</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>French Other</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-fr-pguyot-0.3.zip">vosk-model-small-fr-pguyot-0.3</a></td>
      <td>39M</td>
      <td>37.04 (cv test) 28.72 (mtedx) 37.46 (podcast)</td>
      <td>Lightweight wideband model for Android and RPi trained by <a href="https://github.com/pguyot/zamia-speech/releases">Paul Guyot</a></td>
      <td>CC-BY-NC-SA 4.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-fr-0.6-linto-2.2.0.zip">vosk-model-fr-0.6-linto-2.2.0</a></td>
      <td>1.5G</td>
      <td>16.19 (cv test) 16.44 (mtedx) 23.77 (podcast) 0.4xRT</td>
      <td>Model from <a href="https://doc.linto.ai/#/services/linstt">LINTO</a> project</td>
      <td>AGPL</td>
    </tr>
    <tr>
      <td><strong>German</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip">vosk-model-de-0.21</a></td>
      <td>1.9G</td>
      <td>9.83 (Tuda-de test), 24.00 (podcast) 12.82 (cv-test) 12.42 (mls) 33.26 (mtedx)</td>
      <td>Big German model for telephony and server</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-de-tuda-0.6-900k.zip">vosk-model-de-tuda-0.6-900k</a></td>
      <td>4.4G</td>
      <td>9.48 (Tuda-de test), 25.82 (podcast) 4.97 (cv-test) 11.01 (mls) 35.20 (mtedx)</td>
      <td>Latest big wideband model from <a href="https://github.com/uhh-lt/kaldi-tuda-de">Tuda-DE</a> project</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-de-zamia-0.3.zip">vosk-model-small-de-zamia-0.3</a></td>
      <td>49M</td>
      <td>14.81 (Tuda-de test, 37.46 (podcast)</td>
      <td>Zamia f_250 small model repackaged (not recommended)</td>
      <td>LGPL-3.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip">vosk-model-small-de-0.15</a></td>
      <td>45M</td>
      <td>13.75 (Tuda-de test), 30.67 (podcast)</td>
      <td>Lightweight wideband model for Android and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Spanish</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip">vosk-model-small-es-0.42</a></td>
      <td>39M</td>
      <td>16.02 (cv test) 16.72 (mtedx test) 11.21 (mls)</td>
      <td>Lightweight wideband model for Android and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip">vosk-model-es-0.42</a></td>
      <td>1.4G</td>
      <td>7.50 (cv test) 10.05 (mtedx test) 5.84 (mls)</td>
      <td>Big model for Spanish</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Portuguese/Brazilian Portuguese</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip">vosk-model-small-pt-0.3</a></td>
      <td>31M</td>
      <td>68.92 (coraa dev) 32.60 (cv test)</td>
      <td>Lightweight wideband model for Android and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-pt-fb-v0.1.1-20220516_2113.zip">vosk-model-pt-fb-v0.1.1-20220516_2113</a></td>
      <td>1.6G</td>
      <td>54.34 (coraa dev) 27.70 (cv test)</td>
      <td>Big model from <a href="https://gitlab.com/fb-resources/kaldi-br">FalaBrazil</a></td>
      <td>GPLv3.0</td>
    </tr>
    <tr>
      <td><strong>Greek</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-el-gr-0.7.zip">vosk-model-el-gr-0.7</a></td>
      <td>1.1G</td>
      <td>TBD</td>
      <td>Big narrowband Greek model for server processing, not extremely accurate though</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Turkish</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip">vosk-model-small-tr-0.3</a></td>
      <td>35M</td>
      <td>TBD</td>
      <td>Lightweight wideband model for Android and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Vietnamese</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip">vosk-model-small-vn-0.4</a></td>
      <td>32M</td>
      <td>15.70 (Vivos test)</td>
      <td>Lightweight Vietnamese model</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-vn-0.4.zip">vosk-model-vn-0.4</a></td>
      <td>78M</td>
      <td>15.70 (Vivos test)</td>
      <td>Bigger Vietnamese model for server</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Italian</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip">vosk-model-small-it-0.22</a></td>
      <td>48M</td>
      <td>16.88 (cv test) 25.87 (mls) 17.01 (mtedx)</td>
      <td>Lightweight model for Android and RPi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-it-0.22.zip">vosk-model-it-0.22</a></td>
      <td>1.2G</td>
      <td>8.10 (cv test) 15.68 (mls) 11.23 (mtedx)</td>
      <td>Big generic Italian model for servers</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Dutch</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-nl-0.22.zip">vosk-model-small-nl-0.22</a></td>
      <td>39M</td>
      <td>22.45 (cv test) 26.80 (tv) 25.84 (mls) 24.09 (voxpopuli)</td>
      <td>Lightweight model for Dutch</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Dutch Other</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-nl-spraakherkenning-0.6.zip">vosk-model-nl-spraakherkenning-0.6</a></td>
      <td>860M</td>
      <td>20.40 (cv test) 32.64 (tv) 17.73 (mls) 19.96 (voxpopuli)</td>
      <td>Medium Dutch model from <a href="https://github.com/opensource-spraakherkenning-nl/Kaldi_NL">Kaldi_NL</a></td>
      <td>CC-BY-NC-SA</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-nl-spraakherkenning-0.6-lgraph.zip">vosk-model-nl-spraakherkenning-0.6-lgraph</a></td>
      <td>100M</td>
      <td>22.82 (cv test) 34.01 (tv) 18.81 (mls) 21.01 (voxpopuli)</td>
      <td>Smaller model with dynamic graph</td>
      <td>CC-BY-NC-SA</td>
    </tr>
    <tr>
      <td><strong>Catalan</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-ca-0.4.zip">vosk-model-small-ca-0.4</a></td>
      <td>42M</td>
      <td>TBD</td>
      <td>Lightweight wideband model for Android and RPi for Catalan</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Arabic</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip">vosk-model-ar-mgb2-0.4</a></td>
      <td>318M</td>
      <td>16.40 (MGB-2 dev set)</td>
      <td>Repackaged Arabic model trained on MGB2 dataset from <a href="https://kaldi-asr.org/models/m9">Kaldi</a></td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ar-0.22-linto-1.1.0.zip">vosk-model-ar-0.22-linto-1.1.0</a></td>
      <td>1.3G</td>
      <td>52.87 (cv test) 28.50 (MBG-2 dev set) 1.0xRT</td>
      <td>Big model from <a href="https://doc.linto.ai/#/services/linstt">LINTO</a> project</td>
      <td>AGPL</td>
    </tr>
    <tr>
      <td><strong>Arabic Tunisian</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-ar-tn-0.1-linto.zip">vosk-model-small-ar-tn-0.1-linto</a></td>
      <td>158M</td>
      <td>16.06 (TARIC set)</td>
      <td>Small Arabic Tunisian model from <a href="https://huggingface.co/linagora/linto-asr-ar-tn-0.1">Linagora</a></td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ar-tn-0.1-linto.zip">vosk-model-ar-tn-0.1-linto</a></td>
      <td>517M</td>
      <td>16.06 (TARIC set)</td>
      <td>Arabic Tunisian model from <a href="https://huggingface.co/linagora/linto-asr-ar-tn-0.1">Linagora</a></td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Farsi</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-fa-0.42.zip">vosk-model-fa-0.42</a></td>
      <td>1.6G</td>
      <td>16.7 (CV17) 11.1 (Fleurs)</td>
      <td>Model with large vocabulary, not yet accurate but better than before (Persian)</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-fa-0.42.zip">vosk-model-small-fa-0.42</a></td>
      <td>53M</td>
      <td>23.4 (CV17) 14.0 (Fleurs)</td>
      <td>Small model for desktop and mobile applications (Persian)</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Farsi Other</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-fa-0.5.zip">vosk-model-fa-0.5</a></td>
      <td>1G</td>
      <td>29.7 (CV17) 25.1 (Fleurs)</td>
      <td>Model with large vocabulary, not yet accurate but better than before (Persian)</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip">vosk-model-small-fa-0.5</a></td>
      <td>60M</td>
      <td>31.2 (CV17) 26.2 (Fleurs)</td>
      <td>Bigger small model for desktop applications (Persian)</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Filipino</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-tl-ph-generic-0.6.zip">vosk-model-tl-ph-generic-0.6</a></td>
      <td>320M</td>
      <td>18.87 (FLEURS-dev) 18.61 (FLEURS-test) 97.9 (BABEL-dev) MATERIAL-dev (41.31)</td>
      <td>Medium wideband model for Filipino (Tagalog) by <a href="https://github.com/feddybear/flipside_ph">feddybear</a></td>
      <td>CC-BY-NC-SA 4.0</td>
    </tr>
    <tr>
      <td><strong>Ukrainian</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-uk-v3-nano.zip">vosk-model-small-uk-v3-nano</a></td>
      <td>73M</td>
      <td>TBD</td>
      <td>Nano model from <a href="https://github.com/egorsmkv/speech-recognition-uk">Speech Recognition for Ukrainian</a></td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-uk-v3-small.zip">vosk-model-small-uk-v3-small</a></td>
      <td>133M</td>
      <td>TBD</td>
      <td>Small model from <a href="https://github.com/egorsmkv/speech-recognition-uk">Speech Recognition for Ukrainian</a></td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-uk-v3.zip">vosk-model-uk-v3</a></td>
      <td>343M</td>
      <td>TBD</td>
      <td>Bigger model from <a href="https://github.com/egorsmkv/speech-recognition-uk">Speech Recognition for Ukrainian</a></td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-uk-v3-lgraph.zip">vosk-model-uk-v3-lgraph</a></td>
      <td>325M</td>
      <td>TBD</td>
      <td>Big dynamic model from <a href="https://github.com/egorsmkv/speech-recognition-uk">Speech Recognition for Ukrainian</a></td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Kazakh</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-kz-0.42.zip">vosk-model-small-kz-0.42</a></td>
      <td>58M</td>
      <td>21.10 (fleurs) 30.0 (CV17) 9.7 (KSC) 24.86 (KSC Other)</td>
      <td>Small mobile model for Kazakh</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-kz-0.42.zip">vosk-model-kz-0.42</a></td>
      <td>1.3G</td>
      <td>13.09 (fleurs) 12.50 (CV17) 4.49 (KSC) 18.51 (KSC Other)</td>
      <td>Bigger model for Kazakh</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Swedish</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-sv-rhasspy-0.15.zip">vosk-model-small-sv-rhasspy-0.15</a></td>
      <td>289M</td>
      <td>TBD</td>
      <td>Repackaged model from <a href="https://github.com/rhasspy/sv_kaldi-rhasspy">Rhasspy project</a></td>
      <td>MIT</td>
    </tr>
    <tr>
      <td><strong>Japanese</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip">vosk-model-small-ja-0.22</a></td>
      <td>48M</td>
      <td>9.52(csj CER) 17.07(ted10k CER)</td>
      <td>Lightweight wideband model for Japanese</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ja-0.22.zip">vosk-model-ja-0.22</a></td>
      <td>1Gb</td>
      <td>8.40(csj CER) 13.91(ted10k CER)</td>
      <td>Big model for Japanese</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Esperanto</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-eo-0.42.zip">vosk-model-small-eo-0.42</a></td>
      <td>42M</td>
      <td>7.24 (CV Test)</td>
      <td>Lightweight model for Esperanto</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Hindi</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip">vosk-model-small-hi-0.22</a></td>
      <td>42M</td>
      <td>20.89 (IITM Challenge) 24.72 (MUCS Challenge)</td>
      <td>Lightweight model for Hindi</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-hi-0.22.zip">vosk-model-hi-0.22</a></td>
      <td>1.5Gb</td>
      <td>14.85 (CV Test) 14.83 (IITM Challenge) 13.11 (MUCS Challenge)</td>
      <td>Big accurate model for servers</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Czech</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-cs-0.4-rhasspy.zip">vosk-model-small-cs-0.4-rhasspy</a></td>
      <td>44M</td>
      <td>21.29 (CV Test)</td>
      <td>Lightweight model for Czech from Rhasspy project</td>
      <td>MIT</td>
    </tr>
    <tr>
      <td><strong>Polish</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip">vosk-model-small-pl-0.22</a></td>
      <td>50M</td>
      <td>18.36 (CV Test) 16.88 (MLS Test) 11.55 (Voxpopuli Test)</td>
      <td>Lightweight model for Polish</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Uzbek</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-uz-0.22.zip">vosk-model-small-uz-0.22</a></td>
      <td>49M</td>
      <td>13.54 (CV Test) 12.92 (IS2AI USC test)</td>
      <td>Lightweight model for Uzbek</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Korean</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip">vosk-model-small-ko-0.22</a></td>
      <td>82M</td>
      <td>28.1 (Zeroth Test)</td>
      <td>Lightweight model for Korean</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Breton</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-br-0.8.zip">vosk-model-br-0.8</a></td>
      <td>70M</td>
      <td>36.4 (MCV11 Test)</td>
      <td>Breton model from <a href="https://github.com/gweltou/vosk-br">vosk-br</a> project</td>
      <td>MIT license</td>
    </tr>
    <tr>
      <td><strong>Gujarati</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-gu-0.42.zip">vosk-model-gu-0.42</a></td>
      <td>700M</td>
      <td>16.45 (MS Test)</td>
      <td>Big Gujarati model</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-gu-0.42.zip">vosk-model-small-gu-0.42</a></td>
      <td>100M</td>
      <td>20.49 (MS Test)</td>
      <td>Lightweight model for Gujarati</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Tajik</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-tg-0.22.zip">vosk-model-tg-0.22</a></td>
      <td>327M</td>
      <td>41.1 (Fleurs test)</td>
      <td>Big Tajik model</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-tg-0.22.zip">vosk-model-small-tg-0.22</a></td>
      <td>50M</td>
      <td>38.4 (Fleurs test)</td>
      <td>Lightweight model for Tajik</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Telugu</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-te-0.42.zip">vosk-model-small-te-0.42</a></td>
      <td>58M</td>
      <td>87.9 (Fleurs test)</td>
      <td>Lightweight model for Telugu</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Kyrgyz</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-ky-0.42.zip">vosk-model-small-ky-0.42</a></td>
      <td>49M</td>
      <td>18.95 (Fleurs) 16.96 (CV17)</td>
      <td>Small mobile model for Kyrgyz</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ky-0.42.zip">vosk-model-ky-0.42</a></td>
      <td>1.1G</td>
      <td>13.45 (Fleurs) 8.75 (CV17)</td>
      <td>Bigger model for Kyrgyz</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Georgian</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-small-ka-0.42.zip">vosk-model-small-ka-0.42</a></td>
      <td>45M</td>
      <td>18.0 (Fleurs) 14.2 (CV17)</td>
      <td>Small mobile model for Georgian</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-ka-0.42.zip">vosk-model-ka-0.42</a></td>
      <td>700M</td>
      <td>12.7 (Fleurs) 5.2 (CV17)</td>
      <td>Bigger model for Georgian</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Speaker identification model</strong></td>
      <td> </td>
      <td> </td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip">vosk-model-spk-0.4</a></td>
      <td>13M</td>
      <td>TBD</td>
      <td>Model for speaker identification, should work for all languages</td>
      <td>Apache 2.0</td>
    </tr>
  </tbody>
</table>

<h2 id="punctuation-models">Punctuation models</h2>

<p>For punctuation and case restoration we recommend the  models trained with <a href="https://github.com/benob/recasepunc">https://github.com/benob/recasepunc</a></p>

<table class="table table-bordered">
  <thead>
    <tr>
      <th>Model</th>
      <th>Size</th>
      <th>License</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>English</strong></td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-recasepunc-en-0.22.zip">vosk-recasepunc-en-0.22</a></td>
      <td>1.6G</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>Russian</strong></td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-recasepunc-ru-0.22.zip">vosk-recasepunc-ru-0.22</a></td>
      <td>1.6G</td>
      <td>Apache 2.0</td>
    </tr>
    <tr>
      <td><strong>German</strong></td>
      <td> </td>
      <td> </td>
    </tr>
    <tr>
      <td><a href="https://alphacephei.com/vosk/models/vosk-recasepunc-de-0.21.zip">vosk-recasepunc-de-0.21</a></td>
      <td>1.1G</td>
      <td>Apache 2.0</td>
    </tr>
  </tbody>
</table>

<h2 id="other-models">Other models</h2>

<p>Other places where you can check for models which might be compatible:</p>

<ul>
  <li><a href="https://kaldi-asr.org/models.html">https://kaldi-asr.org/models.html</a> - variety of models from Kaldi - librispeech, aspire, chinese models</li>
  <li><a href="https://github.com/daanzu/kaldi-active-grammar/blob/master/docs/models.md">https://github.com/daanzu/kaldi-active-grammar/blob/master/docs/models.md</a> - Big dictation models for English</li>
  <li><a href="https://github.com/uhh-lt/vosk-model-tuda-de">https://github.com/uhh-lt/vosk-model-tuda-de</a> - German models</li>
  <li><a href="https://github.com/german-asr/kaldi-german">https://github.com/german-asr/kaldi-german</a> - Another German project</li>
  <li><a href="https://zamia-speech.org/asr/">https://zamia-speech.org/asr/</a> - German and English model from Zamia</li>
  <li><a href="https://github.com/pguyot/zamia-speech/releases">https://github.com/pguyot/zamia-speech/releases</a> - French models for Zamia</li>
  <li><a href="https://github.com/opensource-spraakherkenning-nl/Kaldi_NL">https://github.com/opensource-spraakherkenning-nl/Kaldi_NL</a> - Dutch model</li>
  <li><a href="https://montreal-forced-aligner.readthedocs.io/en/latest/pretrained_models.html">https://montreal-forced-aligner.readthedocs.io/en/latest/pretrained_models.html</a> (GMM models, not compatible but might be still useful)</li>
  <li><a href="https://github.com/goodatlas/zeroth">https://github.com/goodatlas/zeroth</a> - Korean Kaldi (just a recipe and data to train)</li>
  <li><a href="https://github.com/undertheseanlp/automatic_speech_recognition">https://github.com/undertheseanlp/automatic_speech_recognition</a> - Vietnamese Kaldi project</li>
  <li><a href="https://doc.linto.ai/#/services/linstt">https://doc.linto.ai/#/services/linstt</a> - LINTO project by <a href="https://linagora.com">Linagora</a> with French, English and Arabic models</li>
  <li><a href="https://community.rhasspy.org/">https://community.rhasspy.org/</a> - Rhasspy (some Kaldi models for Czech, probably even more)</li>
  <li><a href="https://github.com/feddybear/flipside_ph">https://github.com/feddybear/flipside_ph</a> - Filipino model project by Federico Ang</li>
  <li><a href="https://github.com/alumae/kiirkirjutaja">https://github.com/alumae/kiirkirjutaja</a> - Estonian Speech Recognition project with Vosk models</li>
  <li><a href="https://github.com/falabrasil/kaldi-br">https://github.com/falabrasil/kaldi-br</a> - Portuguese models from FalaBrasil project</li>
  <li><a href="https://github.com/egorsmkv/speech-recognition-uk">https://github.com/egorsmkv/speech-recognition-uk</a> - Ukrainian ASR project with Vosk models</li>
  <li><a href="https://github.com/Appen/UHV-OTS-Speech">https://github.com/Appen/UHV-OTS-Speech</a> - repository from Appen for Scalable Data Annotation Pipeline for High-Quality Large Speech Datasets Development</li>
  <li><a href="https://github.com/vistec-AI/commonvoice-th">https://github.com/vistec-AI/commonvoice-th</a> - Thai models trained on CommonVoice</li>
  <li><a href="https://github.com/gweltou/vosk-br">https://github.com/gweltou/vosk-br</a> - Vosk for Breton</li>
</ul>

<h2 id="training-your-own-model">Training your own model</h2>

<p>You can train your model with Kaldi toolkit. The training is pretty
standard - you need tdnn nnet3 model with i-vectors. You can check Vosk recipe for details:</p>

<p><a href="https://github.com/alphacep/vosk-api/tree/master/training">https://github.com/alphacep/vosk-api/tree/master/training</a></p>

<ul>
  <li>For smaller mobile models watch the number of parameters</li>
  <li>Train the model without pitch. It might be helpful for small amount of data, but for large database it doesn’t give the advantage
but complicates the processing and increases response time.</li>
  <li>Train ivector of dim 40 instead of standard 100 to save memory of mobile models.</li>
  <li>Many Kaldi recipes are overcomplicated and do many unnecessary steps</li>
  <li>PLEASE NOTE THAT THE SIMPLE GMM MODEL YOU TRAIN WITH <strong>“KALDI FOR DUMMIES”</strong> TUTORIAL <strong>DOES NOT WORK</strong> WITH VOSK. YOU NEED TO RUN VOSK RECIPE FROM START TO END, INCLUDING <strong>CHAIN MODEL TRAINING</strong>. You also need CUDA GPU to train. If you do not have a GPU, try to run Kaldi on Google Colab.</li>
</ul>

<h2 id="model-structure">Model structure</h2>

<p>Once you trained the model arrange the files according to the following layout (see en-us-aspire for details):</p>

<ul>
  <li><code class="language-plaintext highlighter-rouge">am/final.mdl</code> - acoustic model</li>
  <li><code class="language-plaintext highlighter-rouge">am/global_cmvn.stats</code> - required for online-cmvn models, if present enables online cmvn on features.</li>
  <li><code class="language-plaintext highlighter-rouge">conf/mfcc.conf</code> - mfcc config file. Make sure you take mfcc_hires.conf version if you are using hires model (most external ones)</li>
  <li><code class="language-plaintext highlighter-rouge">conf/model.conf</code> - provide default decoding beams and silence phones. you have to create this file yourself, it is not present in kaldi model</li>
  <li><code class="language-plaintext highlighter-rouge">conf/pitch.conf</code> - optional file to create feature pipeline with pitch features. Might be missing if model doesn’t use pitch</li>
  <li><code class="language-plaintext highlighter-rouge">ivector/final.dubm</code> - take ivector files from ivector extractor (optional folder if the model is trained with ivectors)</li>
  <li><code class="language-plaintext highlighter-rouge">ivector/final.ie</code></li>
  <li><code class="language-plaintext highlighter-rouge">ivector/final.mat</code></li>
  <li><code class="language-plaintext highlighter-rouge">ivector/splice.conf</code></li>
  <li><code class="language-plaintext highlighter-rouge">ivector/global_cmvn.stats</code></li>
  <li><code class="language-plaintext highlighter-rouge">ivector/online_cmvn.conf</code></li>
  <li><code class="language-plaintext highlighter-rouge">graph/phones/word_boundary.int</code> - from the graph</li>
  <li><code class="language-plaintext highlighter-rouge">graph/HCLG.fst</code> - this is the decoding graph, if you are not using lookahead</li>
  <li><code class="language-plaintext highlighter-rouge">graph/HCLr.fst</code> - use Gr.fst and HCLr.fst instead of one big HCLG.fst if you want to run rescoring</li>
  <li><code class="language-plaintext highlighter-rouge">graph/Gr.fst</code></li>
  <li><code class="language-plaintext highlighter-rouge">graph/phones.txt</code> - from the graph</li>
  <li><code class="language-plaintext highlighter-rouge">graph/words.txt</code> - from the graph</li>
  <li><code class="language-plaintext highlighter-rouge">rescore/G.carpa</code> - carpa rescoring is optional but helpful in big models. Usually located inside data/lang_test_rescore</li>
  <li><code class="language-plaintext highlighter-rouge">rescore/G.fst</code> - also optional if you want to use rescoring, also used for interpolation with RNNLM</li>
  <li><code class="language-plaintext highlighter-rouge">rnnlm/feat_embedding.final.mat</code> - RNNLM embedding for rescoring. Optional if you have it.</li>
  <li><code class="language-plaintext highlighter-rouge">rnnlm/special_symbol_opts.conf</code> - RNNLM model options</li>
  <li><code class="language-plaintext highlighter-rouge">rnnlm/final.raw</code> - RNNLM model</li>
  <li><code class="language-plaintext highlighter-rouge">rnnlm/word_feats.txt</code> - RNNLM model word feats</li>
</ul>

                   </main>
             </div>
        </div>

        <div class="row-fluid">
            <div class="col">
                <footer>
</footer>

            </div>
        </div>
    </div>
  </body>

  <script defer src="/lib/jquery-1.12.4.min.js"></script>
  <script defer src="/lib/bootstrap.min.js"></script>

</html>
