# Globale Spielerliste
SPIELER = ["Jonas", "Marlon", "Paul", "Vossi"]

# Finanz-Parameter für Abrechnungslogik
PLATZPREIS = 19
FAKTOR = 200 / 250
KARTEN_WERT = 200.0

# Basis für die Verteilung der Karten-Abrechnung, wenn das Guthaben aufgebraucht ist:
#   "kosten"    -> Verteilung nach tatsächlich angefallenen Kosten pro Spieler
#                  (berücksichtigt, dass Sessions mit mehr Mitspielern pro Kopf
#                   günstiger waren)
#   "einheiten" -> alte Logik: Verteilung nach Summe der gespielten Einheiten,
#                  unabhängig davon, wie viele Personen sich die Session geteilt haben
ABRECHNUNG_BASIS = "kosten"

# Sortierungs-Reihenfolge für Tabellen-Anzeigen
ORDERED_COLUMNS = ["eingetragen_von", "gespielt_am", "spieler", "eingetragen_am", "einheiten", "kosten"]
