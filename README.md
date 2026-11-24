# Übezimmer

Übe-App für Klavier und Gehörbildung. Läuft im Browser: am Mac in Chrome mit MIDI am Kawai CA901, auf iPhone und iPad für die Hörübungen.

Die Übungsdaten liegen nicht hier, sondern im privaten Repository `uebezimmer-daten`. Die App gleicht sie automatisch über die GitHub-API ab.

Notensatz fürs Blattlesen: [abcjs](https://github.com/paulrosen/abcjs) (MIT). QR-Code: qrcode-generator von Kazuhiko Arase (MIT).

Hanon-Noten Nr. 1–20: Mutopia Project (Mutopia-2015/07/23-2037, Steve Taylor und Javier Ruiz-Alma), CC BY-SA 4.0.

## Hörgang (Gehörtraining unterwegs)

Audio-Lektionen zum Gehen, als Podcast-Feed: `https://avmendel.github.io/uebezimmer/hoergang/feed.xml`
(Apple Podcasts → Mediathek → „Sendung per URL folgen“). Jede Lektion etwa 12 Minuten: hören, in der Pause innerlich antworten, dann die Lösung.

Erzeugt mit `tools/hoergang/gen.py` (Python, numpy, ffmpeg, `piper-tts`; Stimme `voice-en-us-lessac-medium` aus
https://github.com/rhasspy/piper/releases/tag/v0.0.2 nach `tools/hoergang/voices/` entpacken). Aufruf: `python3 gen.py <ausgabe> <von> <bis>`.
