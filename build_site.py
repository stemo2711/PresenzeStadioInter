#!/usr/bin/env python3
"""
Costruisce il sito statico (cartella ./site) a partire dai notebook:
  - esegue i notebook con i dati attuali (nbconvert --execute)
  - li esporta in HTML senza codice, con CSS per il telefono
  - crea una home page (index.html) con qualche numero riassuntivo

Uso locale:   python build_site.py     (poi apri site/index.html)
Su GitHub:    lo lancia il workflow .github/workflows/pubblica.yml a ogni aggiornamento del dataset.
"""

import datetime
import html
import pathlib
import re
import subprocess
import sys

import pandas as pd

SITE = pathlib.Path("site")
PRESENZE = pathlib.Path("presenze_stadio.csv")

# (notebook, nome pagina, titolo, descrizione, file che servono)
REPORT = [
    ("statistiche_inter.ipynb", "statistiche.html",
     "Le partite", "Risultati, competizioni, marcatori, cartellini, arbitri, settori.",
     [PRESENZE]),
    ("formazioni_inter.ipynb", "formazioni.html",
     "I giocatori", "Chi ho visto più volte, avversari, moduli.",
     [PRESENZE, [pathlib.Path("formazioni_complete.csv"), pathlib.Path("formazioni.csv")]]),
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
  .back { display: inline-block; margin: 10px; padding: 6px 12px; border-radius: 8px;
          background: #1565c0; color: #fff !important; text-decoration: none; font: 14px sans-serif; }
</style>
"""
LINK_INDIETRO = '<a class="back" href="index.html">&larr; Home</a>'


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


def kpi():
    """Numeri per la home. Se qualcosa manca nel CSV, salta quella voce."""
    voci = []
    try:
        d = pd.read_csv(PRESENZE)
    except Exception:
        return voci
    voci.append(("Partite viste", len(d)))
    if "esito_inter" in d.columns:
        e = d["esito_inter"].value_counts()
        voci += [("Vittorie", int(e.get("V", 0))), ("Pareggi", int(e.get("N", 0))),
                 ("Sconfitte", int(e.get("P", 0)))]
    for etichetta, col in (("Gol fatti", "gol_inter"), ("Gol subiti", "gol_avversario")):
        if col in d.columns:
            voci.append((etichetta, int(pd.to_numeric(d[col], errors="coerce").sum())))
    return voci


def crea_indice(pagine):
    ora = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    celle = "".join(f'<div class="k"><b>{html.escape(str(v))}</b><span>{html.escape(l)}</span></div>'
                    for l, v in kpi())
    link = "".join(f'<a class="card" href="{html.escape(p)}"><h2>{html.escape(t)}</h2>'
                   f'<p>{html.escape(desc)}</p></a>' for p, t, desc in pagine)
    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Le mie partite dell'Inter a San Siro</title>
<style>
  :root {{ --bg:#fff; --fg:#111; --card:#f1f4f9; --acc:#1565c0; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#111; --fg:#eee; --card:#1e2530; --acc:#64b5f6; }} }}
  body {{ margin:0; padding:16px; background:var(--bg); color:var(--fg); font:16px/1.4 -apple-system,Segoe UI,Roboto,sans-serif; max-width:640px; margin:auto; }}
  h1 {{ font-size:22px; }}
  .kpi {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:16px 0; }}
  .k {{ background:var(--card); border-radius:12px; padding:12px 6px; text-align:center; }}
  .k b {{ display:block; font-size:24px; color:var(--acc); }}
  .k span {{ font-size:12px; opacity:.8; }}
  .card {{ display:block; background:var(--card); border-radius:12px; padding:14px 16px; margin:10px 0; text-decoration:none; color:inherit; }}
  .card h2 {{ margin:0 0 4px; font-size:18px; color:var(--acc); }}
  .card p {{ margin:0; font-size:14px; opacity:.85; }}
  footer {{ margin-top:24px; font-size:12px; opacity:.6; }}
</style></head><body>
<h1>Le mie partite dell'Inter a San Siro</h1>
<div class="kpi">{celle}</div>
{link}
<footer>Aggiornato il {ora}</footer>
</body></html>"""


def main():
    SITE.mkdir(exist_ok=True)
    pagine = []
    for notebook, pagina, titolo, descr, richiesti in REPORT:
        if not pathlib.Path(notebook).exists() or not file_disponibili(richiesti):
            print(f"Salto {notebook}: notebook o dati mancanti")
            continue
        converti(notebook, pagina)
        pagine.append((pagina, titolo, descr))
    if not pagine:
        sys.exit("Nessun report costruito: controlla che notebook e CSV siano nella cartella principale.")
    (SITE / "index.html").write_text(crea_indice(pagine), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print("Sito pronto in ./site")


if __name__ == "__main__":
    main()
