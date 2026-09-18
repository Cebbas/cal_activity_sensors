# Cal Activity Sensors – Home Assistant custom integration

Bygger fristående `binary_sensor`-entiteter från ett filtrerat urval av
kalenderaktivitet – t.ex. en `binary_sensor.zoo_besok` som är `on` när ett
Zoo-event pågår, perfekt att trigga automationer på. Kan även skapa
nedräknings-/livshändelsesensorer (t.ex. `on` på en födelsedag, eller under
hela en resa), med dagar kvar och nästa datum som attribut.

Detta var tidigare en del av [Cal Combiner](https://github.com/Cebbas/cal_combiner)
men är utbrutet till en egen, fristående integration: den pratar bara med
vanliga `calendar.*`-entiteter i Home Assistant och behöver inte Cal Combiner
installerat för att fungera.

## 1. Installation

**Manuellt:**
1. Kopiera mappen `cal_activity/` till `config/custom_components/` på din
   HA-installation (t.ex. via Samba, SSH eller Studio Code Server-tillägget).
2. Starta om Home Assistant.

**Via HACS (custom repository):**
1. HACS → tre punkter uppe till höger → *Custom repositories*
2. Lägg till `https://github.com/Cebbas/cal_activity_sensors` med kategori
   *Integration*
3. Sök upp "Cal Activity Sensors" i HACS och installera, starta om HA.

## 2. Skapa en sensor

Enklast via sidopanelen: efter installation dyker **Cal Activity** upp som en
egen flik i sidomenyn (kräver adminkonto). Där väljer du först typ:

**Aktivitet** (kalenderevent pågår/inträffar):
- Välj en eller flera källkalendrar (`calendar.*`-entiteter, t.ex. din
  Google-kalender eller en sammanslagen kalender från Cal Combiner)
- Sätt ett filter: fält att matcha mot (titel/beskrivning/plats/alla),
  inkludera/uteslut-ord, regex-läge, skiftlägeskänslighet
- Välj om sensorn ska vara "på" när ett event pågår just nu, eller när ett
  matchande event inträffar någon gång samma dag

**Nedräkning / livshändelse** (dagar kvar):
- Ett fast datum (återkommande varje år som förval - räknar ålder/antal år,
  t.ex. namnsdagar, jubileum) eller ett matchande kalenderevent
- Valfritt slutdatum (eller kalenderns eget slutdatum) för flerdagshändelser
  som en resa - sensorn är då "på" hela perioden, inte bara första dagen

**Födelsedag** (dagar kvar, räknar ålder):
- Ett eget, förenklat formulär (bara namn + datum) för det vanligaste
  specialfallet av Nedräkning/livshändelse ovan - alltid återkommande,
  alltid ett fast datum. Räknar automatiskt åldern som attributet `age`
- Avancerat, valfritt: koppla till en `person.*`-entitet - används som
  bildkälla om ingen egen bild är satt, och läggs till som attributet
  `person`
- Avancerat, valfritt: skriv till en kalender - välj en `calendar.*`-entitet
  (t.ex. en delad Local Calendar) och sensorn lägger automatiskt in sitt
  aktuella årliga tillfälle där som en heldagshändelse. Synkas om
  automatiskt när nästa års datum räknas fram - ingen manuell uppdatering
  behövs. Byter du kalender eller tar bort sensorn försvinner inte en
  redan skapad händelse i den gamla kalendern automatiskt; ta bort den
  manuellt om du inte vill ha den kvar

Alla typer (inklusive Födelsedag) går att skapa och redigera både via
sidopanelen och Inställningar → Enheter & tjänster, och visar en logg över
senaste ändringarna direkt på panelkortet.

Går även via Inställningar → Enheter & tjänster → Lägg till integration →
**Cal Activity Sensors**, om du föredrar den vanliga inställningsdialogen.
Redigera/ta bort dem enklast i panelen, eller via Konfigurera-knappen i
Inställningar → Enheter & tjänster - båda täcker alla typer.

## 3. Vad du får

Varje konfiguration skapar exakt en `binary_sensor`-entitet - state är
`on`/`off`, all annan information (vilket event, nästa datum, dagar kvar...)
är attribut:

- **Aktivitet**: `on` enligt valt läge, attribut `current_event`
  (+ `active_until` - när det pågående eventet slutar), `next_event`,
  `next_start`, `next_end`, `matches_today`, `location`, `failed_sources`
- **Nedräkning / livshändelse**: `on` den dag (eller hela perioden, för
  flerdagshändelser) datumet/eventet inträffar, attribut `phase`
  (`upcoming`/`in_progress`/`passed`), `days_remaining`, `days_until_start`,
  `next_date`, `label`, `years`, `end_date`/`day_of_span`/`span_length`
  (flerdagshändelser), `failed_sources`
- **Födelsedag**: samma som Nedräkning/livshändelse ovan, plus `age` (alias
  för `years`) och, om kopplad till en person, attributet `person`

Exempel: en aktivitetssensor med källa = din Google-kalender och filter
"inkludera: Zoo" ger en `binary_sensor.zoo_besok` som är `on` när ett
Zoo-event pågår (eller hela dagen zoo-eventet finns, om du valt det läget) –
trigga automationer på det (t.ex. stäng av larmet, sätt på "borta"-läge,
eller skicka en påminnelse).

## 4. Om en källa inte svarar

Om en källkalender inte går att nå exkluderas den tillfälligt för den
pollningen, syns som `failed_sources` på entiteten, och loggas i sensorns
"Senaste händelser"-lista i panelen. Misslyckas den två pollningar i rad
(~10 min) syns det även som en riktig issue under Inställningar → Repairs -
en enstaka tillfällig blip flaggas alltså inte direkt. Issuen försvinner
automatiskt igen så fort källan svarar normalt.

## 5. Tester

Filterlogik, kalenderhämtning, datummatten för nedräkningssensorerna
(`next_span`/`_end_inclusive`, inkl. skottdag och årsskiftesspann) och
båda sensor-typernas `is_on`/attribut-logik täcks av en pytest-svit under
`tests/`, byggd på `pytest-homeassistant-custom-component`. Köra lokalt:

```bash
pip install -r requirements_test.txt
pytest tests/ -q
```

Körs även automatiskt i CI (`.github/workflows/validate.yml`) vid varje
push/PR.

## 6. Bygga vidare

Se `IDEAS.md` för en avbockningsbar lista över vad som är gjort och vad som
återstår.

## Filstruktur

```
custom_components/
  cal_activity/
    __init__.py       # setup, registrerar panel + ws-api, städar ev. kvarblivna entitetsposter
    activity.py          # coordinator + delad hämtnings-/filterlogik för aktivitetssensorer
    life_event.py            # coordinator + datumlogik för nedräknings-/livshändelsesensorer
    activity_log.py             # rullande "senaste händelser"-logg per sensor
    binary_sensor.py                # den enda entitetsplattformen - både aktivitet och nedräkning
    diagnostics.py                     # exporterbar felsökningsdata
    config_flow.py                        # UI för att lägga till/ändra en sensor
    panel.py                                 # registrerar sidopanelen + statiska filer
    ws_api.py                                   # websocket-kommandon som panelen använder
    const.py
    manifest.json
    hacs.json
    strings.json
    translations/
      en.json
      sv.json
    www/
      cal-activity-panel.js  # sidopanelens UI (vanilla JS)
tests/               # pytest-svit (filter, kalenderhämtning, datummatte, sensorlogik)
requirements_test.txt
pytest.ini
```
