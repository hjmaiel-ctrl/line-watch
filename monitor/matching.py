"""
Abbinamento delle partite tra bookmaker diversi, che quasi mai scrivono i nomi
delle squadre esattamente allo stesso modo (es. "Man Utd" vs "Manchester United").
Usiamo una somiglianza testuale semplice (difflib, nella libreria standard di
Python) invece di un abbinamento esatto.
"""
import difflib
from typing import List, Optional, Tuple


def best_match(home: str, away: str, candidates: List[Tuple[str, str]], threshold: float = 0.55):
      """candidates: lista di (home, away). Ritorna (indice, punteggio) del migliore
          match sopra soglia, o (None, punteggio migliore trovato) se nessuno la supera."""
      target = f"{home} {away}".lower()
      best_idx, best_score = None, 0.0
      for idx, (h, a) in enumerate(candidates):
                label = f"{h} {a}".lower()
                score = difflib.SequenceMatcher(None, target, label).ratio()
                # proviamo anche l'abbinamento invertito, in caso "casa/ospite" sia
                # etichettato diversamente da un bookmaker all'altro
                score_swapped = difflib.SequenceMatcher(None, target, f"{a} {h}".lower()).ratio()
                score = max(score, score_swapped)
                if score > best_score:
                              best_score, best_idx = score, idx
                      if best_score >= threshold:
                                return best_idx, best_score
                            return None, best_score
        
