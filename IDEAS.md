# Cal Activity Sensors – idélista / checklista

## Grundfunktioner
- [x] Utbruten till en egen, fristående integration från Cal Combiner (egen
  domän `cal_activity`, egen panel, eget websocket-API, egen storage – ingen
  kod delas mellan de två integrationerna)
- [x] Bygg fristående sensorer (`binary_sensor`/`sensor`) från filtrerade
  kalenderaktiviteter, oavsett vilken integration källkalendern kommer från
- [x] Filter: fält att matcha mot (titel/beskrivning/plats/alla),
  inkludera/uteslut-ord, regex-läge, skiftlägeskänslighet
- [x] `binary_sensor`: valbart läge – på/av just nu, ELLER på om ett
  matchande event inträffar någon gång samma dag
- [x] `sensor`: state = aktuellt/nästa matchande event + attribut (antal
  idag, plats, start/slut)
- [x] Hanterbara via både sidopanelen och vanliga Inställningar → Enheter &
  tjänster
- [x] Aktivitetslogg per sensor ("Senaste händelser") i panelen: skapad,
  ändringar, källa svarar inte/svarar igen

## Utseende
- [x] Egen ikon per sensor
- [x] Egen bild (uppladdad via HA:s inbyggda bilduppladdning) per sensor

## Robusthet
- [ ] Repair-issue (istället för bara `failed_sources`-attributet) så en
  källa som slutat svara syns i Inställningar → Repairs
- [ ] Retry/backoff om en källa svarar ostabilt istället för att direkt
  räknas som "failed" för hela pollningsintervallet
- [ ] Automatiserade tester (unit-tester för filterlogiken och
  coordinator-uppdatering) – idag finns ingen testsvit

## Trevligt-att-ha (ej påbörjat)
- [ ] Fler sensor-typer, t.ex. "minuter kvar till nästa match" eller "antal
  matchande event denna vecka"
- [ ] Möjlighet att koppla en automation-mall direkt från panelen (förslag
  på trigger-YAML)
- [x] "Life event"-liknande sensorer / nedräkningssensor: ny sensor-"kind"
  `countdown` (`life_event.py`) med state = antal hela dagar kvar. Datumkälla
  är antingen ett fast datum (återkommande varje år som förval, räknar
  ålder/antal år - t.ex. födelsedagar, namnsdagar, jubileum) eller ett
  matchande kalenderevent (samma käll-/filtermekanism som aktivitetssensorn).
  `binary_sensor` är "på" den dag datumet/eventet inträffar. Går att skapa
  och redigera både via sidopanelen och Inställningar → Enheter & tjänster.
- [ ] Konfigurerbart pollningsintervall (idag hårdkodat till 5 min) via
  options flow eller panelen
- [x] Diagnostics-stöd (`diagnostics.py`) för att exportera felsökningsdata

## Kända begränsningar
- Pollar källkalendrarna var 5:e minut (hårdkodat) via
  `calendar.get_events` – ingen realtidspush
