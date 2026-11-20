#!/usr/bin/env python3
"""
Costruisce il sito statico (cartella ./site):
  - index.html: home interattiva con ricerca (partite, giocatori, marcatori, arbitri, settori...),
    pagine partita con formazioni e cronaca, pagine giocatore. I dati dei CSV sono incorporati
    nella pagina, la ricerca gira nel browser (home_template.html)
  - statistiche.html / formazioni.html: i report dei notebook (eseguiti con nbconvert)

Uso locale:   python build_site.py     (poi apri site/index.html)
Su GitHub:    lo lancia il workflow .github/workflows/pubblica.yml a ogni aggiornamento del dataset.
"""

import datetime
import html
import json
import pathlib
import re
import subprocess
import sys
import unicodedata

import pandas as pd

SITE = pathlib.Path("site")
PRESENZE = pathlib.Path("presenze_stadio.csv")
FORMAZIONI_COMPLETE = pathlib.Path("formazioni_complete.csv")
FORMAZIONI_ESPN = pathlib.Path("formazioni.csv")
FORMAZIONI_WIKI = pathlib.Path("formazioni_supercoppa_wikipedia.csv")
TEMPLATE = pathlib.Path("home_template.html")

# (notebook, nome pagina, titolo, descrizione, file che servono)
REPORT = [
    ("statistiche_inter.ipynb", "statistiche.html",
     "Statistiche complete", "Risultati, competizioni, marcatori, cartellini, arbitri, settori.",
     [PRESENZE]),
    ("formazioni_inter.ipynb", "formazioni.html",
     "Giocatori: report completo", "Chi ho visto più volte, avversari, moduli.",
     [PRESENZE, [FORMAZIONI_COMPLETE, FORMAZIONI_ESPN]]),
]

