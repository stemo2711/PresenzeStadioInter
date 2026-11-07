# Le mie partite dell'Inter a San Siro

Dataset personale delle partite viste a San Siro, con statistiche pubblicate come pagina web (comoda da telefono)
che si aggiorna da sola a ogni modifica dei dati.

## Cartella del repository

```
presenze_stadio.csv            <- il tuo dataset (lo aggiorni tu)
formazioni_complete.csv        <- formazioni ESPN + Supercoppe (lo aggiorni tu)
statistiche_inter.ipynb        <- notebook statistiche partite
formazioni_inter.ipynb         <- notebook formazioni
build_site.py                  <- esegue i notebook e crea il sito
requirements.txt
.gitignore
.github/workflows/pubblica.yml <- l'automazione (GitHub Actions)
```

Gli script di estrazione (`inter_san_siro.py`, `formazioni_espn.py`, ecc.) puoi tenerli qui se vuoi, oppure solo sul PC:
non servono al sito. Le cartelle `cache_*` non vengono caricate (sono nel `.gitignore`).

## Prima configurazione (una volta sola)

1. Crea un repository su github.com (per esempio `inter-san-siro`).
   Con l'account gratuito le pagine web (GitHub Pages) funzionano **solo con repository pubblico**.
2. Carica tutti i file della cartella sopra, rispettando le sottocartelle (`.github/workflows/pubblica.yml` compreso).
   Da terminale:
   ```
   git init
   git add .
   git commit -m "Primo caricamento"
   git branch -M main
   git remote add origin https://github.com/TUO_UTENTE/inter-san-siro.git
   git push -u origin main
   ```
3. Sul sito di GitHub: **Settings -> Pages -> Build and deployment -> Source: GitHub Actions**.
4. Vai nel tab **Actions**: parte da solo il workflow "Pubblica statistiche" (ci vogliono 2-4 minuti).
   Quando è verde, l'indirizzo del sito è `https://TUO_UTENTE.github.io/inter-san-siro/`.
5. Da telefono apri l'indirizzo e usa "Aggiungi alla schermata Home" per averlo come icona.

## Aggiornare i dati

Ogni volta che cambi `presenze_stadio.csv` o `formazioni_complete.csv` (o un notebook) e lo carichi su GitHub,
il sito si ricostruisce da solo:

```
git add presenze_stadio.csv formazioni_complete.csv
git commit -m "Aggiunta partita"
git push
```

Senza terminale puoi anche aprire il file su github.com, premere **Add file -> Upload files** e trascinare
il CSV aggiornato (anche da telefono). Per rifare la pubblicazione a mano: tab **Actions -> Pubblica statistiche -> Run workflow**.

## Provare tutto sul PC prima di pubblicare

```
pip install -r requirements.txt
python build_site.py
```
poi apri `site/index.html` nel browser.

## Se qualcosa non va

- **Il workflow è rosso**: apri l'esecuzione nel tab Actions e leggi il passaggio "Esegui i notebook". Di solito è un CSV
  mancante o una colonna con un nome diverso. In caso di errore il sito precedente resta online (non viene sostituito).
- **Manca la pagina "I giocatori"**: serve `formazioni_complete.csv` (oppure `formazioni.csv`) nella cartella principale.
- **Avviso su versioni delle action** (`actions/checkout@v4` ecc.): aggiorna il numero di versione nel file del workflow.

## Privacy

Il sito è pubblico: chiunque abbia il link può vederlo, e con repository pubblico anche i CSV sono leggibili
(date delle partite, settore, ecc.). Con piani a pagamento il repository può essere privato, ma il sito pubblicato
con GitHub Pages resta comunque pubblico.
