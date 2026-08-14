# Cal Activity Sensors – idélista / checklista

## Grundfunktioner
- [x] Utbruten till en egen, fristående integration från Cal Combiner (egen
  domän `cal_activity`, egen panel, eget websocket-API, egen storage – ingen
  kod delas mellan de två integrationerna)
- [x] Bygg fristående sensorer (`sensor`) från filtrerade kalenderaktiviteter,
  oavsett vilken integration källkalendern kommer från. En entitet per
  konfiguration - inget separat `binary_sensor` längre, på/av-informationen
  är istället `active`-attributet på sensorn (färre entiteter att hålla
  reda på, och inga föräldralösa entity-registry-poster kvar från att
  kryssa i/ur en sensor-typ)
- [x] Filter: fält att matcha mot (titel/beskrivning/plats/alla),
  inkludera/uteslut-ord, regex-läge, skiftlägeskänslighet
- [x] Valbart läge för `active`-attributet – på/av just nu, ELLER på om ett
  matchande event inträffar någon gång samma dag
- [x] `sensor`: state = aktuellt/nästa matchande event + attribut (`active`,
  `active_until`, antal idag, plats, start/slut)
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
  `active`-attributet är sant den dag datumet/eventet inträffar, plus `phase`
  ("upcoming"/"in_progress"/"passed") och `days_until_start`. Går att skapa
  och redigera både via sidopanelen och Inställningar → Enheter & tjänster.
  Stödjer även flerdagarsspann (t.ex. en resa): valfritt slutdatum vid fast
  datum, eller automatiskt via kalenderns egna start/slut vid kalenderlänkad
  källa - `active` är då sant hela perioden och sensorn får attribut
  `end_date`/`day_of_span`/`span_length`.
- [ ] Konfigurerbart pollningsintervall (idag hårdkodat till 5 min) via
  options flow eller panelen
- [x] Diagnostics-stöd (`diagnostics.py`) för att exportera felsökningsdata

## Kända begränsningar
- Pollar källkalendrarna var 5:e minut (hårdkodat) via
  `calendar.get_events` – ingen realtidspush