CSS_TELEFONO = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html, body { margin: 0 !important; padding: 0 !important; }
  body.jp-Notebook, .jp-Notebook, #notebook-container, .container {
      max-width: 100% !important; padding: 8px 10px !important; box-shadow: none !important; }
  img, svg { max-width: 100% !important; height: auto !important; }
  table { display: block; overflow-x: auto; max-width: 100%; font-size: 12px; }
  pre { overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
  .jp-OutputArea-output, .output_area { overflow-x: auto; }
  .strisce { height: 10px; background: repeating-linear-gradient(90deg, #1637a8 0 22px, #04060d 22px 44px); }
  .back { display: inline-block; margin: 10px; padding: 6px 14px; border-radius: 8px;
          background: #04060d; color: #e8b873 !important; text-decoration: none; font: 15px sans-serif; }
</style>
"""
LINK_INDIETRO = '<div class="strisce"></div><a class="back" href="index.html">&larr; Home</a>'


# ----------------------------------------------------------------------------
# Report dei notebook
# ----------------------------------------------------------------------------
def inietta_css(testo_html):
    """Aggiunge viewport + CSS per il telefono e il link alla home."""
    if "</head>" in testo_html:
        testo_html = testo_html.replace("</head>", CSS_TELEFONO + "</head>", 1)
    else:
        testo_html = CSS_TELEFONO + testo_html
    return re.sub(r"(<body[^>]*>)", r"\1" + LINK_INDIETRO, testo_html, count=1, flags=re.I)


def converti(notebook, pagina):
    """Esegue il notebook e lo salva in HTML (senza celle di codice)."""
    cmd = [sys.executable, "-m", "jupyter", "nbconvert", "--to", "html", "--execute", "--no-input",
           "--ExecutePreprocessor.timeout=900",
           "--output", pathlib.Path(pagina).stem, "--output-dir", str(SITE), notebook]
    print("->", " ".join(cmd))
    subprocess.run(cmd, check=True)   # se il notebook va in errore, il workflow si ferma e non pubblica nulla
    percorso = SITE / pagina
    percorso.write_text(inietta_css(percorso.read_text(encoding="utf-8")), encoding="utf-8")


def file_disponibili(richiesti):
    for r in richiesti:
        opzioni = r if isinstance(r, list) else [r]
        if not any(p.exists() for p in opzioni):
            return False
    return True


# ----------------------------------------------------------------------------
# Dati per la home
# ----------------------------------------------------------------------------
def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def is_inter(nome):
    low = str(nome or "").lower().strip()
    return low in ("inter", "internazionale", "inter milan") or low.startswith("internazionale")


def pulito(x):
    return None if pd.isna(x) else x


def intero(x):
    try:
        return None if pd.isna(x) else int(float(x))
    except (TypeError, ValueError):
        return None


def vero(x):
    return str(x).strip().lower() not in ("", "nan", "false", "none", "0", "<na>")


def sostituzione(raw):
    """'' = no; '1' = si' (minuto sconosciuto); altrimenti il minuto."""
    s = str(raw).strip()
    if s.lower() in ("", "nan", "false", "none", "0", "<na>"):
        return ""
    return s if re.fullmatch(r"\d+(\+\d+)?", s) else "1"


def parse_eventi(s):
    """"Milito 24'; Icardi 6' (rig.)" -> [{nome, min, nota}]"""
    if not isinstance(s, str) or not s.strip():
        return []
    out = []
    for parte in s.split(";"):
        parte = parte.strip()
        if not parte:
            continue
        m = re.match(r"^(.*?)\s+(\d+(?:\+\d+)?)'\s*(?:\(([^)]*)\))?$", parte)
        if m:
            out.append({"nome": m.group(1).strip(), "min": m.group(2), "nota": m.group(3) or ""})
        else:
            out.append({"nome": parte, "min": "", "nota": ""})
    return out


def prepara_formazioni():
    """Legge le formazioni e assegna a ogni giocatore una chiave stabile (id ESPN o nome)."""
    dtypes = {"athlete_id": "string", "numero": "string"}
    if FORMAZIONI_COMPLETE.exists():
        parti = [pd.read_csv(FORMAZIONI_COMPLETE, dtype=dtypes)]
    else:
        parti = [pd.read_csv(p, dtype=dtypes) for p in (FORMAZIONI_ESPN, FORMAZIONI_WIKI) if p.exists()]
    if not parti:
        return None
    f = pd.concat(parti, ignore_index=True)
    f["data"] = pd.to_datetime(f["data"]).dt.strftime("%Y-%m-%d")
    f["titolare"] = f["titolare"].map(vero)
    f["si"] = f["sub_in_raw"].map(sostituzione)
    f["so"] = f["sub_out_raw"].map(sostituzione)
    f["gio"] = f["titolare"] | (f["si"] != "")

    # Righe da Wikipedia (senza id): le abbino a un giocatore ESPN della stessa squadra,
    # se il nome e' contenuto in uno di quelli ESPN ("Julio Cruz" ~ "Julio Ricardo Cruz")
    token = {}
    for (sq, aid), g in f[f["athlete_id"].notna()].groupby(["squadra", "athlete_id"]):
        token[(sq, aid)] = [set(norm(n)) for n in g["giocatore"].unique()]

    def trova_id(nome, squadra):
        t = set(norm(nome))
        if not t:
            return None
        cand = {aid for (sq, aid), liste in token.items() if sq == squadra and any(t <= x for x in liste)}
        return next(iter(cand)) if len(cand) == 1 else None

    chiavi = []
    for r in f.itertuples(index=False):
        if pd.notna(r.athlete_id):
            chiavi.append(str(r.athlete_id))
        else:
            aid = trova_id(r.giocatore, r.squadra)
            chiavi.append(str(aid) if aid is not None else "w:" + "-".join(norm(r.giocatore)))
    f["chiave"] = chiavi
    nome_per_chiave = f.groupby("chiave")["giocatore"].agg(lambda s: s.value_counts().index[0])
    f["nome"] = f["chiave"].map(nome_per_chiave)
    return f


def lineups_per_data(f):
    out = {}
    if f is None:
        return out
    for data, g in f.groupby("data"):
        lati = {}
        for etichetta, lato in (("Inter", "I"), ("Avversario", "A")):
            gg = g[g["squadra"] == etichetta]
            if gg.empty:
                continue
            mod = gg["modulo"].dropna()
            giocatori = []
            for r in gg.itertuples(index=False):
                giocatori.append({"k": r.chiave, "n": r.nome,
                                  "u": "" if pd.isna(r.numero) else str(r.numero),
                                  "r": "" if pd.isna(r.ruolo) else str(r.ruolo),
                                  "t": int(r.titolare), "g": int(r.gio), "si": r.si, "so": r.so})
            giocatori.sort(key=lambda x: -x["t"])      # titolari prima, ordine originale (sort stabile)
            lati[lato] = {"mod": str(mod.iloc[0]) if len(mod) else "", "g": giocatori}
        out[data] = lati
    return out


def contiene(tok_evento, tok_giocatore):
    """Tutte le parole del nome dell'evento sono nel nome del giocatore (le iniziali valgono come prefisso)."""
    for t in tok_evento:
        if len(t) == 1:
            if not any(x.startswith(t) for x in tok_giocatore):
                return False
        elif t not in tok_giocatore:
            return False
    return True


def abbina_evento(nome, lista):
    t = norm(nome)
    if not t or not lista:
        return None
    cand = [g for g in lista if contiene(t, norm(g["n"]))]
    if len(cand) > 1:
        cand = [g for g in cand if g["g"]] or cand
    if len(cand) > 1:
        cand = [g for g in cand if norm(g["n"]) == t] or cand
    return cand[0]["k"] if len(cand) == 1 else None


def registro_giocatori(lineups):
    """Tutti i giocatori noti, per lato (I = Inter, A = avversari)."""
    reg = {"I": {}, "A": {}}
    for lati in lineups.values():
        for lato, v in lati.items():
            for g in v["g"]:
                reg[lato][g["k"]] = g["n"]
    return reg


def abbina_globale(nome, reg_lato):
    """Per le partite senza formazione: cognome -> giocatore noto, solo se l'abbinamento e' unico."""
    t = norm(nome)
    cand = [k for k, n in reg_lato.items() if t and contiene(t, norm(n))]
    return cand[0] if len(cand) == 1 else None


def costruisci_dati():
    d = pd.read_csv(PRESENZE)
    d["data"] = pd.to_datetime(d["data"], errors="coerce")
    d = d.dropna(subset=["data"]).sort_values("data").reset_index(drop=True)
    lineups = lineups_per_data(prepara_formazioni())
    reg = registro_giocatori(lineups)

    partite = []
    for i, r in d.iterrows():
        iso = r["data"].strftime("%Y-%m-%d")
        ic = str(r.get("inter_in_casa", "")).strip().lower() == "true"
        casa, tras = pulito(r.get("casa")) or "", pulito(r.get("trasferta")) or ""
        gi, ga = intero(r.get("gol_inter")), intero(r.get("gol_avversario"))
        punteggio = pulito(r.get("punteggio")) or (
            "" if gi is None else (f"{gi}–{ga}" if ic else f"{ga}–{gi}"))
        rep = str(pulito(r.get("report")) or "").strip()
        fo = lineups.get(iso)

        eventi = []
        for colonna_base, tipo in (("marcatori", "g"), ("ammoniti", "a"), ("espulsi", "e")):
            for lato_csv, inter_lato in (("casa", ic), ("trasferta", not ic)):
                q = "I" if inter_lato else "A"
                for e in parse_eventi(r.get(f"{colonna_base}_{lato_csv}")):
                    # autogol: elencato sotto la squadra che ne beneficia, col nome di chi l'ha fatto
                    cerca_in = ("A" if q == "I" else "I") if e["nota"] == "aut." else q
                    k = abbina_evento(e["nome"], (fo or {}).get(cerca_in, {}).get("g", []))
                    if k is None:
                        k = abbina_globale(e["nome"], reg[cerca_in])
                    eventi.append({"t": tipo, "q": q, "n": e["nome"], "m": e["min"], "x": e["nota"], "k": k})

        partite.append({
            "id": i, "d": iso, "s": str(pulito(r.get("stagione")) or ""),
            "c": str(pulito(r.get("competizione")) or ""), "t": str(pulito(r.get("turno")) or ""),
            "o": str(pulito(r.get("orario")) or ""), "ic": ic,
            "av": str(pulito(r.get("avversario")) or ""),
            "casa": "Inter" if is_inter(casa) else casa, "tr": "Inter" if is_inter(tras) else tras,
            "p": punteggio, "gi": gi, "ga": ga, "e": str(pulito(r.get("esito_inter")) or ""),
            "stad": str(pulito(r.get("stadio")) or ""), "arb": str(pulito(r.get("arbitro")) or ""),
            "pr": intero(r.get("presenze")), "se": str(pulito(r.get("settore")) or ""),
            "rep": rep if rep.startswith("http") else "",
            "ev": eventi, "fo": fo,
        })
    return {"partite": partite}


def crea_home(pagine):
    dati = costruisci_dati()
    dati["pagine"] = [{"href": p, "titolo": t, "descr": desc} for p, t, desc in pagine]
    dati["agg"] = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    js = json.dumps(dati, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("__DATI_JSON__", js)


# ----------------------------------------------------------------------------
# Home semplice di riserva (se manca home_template.html)
# ----------------------------------------------------------------------------
def crea_indice_semplice(pagine):
    ora = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    link = "".join(f'<p><a href="{html.escape(p)}">{html.escape(t)}</a> &ndash; {html.escape(d)}</p>'
                   for p, t, d in pagine)
    return (f'<!doctype html><html lang="it"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Partite a San Siro</title></head><body style="font-family:sans-serif;padding:16px">'
            f'<h1>Le mie partite a San Siro</h1>{link}<small>Aggiornato il {ora}</small></body></html>')


def main():
    SITE.mkdir(exist_ok=True)
    pagine = []
    for notebook, pagina, titolo, descr, richiesti in REPORT:
        if not pathlib.Path(notebook).exists() or not file_disponibili(richiesti):
            print(f"Salto {notebook}: notebook o dati mancanti")
            continue
        converti(notebook, pagina)
        pagine.append((pagina, titolo, descr))

    if not PRESENZE.exists():
        sys.exit(f"Manca {PRESENZE}: impossibile costruire il sito.")
    if TEMPLATE.exists():
        indice = crea_home(pagine)
    else:
        print(f"Attenzione: manca {TEMPLATE}, uso la home semplice")
        indice = crea_indice_semplice(pagine)
    (SITE / "index.html").write_text(indice, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print("Sito pronto in ./site")


if __name__ == "__main__":
    main()
