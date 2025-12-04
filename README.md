# ArbiBot - Online Arbitrage Bot

Eine Webanwendung für Online-Arbitrage via RSS-Feeds mit AI-gestützter Produkterkennung und automatischen E-Mail-Benachrichtigungen.

## Features

- 🤖 **AI-gestützte Produkterkennung** mit Google Gemini
- 📊 **Dashboard** mit Live-Logs und Winners-Ansicht
- 🔒 **Passwortgeschützt** via HTTP Basic Auth
- ⏰ **Automatisierter Cron-Job** (alle 2 Stunden, 8:00-20:00 Uhr)
- 📧 **E-Mail-Benachrichtigungen** bei profitablen Deals (>15€)
- 🛒 **eBay Marktpreis-Analyse** für Arbitrage-Berechnung

## Setup

### 1. Supabase Datenbank einrichten

Führe das SQL-Schema aus `schema.sql` in deinem Supabase-Projekt aus.

### 2. Umgebungsvariablen konfigurieren

Kopiere `.env.example` zu `.env` und fülle alle Werte aus:

```bash
cp .env.example .env
```

### 3. eBay API Setup

1. Registriere dich bei [eBay Developers](https://developer.ebay.com/)
2. Erstelle eine neue App und kopiere die App ID
3. Trage die App ID in `.env` ein

**Hinweis:** Die eBay Finding API ist deprecated. Für Produktion solltest du die eBay Browse API mit OAuth verwenden.

### 4. Gmail App-Passwort erstellen

1. Gehe zu deinem Google Account → Sicherheit
2. Aktiviere 2-Faktor-Authentifizierung
3. Erstelle ein App-spezifisches Passwort
4. Verwende dieses Passwort in `.env` (nicht dein normales Gmail-Passwort!)

### 5. Vercel Deployment

```bash
# Installiere Vercel CLI
npm i -g vercel

# Deploy
vercel

# Setze Umgebungsvariablen in Vercel Dashboard
# oder via CLI:
vercel env add SUPABASE_URL
vercel env add SUPABASE_KEY
# ... etc.
```

## Projektstruktur

```
.
├── app.py              # Haupt-Flask-Anwendung
├── schema.sql          # Supabase Datenbank-Schema
├── requirements.txt    # Python Dependencies
├── vercel.json        # Vercel Konfiguration (inkl. Cron)
├── .env.example       # Beispiel Umgebungsvariablen
└── README.md          # Diese Datei
```

## Cron-Job Zeitplan

Der Cron-Job läuft automatisch:
- **Zeitplan:** `0 8-20/2 * * *` (Minute 0, von 8 bis 20 Uhr, alle 2 Stunden)
- **Route:** `/api/cron`
- **Zeitfenster:** 08:00 - 20:00 Uhr

## RSS-Quellen

- mydealz.de/rss/hot
- dealdoktor.de/feed/
- schnaeppchenfuchs.de/feed

## Technologie-Stack

- **Backend:** Flask (Python 3.9+)
- **Hosting:** Vercel Serverless
- **Datenbank:** Supabase (PostgreSQL)
- **AI:** Google Gemini API (gemini-2.0-flash-exp)
- **Marktdaten:** eBay Browse/Finding API
- **E-Mail:** Gmail SMTP

## Sicherheit

- Dashboard ist mit HTTP Basic Auth geschützt
- Umgebungsvariablen werden nicht im Code gespeichert
- Verwende starke Passwörter für Basic Auth

## Troubleshooting

### Cron-Job läuft nicht
- Prüfe Vercel Dashboard → Cron Jobs
- Stelle sicher, dass Umgebungsvariablen gesetzt sind
- Prüfe Logs in Vercel Dashboard

### E-Mails werden nicht versendet
- Stelle sicher, dass Gmail App-Passwort verwendet wird (nicht normales Passwort)
- Prüfe, ob 2FA aktiviert ist
- Prüfe Spam-Ordner

### eBay API Fehler
- Stelle sicher, dass App ID korrekt ist
- Prüfe API-Limits in eBay Developer Portal
- Für Produktion: Implementiere OAuth für Browse API

## Lizenz

MIT

