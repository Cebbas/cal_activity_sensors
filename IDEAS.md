# Cal Activity Sensors – idélista / checklista

## Grundfunktioner
- [x] Utbruten till en egen, fristående integration från Cal Combiner (egen
  domän `cal_activity`, egen panel, eget websocket-API, egen storage – ingen
  kod delas mellan de två integrationerna)
- [x] Bygg fristående sensorer (`binary_sensor`) från filtrerade
  kalenderaktiviteter, oavsett vilken integration källkalendern kommer från.
  En entitet per konfiguration - state är `on`/`off`, all annan info
  (händelsetitel, nästa datum, dagar kvar, ...) är attribut (färre entiteter
  att hålla reda på än det gamla `binary_sensor`/`sensor`-paret, och inga
  föräldralösa entity-registry-poster kvar från plattformsbyten - städas
  automatiskt av `__init__.py` vid varje setup)
- [x] Filter: fält att matcha mot (titel/beskrivning/plats/alla),
  inkludera/uteslut-ord, regex-läge, skiftlägeskänslighet
- [x] Valbart läge för state – på/av just nu, ELLER på om ett matchande
  event inträffar någon gång samma dag
- [x] Attribut: `current_event`/`active_until`, `next_event`, `next_start`,
  `next_end`, `matches_today`, `location`, `failed_sources`
- [x] Hanterbara via både sidopanelen och vanliga Inställningar → Enheter &
  tjänster
- [x] Aktivitetslogg per sensor ("Senaste händelser") i panelen: skapad,
  ändringar, källa svarar inte/svarar igen

## Utseende
- [x] Egen ikon per sensor
- [x] Egen bild (uppladdad via HA:s inbyggda bilduppladdning) per sensor

## Robusthet
- [x] Repair-issue (istället för bara `failed_sources`-attributet) så en
  källa som slutat svara syns i Inställningar → Repairs – delad
  `FailureStreakTracker` (`activity.py`) används av både
  `ActivitySensorCoordinator` och `LifeEventCoordinator` (kalenderkälla),
  `homeassistant.helpers.issue_registry`, döljs automatiskt igen när alla
  källor svarar.
- [x] Retry/backoff om en källa svarar ostabilt istället för att direkt
  räknas som "failed" för hela pollningsintervallet – samma
  `FailureStreakTracker` väntar med att höja issuen tills `FAILURE_THRESHOLD`
  (2) pollningar i rad misslyckats. `failed_sources`-attributet är
  opåverkat (visar fortfarande rådata per pollning).
- [x] Automatiserade tester (unit-tester för filterlogiken och
  coordinator-uppdatering) – pytest-svit i `tests/` (byggd på
  `pytest-homeassistant-custom-component`), körs i CI via
  `.github/workflows/validate.yml`. Täcker filter (`_matches_filter`),
  `fetch_matching_events`, `event_is_active`/`event_is_upcoming`/`event_is_today`,
  `life_event.py`s datummatte (`next_span`, `_end_inclusive`, `_safe_date`,
  inkl. skottdag och årsskiftesspann) och båda coordinatorernas
  uppdateringslogik (manuellt/kalenderdatum, retry/backoff), samt
  `binary_sensor.py`s `is_on`/attribut-logik för alla tre sensor-typerna
  (`tests/test_birthday.py` täcker `BirthdayBinarySensor` och
  migreringsfunktionen separat).

## Trevligt-att-ha (ej påbörjat)
- [ ] Fler sensor-typer, t.ex. "minuter kvar till nästa match" eller "antal
  matchande event denna vecka"
- [x] Egen "Födelsedag"-kind (`birthday`, `const.py`), utbruten ur
  Nedräkning/livshändelse: ett eget, fokuserat formulär (bara namn + datum -
  alltid återkommande, alltid fast datum, inga kalender-/flerdagsval).
  Återanvänder samma `LifeEventCoordinator`/datummatte som countdown (ingen
  duplicerad logik) via en tunn `BirthdayBinarySensor`-subklass i
  `binary_sensor.py` med samma `unique_id`-suffix som föräldraklassen, plus
  attributet `age` (alias för `years`). Avancerat, valfritt: koppla till en
  `person.*`-entitet (`person_entity`, bara synligt i Avancerat läge) -
  används som bildkälla om ingen egen bild är satt, och exponeras som
  attributet `person`. Befintliga countdown-entries vars namn innehåller
  "födelsedag"/"birthday" migreras automatiskt till `birthday`-kind vid
  uppstart (`_migrate_birthday_named_countdowns`, `__init__.py`) - samma
  entity_id/historik, bara kind och formulär byts. Panelens eget
  websocket-API (`ws_api.py`, separat från `config_flow.py` - det är det
  panelen faktiskt pratar med) och dess formulär
  (`www/cal-activity-panel.js`) är uppdaterade i samma svep: eget typval
  "Födelsedag" i skapa-kortet, egen ikon i list-/kortvy. Har sedan fått ett
  helt eget, minimalt fältformulär (`_buildBirthdayFieldsSection` - bara
  ikon, bild, datum, person; inga countdown-fält som datumkälla/slutdatum/
  återkommande/källkalendrar syns alls) istället för att återanvända
  Nedräkning-formuläret med en bortförklarande textrad. Panelen har även
  fått en översta flik-nivå (`_renderGroupTabs`) som delar upp allt i
  "Födelsedagar" och "Övrigt" (Aktivitet/Nedräkning), var med sin egen
  rad av entitets-flikar och eget skapa-kort under.
- [ ] Möjlighet att koppla en automation-mall direkt från panelen (förslag
  på trigger-YAML)
- [x] "Life event"-liknande sensorer / nedräkningssensor: ny sensor-"kind"
  `countdown` (`life_event.py`), state = `on`/`off`. Datumkälla är antingen
  ett fast datum (återkommande varje år som förval, räknar ålder/antal år -
  t.ex. födelsedagar, namnsdagar, jubileum) eller ett matchande kalenderevent
  (samma käll-/filtermekanism som aktivitetssensorn). `on` den dag
  datumet/eventet inträffar, med attribut `days_remaining`, `phase`
  ("upcoming"/"in_progress"/"passed") och `days_until_start`. Går att skapa
  och redigera både via sidopanelen och Inställningar → Enheter & tjänster.
  Stödjer även flerdagarsspann (t.ex. en resa): valfritt slutdatum vid fast
  datum, eller automatiskt via kalenderns egna start/slut vid kalenderlänkad
  källa - `on` är då sant hela perioden och sensorn får attribut
  `end_date`/`day_of_span`/`span_length`.
- [ ] Konfigurerbart pollningsintervall (idag hårdkodat till 5 min) via
  options flow eller panelen
- [x] Diagnostics-stöd (`diagnostics.py`) för att exportera felsökningsdata

## Kända begränsningar
- Pollar källkalendrarna var 5:e minut (hårdkodat) via
  `calendar.get_events` – ingen realtidspush
