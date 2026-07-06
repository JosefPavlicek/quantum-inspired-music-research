Cíl: z hustého „4 akordy na takt“ udělat přirozenější doprovod.

A) Redukce změn akordů (humanize)

penalizovat změny na slabých dobách (2, 4)

když je melodie stejná přes 2–4 doby, často držet akord déle

změny preferovat na dobách 1 a 3

když se v taktu mění akordy, ale rozdíl je „kosmetický“, držet

B) Kadence na konci

poslední takt (nebo poslední 1–2 doby) preferovat C (tonika) nebo G7 (dominanta)
(u tebe v C dur: Cmaj7 / C, nebo G7)

C) Volitelné „jazz“ rozšíření a zjednodušení

někdy nahradit 7th → triáda (kvintakord)

někdy přidat 6/9/11/13/sus jen když to sedí na soprán
Např. v C: když soprán je D, může to být Cadd9 / Cmaj9; když F → Csus4 (ale pozor na rozvázání).

D) Obraty (slash chords)

vybrat obrat tak, aby bas šel co nejplynuleji (minimalizace skoků)

např. D/F# místo čistého D, pokud to plynuleji navazuje

3) Hotový skript: musicxml_optimizer.py

Vstup: tvůj generovaný MusicXML (ten se 2 party: P1 melody + harmony, P2 chord tones)

Výstup: nový MusicXML, kde:

P1 melodie zůstane beze změny

harmony značky se zredukují (ne vždy 4 na takt)

P2 chord tones se přepočítají podle nové harmonie a nového držení (delší noty)

Poznámka: Skript počítá s tím, že tvůj exporter má <divisions>1</divisions> a beat = quarter. Pokud máš jiný divisions, skript si ho načte a přizpůsobí se.