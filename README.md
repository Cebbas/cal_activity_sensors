# Cal Activity Sensors – Home Assistant custom integration

Bygger fristående `binary_sensor`/`sensor`-par från ett filtrerat urval av
kalenderaktivitet – t.ex. en `binary_sensor.zoo_besok` som är `on` när ett
Zoo-event pågår, perfekt att trigga automationer på.

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

## 2. Skapa en aktivitetssensor

Enklast via sidopanelen: efter installation dyker **Cal Activity** upp som en
egen flik i sidomenyn (kräver adminkonto). Där kan du:

- Välja en eller flera källkalendrar (`calendar.*`-entiteter, t.ex. din
  Google-kalender eller en sammanslagen kalender från Cal Combiner)
- Sätta ett filter: fält att matcha mot (titel/beskrivning/plats/alla),
  inkludera/uteslut-ord, regex-läge, skiftlägeskänslighet
- Välja om `binary_sensor`:n ska vara "på" när ett event pågår just nu, eller
  när ett matchande event inträffar någon gång samma dag
- Välja om du vill ha `binary_sensor`, `sensor`, eller båda
- Sätta egen ikon och bild
- Se en logg över senaste ändringarna direkt på kortet

Går även via Inställningar → Enheter & tjänster → Lägg till integration →
**Cal Activity Sensors**, om du föredrar den vanliga inställningsdialogen.
Redigera/ta bort dem enklast i panelen, eller via Konfigurera-knappen i
Inställningar → Enheter & tjänster.

## 3. Vad du får

Varje aktivitetssensor kan skapa:

- **`binary_sensor`**: `on` beroende på vilket läge du valt – antingen "ett
  event pågår just nu" eller "ett event inträffar någon gång idag" – med
  attribut `current_event`, `next_event`, `next_start`, `failed_sources`
- **`sensor`**: state = titeln på pågående (eller näst kommande) matchande
  event, attribut `matches_today`, `next_start`, `next_end`, `location`,
  `failed_sources`

Exempel: en sensor med källa = din Google-kalender och filter
"inkludera: Zoo" ger en `binary_sensor.zoo_besok` som är `on` när ett
Zoo-event pågår (eller hela dagen zoo-eventet finns, om du valt det läget) –
trigga automationer på det (t.ex. stäng av larmet, sätt på "borta"-läge,
eller skicka en påminnelse).

## 4. Om en källa inte svarar

Om en källkalender inte går att nå exkluderas den tillfälligt för den
pollningen, syns som `failed_sources` på entiteten, och loggas i sensorns
"Senaste händelser"-lista i panelen.

## 5. Bygga vidare

Se `IDEAS.md` för en avbockningsbar lista över vad som är gjort och vad som
återstår.

## Filstruktur

```
custom_components/
  cal_activity/
    __init__.py       # setup, registrerar panel + ws-api
    activity.py          # coordinator + delad hämtnings-/filterlogik (fristående, ingen extern kalender-integration krävs)
    activity_log.py         # rullande "senaste händelser"-logg per sensor
    binary_sensor.py           # på/av (nu eller idag)
    sensor.py                     # aktuellt/nästa event
    config_flow.py                  # UI för att lägga till/ändra en sensor
    panel.py                           # registrerar sidopanelen + statiska filer
    ws_api.py                             # websocket-kommandon som panelen använder
    const.py
    manifest.json
    hacs.json
    strings.json
    translations/
      en.json
      sv.json
    www/
      cal-activity-panel.js  # sidopanelens UI (vanilla JS)
```
