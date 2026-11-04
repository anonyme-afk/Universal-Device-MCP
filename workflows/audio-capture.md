# Workflow : Enregistrement audio avec un microphone

## Objectif

Détecter les microphones disponibles et capturer un échantillon audio WAV en mémoire.

## Preconditions

- `UDMCP_MEDIA_CAPTURE=true` doit être défini dans l'environnement du serveur (opt-in du propriétaire).
- Le paquet `[media]` est installé (`opencv-python-headless`, `sounddevice`, `numpy`).

## Séquence recommandée

1. **Vérifier que le média est autorisé** : vérifier `UDMCP_MEDIA_CAPTURE=true`.
2. **Découvrir les microphones** : `discover_microphones()`
   - Liste les périphériques d'entrée audio sans ouvrir de flux d'enregistrement.
3. **Enregistrer un échantillon** : `record_audio_sample(duration_seconds=3.0, device_index=None)`
   - Durée entre 0,25 et 10 secondes.
   - Retourne un WAV mono 16 kHz encodé en base64, en mémoire uniquement.
   - L'audio n'est pas écrit sur disque et n'est pas conservé dans l'historique.

## Outils MCP utilisés

- `discover_microphones`
- `record_audio_sample`

## Résultat attendu

- Liste des microphones avec `device_id`, `index`, `name`, `max_input_channels`, `default_samplerate`.
- Audio capturé : `mime_type: audio/wav`, `audio_base64`, `sample_rate_hz: 16000`, `channels: 1`, `duration_seconds`, `persisted: false`.

## Gestion des erreurs

| Situation | Action |
|-----------|--------|
| `PermissionError` | `UDMCP_MEDIA_CAPTURE` n'est pas défini. Demander au propriétaire de l'activer localement. |
| `ImportError` | Le paquet `[media]` n'est pas installé. Exécuter `pip install "universal-device-mcp[media]"`. |
| `ValueError` | `duration_seconds` doit être entre 0,25 et 10. Corriger le paramètre. |
| Aucun microphone trouvé | Aucun périphérique d'entrée audio détecté. Vérifier que le microphone est branché et autorisé par l'OS. |

## Considérations de sécurité

- Aucun microphone n'est enregistré en arrière-plan par défaut. `record_audio_sample` requiert un appel explicite.
- L'audio est en mémoire uniquement, jamais écrit sur disque.
- Respecter les paramètres de confidentialité du système d'exploitation (Windows/macOS/Linux).
