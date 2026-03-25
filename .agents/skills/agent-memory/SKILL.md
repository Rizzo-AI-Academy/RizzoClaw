---
name: agent-memory
description: Gestisce la memoria persistente dell'agente AI in file markdown locali. Usa questa skill ogni volta che l'utente vuole che l'agente ricordi sessioni precedenti, mantenga un contesto tra conversazioni, salvi riassunti giornalieri, cerchi nella cronologia delle sessioni, o tenga traccia dell'avanzamento di task di coding. Attiva anche quando l'utente dice "ricordati di", "cosa abbiamo fatto ieri", "aggiorna la memoria", "controlla i progressi", "segna come completato", o inizia/finisce una sessione di lavoro. Usa questa skill proattivamente all'inizio di ogni sessione (leggi BRAIN.md) e alla fine (aggiorna la memoria).
---

# Agent Memory — Gestione della Memoria Persistente

Questa skill definisce come gestire la memoria dell'agente AI attraverso file markdown locali, garantendo continuità tra sessioni diverse.

## Struttura della memoria

```
<project-root>/
├── BRAIN.md          ← contesto globale, letto all'avvio di ogni sessione
├── PROGRESS.md       ← todo list per task di coding (solo quando si sviluppa codice)
└── memories/
    ├── 2024-01-15/
    │   └── session.md   ← riassunto della sessione di quel giorno
    ├── 2024-01-16/
    │   └── session.md
    └── ...
```

Il percorso base è la root del progetto corrente (dove si trova il CLAUDE.md o il file principale del progetto).

---

## 1. BRAIN.md — Contesto Globale

### Quando leggere
Leggi sempre `BRAIN.md` all'inizio di ogni nuova sessione, **prima** di rispondere alla prima richiesta dell'utente. Se il file non esiste ancora, crealo vuoto e inizia dalla sessione corrente.

### Struttura del file
```markdown
# 🧠 BRAIN — Contesto Agente

## Ultima sessione
**Data:** yyyy-mm-gg
**Argomenti trattati:** breve lista degli argomenti principali

## Contesto utente
Preferenze, abitudini di lavoro, informazioni rilevanti sull'utente emerse nel tempo.

## Decisioni importanti
Scelte architetturali, preferenze tecniche, o decisioni prese che potrebbero influenzare il lavoro futuro.

## In sospeso
Cose non completate o da riprendere nella prossima sessione.
```

### Quando aggiornare
Aggiorna `BRAIN.md` alla **fine della sessione** (quando l'utente saluta, dice "a dopo", "stop", o esplicitamente chiede di salvare la memoria). Aggiorna:
- La data dell'ultima sessione
- Gli argomenti trattati
- Eventuali nuove preferenze o informazioni sull'utente emerse
- Decisioni importanti prese
- Eventuali task lasciati in sospeso

---

## 2. memories/yyyy-mm-gg/session.md — Archivio Giornaliero

### Quando creare/aggiornare
Alla fine di ogni sessione, salva un riassunto dettagliato nella cartella del giorno corrente. Se la cartella non esiste, creala. Se il file `session.md` esiste già (più sessioni nello stesso giorno), aggiungi una nuova sezione in fondo al file invece di sovrascrivere.

### Struttura del file
```markdown
# Sessione del yyyy-mm-gg

## Sessione HH:MM (ora di inizio approssimativa)

### Richieste principali
- Breve descrizione di cosa ha chiesto l'utente

### Cosa è stato fatto
- Lista delle azioni intraprese, codice scritto, problemi risolti

### Risposte e output notevoli
Riassunto delle risposte più importanti date all'utente.

### Note
Qualsiasi altra informazione utile per il futuro.
```

---

## 3. PROGRESS.md — Avanzamento Task di Coding

Usa `PROGRESS.md` **esclusivamente** durante task di sviluppo software (implementare feature, risolvere bug, costruire un'app). Non usarlo per conversazioni generali.

### Quando creare
Crea o apri `PROGRESS.md` quando inizia un task di coding significativo (più di un paio di file da modificare, o una feature nuova).

### Struttura del file
```markdown
# 🚀 PROGRESS — [Nome del Progetto/Feature]

## Obiettivo
Descrizione chiara di cosa si sta costruendo/risolvendo.

## Task

### ✅ Completati
- [x] Task già fatto

### 🔄 In corso
- [ ] Task su cui si sta lavorando ora

### 📋 Da fare
- [ ] Task futuro 1
- [ ] Task futuro 2

## Note tecniche
Decisioni architetturali, problemi incontrati, soluzioni adottate.

## Ultimo aggiornamento
yyyy-mm-gg HH:MM
```

### Regole di aggiornamento
- Sposta i task tra le sezioni man mano che avanzano
- Aggiungi nuovi task scoperti durante il lavoro
- Aggiorna "Ultimo aggiornamento" ad ogni modifica

### Quando svuotare
Quando l'app o la feature è **completamente completata** e funzionante, svuota il file lasciando solo:
```markdown
# 🚀 PROGRESS

_(nessun task attivo)_
```
Non eliminare mai il file, solo svuotalo.

---

## 4. Ricerca nella Memoria

Quando l'utente chiede "cosa abbiamo fatto il [data]?", "hai memoria di quando...?", o vuole cercare tra le sessioni passate:

1. **Per data specifica**: leggi direttamente `memories/yyyy-mm-gg/session.md`
2. **Per parola chiave**: elenca le cartelle in `memories/`, poi leggi i file `session.md` più recenti o pertinenti per titolo/data
3. **Per contesto generale**: leggi `BRAIN.md` per una panoramica rapida

Quando cerchi, comunica all'utente cosa stai guardando: *"Sto controllando la memoria del [data]..."*

---

## 5. Flusso Operativo di una Sessione

```
INIZIO SESSIONE
    ↓
Leggi BRAIN.md → informa la tua risposta con il contesto precedente
    ↓
[Se task di coding] → Leggi/crea PROGRESS.md
    ↓
Lavora normalmente con l'utente
    ↓
FINE SESSIONE (saluto, "stop", o richiesta esplicita)
    ↓
Aggiorna BRAIN.md con riassunto sessione
    ↓
Salva dettaglio in memories/yyyy-mm-gg/session.md
    ↓
[Se task di coding completato] → Svuota PROGRESS.md
```

---

## 6. Comportamenti Importanti

**Trasparenza**: quando leggi o scrivi in memoria, dillo all'utente brevemente. Es: *"Ho letto il contesto della sessione precedente."* oppure *"Sto salvando il riassunto della sessione."*

**Non sovrascrivere mai** la memoria precedente senza aver prima letto il file esistente. Integra sempre con quanto già presente.

**Lingua**: tutta la memoria viene scritta in **italiano**, in linea con la lingua del progetto.

**Date**: usa sempre il formato `yyyy-mm-gg` per le cartelle e `yyyy-mm-gg HH:MM` per i timestamp nei file.

**Se BRAIN.md non esiste**: crealo al primo utilizzo con un messaggio di benvenuto e la data della prima sessione. Non è un errore, è semplicemente la prima volta.
